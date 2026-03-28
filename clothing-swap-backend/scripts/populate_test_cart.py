#!/usr/bin/env python3
"""
Populate a test cart with items (2 available, 1 unavailable) for testing availability verification.
"""

import sys
import hashlib
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_database_session, init_db
from app.models.user import User
from app.models.clothing import ClothingItem
from app.models.cart import CartItem


CART_USERNAME = "sarah_wilson"
SELLER_USERNAME = "alex_brown"


def hash_password(password: str) -> str:
    """Simple password hashing for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_or_create_user(session, username, email, display_name, location):
    """Get or create a user needed for cart testing."""
    existing_user = session.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"✅ Using existing user: {username} (ID: {existing_user.user_id})")
        return existing_user

    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
        display_name=display_name,
        location=location,
        profile_public=True,
        share_stats=True,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"✅ Created user: {username} (ID: {user.user_id})")
    return user


def create_test_items(session, owner_user_id):
    """Create 3 test items: 2 available, 1 unavailable."""
    
    items_data = [
        {
            "clothing_type": "T-Shirt",
            "brand": "Patagonia",
            "description": "Sarah cart test - Available blue cotton t-shirt",
            "size": "M",
            "color": "Blue",
            "condition": "Good",
            "material_composition": {"Cotton": 100},
            "available": True,
            "unavailable_reason": None,
            "sell_price": 24.99,
        },
        {
            "clothing_type": "Jeans",
            "brand": "Levi's",
            "description": "Sarah cart test - Available dark wash jeans",
            "size": "32",
            "color": "Dark Blue",
            "condition": "Excellent",
            "material_composition": {"Cotton": 99, "Spandex": 1},
            "available": True,
            "unavailable_reason": None,
            "sell_price": 42.50,
        },
        {
            "clothing_type": "Hoodie",
            "brand": "The North Face",
            "description": "Sarah cart test - Unavailable grey hoodie",
            "size": "L",
            "color": "Grey",
            "condition": "Good",
            "material_composition": {"Polyester": 80, "Cotton": 20},
            "available": False,
            "unavailable_reason": "Item sold - no longer available",
            "sell_price": 35.00,
        }
    ]
    
    created_items = []
    
    for idx, item_data in enumerate(items_data, 1):
        # Check if item already exists by description
        existing_item = session.query(ClothingItem).filter(
            ClothingItem.description == item_data["description"]
        ).first()
        
        if existing_item:
            existing_item.owner_user_id = owner_user_id
            existing_item.available = item_data["available"]
            existing_item.status = "available" if item_data["available"] else "unavailable"
            existing_item.unavailable_reason = item_data["unavailable_reason"]
            existing_item.sell_price = item_data["sell_price"]
            print(f"  ✅ Item {idx} already exists: {item_data['description']}")
            created_items.append(existing_item)
            continue
        
        item = ClothingItem(
            owner_user_id=owner_user_id,
            clothing_type=item_data["clothing_type"],
            brand=item_data["brand"],
            description=item_data["description"],
            size=item_data["size"],
            color=item_data["color"],
            condition=item_data["condition"],
            material_composition=item_data["material_composition"],
            available=item_data["available"],
            unavailable_reason=item_data["unavailable_reason"],
            status="available" if item_data["available"] else "unavailable",
            sell_price=item_data["sell_price"],
        )
        
        session.add(item)
        created_items.append(item)
        availability_status = "✅ AVAILABLE" if item_data["available"] else "❌ UNAVAILABLE"
        print(f"  Created Item {idx}: {item_data['clothing_type']} - {availability_status}")
    
    session.commit()
    
    # Refresh to get IDs
    for item in created_items:
        session.refresh(item)
    
    return created_items


def add_items_to_cart(session, user_id, items):
    """Add items to user's cart."""
    
    # Clear existing cart items for this user
    existing_cart_items = session.query(CartItem).filter(CartItem.user_id == user_id).all()
    for cart_item in existing_cart_items:
        session.delete(cart_item)
    session.commit()
    print(f"\n✅ Cleared existing cart items")
    
    # Add new items to cart
    for item in items:
        cart_item = CartItem(
            user_id=user_id,
            clothing_id=item.clothing_id
        )
        session.add(cart_item)
        availability_text = "✅ AVAILABLE" if item.available else "❌ UNAVAILABLE"
        print(f"  Added to cart: {item.clothing_type} (ID: {item.clothing_id}) - {availability_text}")
    
    session.commit()
    print(f"\n✅ Cart populated successfully!")


def main():
    """Main function."""
    
    print("🛒 Setting up test cart with mixed availability items...\n")
    
    try:
        init_db()
        session = get_database_session()
        
        # Get or create test users
        print("📝 User Setup:")
        user = get_or_create_user(
            session,
            CART_USERNAME,
            "sarah.wilson@example.com",
            "Sarah Wilson",
            "Austin, TX",
        )
        seller = get_or_create_user(
            session,
            SELLER_USERNAME,
            "alex.brown@example.com",
            "Alex Brown",
            "Seattle, WA",
        )
        
        # Create test items
        print("\n📦 Creating Test Items (2 available, 1 unavailable):")
        items = create_test_items(session, seller.user_id)
        
        # Add items to cart
        print("\n🛍️  Adding Items to Cart:")
        add_items_to_cart(session, user.user_id, items)
        
        # Display summary
        print("\n" + "="*60)
        print("📊 CART SUMMARY")
        print("="*60)
        print(f"User: {user.username} (ID: {user.user_id})")
        print(f"Email: {user.email}")
        print(f"Seller account for seeded items: {seller.username} (ID: {seller.user_id})")
        print(f"\nCart Contents:")
        
        cart_items = session.query(CartItem).filter(CartItem.user_id == user.user_id).all()
        for idx, cart_item in enumerate(cart_items, 1):
            item = cart_item.clothing
            status = "✅ AVAILABLE" if item.available else "❌ UNAVAILABLE"
            print(f"  {idx}. {item.clothing_type} ({item.brand}) - {item.color} - Size: {item.size}")
            print(f"     ID: {item.clothing_id} | Condition: {item.condition} | {status}")
            if item.unavailable_reason:
                print(f"     Reason: {item.unavailable_reason}")
        
        print(f"\nTotal Items in Cart: {len(cart_items)}")
        available_count = sum(1 for cart_item in cart_items if cart_item.clothing.available)
        unavailable_count = len(cart_items) - available_count
        print(f"  • Available: {available_count}")
        print(f"  • Unavailable: {unavailable_count}")
        print("="*60 + "\n")
        
        print(f"✅ Test cart setup complete! Ready for availability verification testing.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'session' in locals():
            session.close()
    
    return True


if __name__ == "__main__":
    main()
