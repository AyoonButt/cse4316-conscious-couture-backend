#!/usr/bin/env python3
"""
Populate Sarah's cart from existing database items:
- 2 available items
- 1 unavailable item
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
AVAILABLE_ITEMS_TO_USE = 2
UNAVAILABLE_ITEMS_TO_USE = 1
DEFAULT_TEST_PRICES = [24.99, 42.50, 35.00]


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


def select_existing_items(session, cart_user_id):
    """Select 2 available and 1 unavailable items from the SAME owner."""

    all_items = (
        session.query(ClothingItem)
        .filter(ClothingItem.owner_user_id != cart_user_id)
        .order_by(ClothingItem.clothing_id.asc())
        .all()
    )

    # Group items by owner
    from collections import defaultdict
    items_by_owner = defaultdict(list)
    for item in all_items:
        items_by_owner[item.owner_user_id].append(item)

    # Find an owner with enough items (prefer one with both available and unavailable)
    chosen_owner_id = None
    for owner_id, items in items_by_owner.items():
        avail = [i for i in items if i.status == "available"]
        unavail = [i for i in items if i.status != "available"]
        if len(avail) >= AVAILABLE_ITEMS_TO_USE and len(unavail) >= UNAVAILABLE_ITEMS_TO_USE:
            chosen_owner_id = owner_id
            break

    # Fallback: owner with most total items (mark extras unavailable)
    if chosen_owner_id is None:
        chosen_owner_id = max(items_by_owner, key=lambda oid: len(items_by_owner[oid]))

    owner_items = items_by_owner[chosen_owner_id]
    available_items = [item for item in owner_items if item.status == "available"]
    unavailable_items = [item for item in owner_items if item.status != "available"]

    # If not enough unavailable items, force one available item to unavailable
    if len(unavailable_items) < UNAVAILABLE_ITEMS_TO_USE:
        extra = available_items[AVAILABLE_ITEMS_TO_USE:]
        if not extra:
            raise ValueError(
                f"Owner {chosen_owner_id} does not have enough items to fill the cart."
            )
        item_to_force = extra[0]
        item_to_force.status = "sold"
        session.commit()
        session.refresh(item_to_force)
        available_items = available_items[:AVAILABLE_ITEMS_TO_USE]
        unavailable_items = [item_to_force]

    owner_user = session.query(User).filter(User.user_id == chosen_owner_id).first()
    print(f"\n👤 Items owner: {owner_user.username} ({owner_user.email})")

    selected_items = (
        available_items[:AVAILABLE_ITEMS_TO_USE]
        + unavailable_items[:UNAVAILABLE_ITEMS_TO_USE]
    )

    for index, item in enumerate(selected_items):
        if not item.sell_price or float(item.sell_price) <= 0:
            item.sell_price = DEFAULT_TEST_PRICES[index]
        if item.status == "available":
            item.available = True
            item.unavailable_reason = None
        else:
            item.available = False
            if not item.unavailable_reason:
                item.unavailable_reason = "Item is no longer available"

    session.commit()

    for item in selected_items:
        session.refresh(item)

    return selected_items


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
        
        # Get or create cart user
        print("📝 User Setup:")
        user = get_or_create_user(
            session,
            CART_USERNAME,
            "sarah.wilson@example.com",
            "Sarah Wilson",
            "Austin, TX",
        )

        # Select existing database items
        print("\n📦 Selecting Existing Database Items (2 available, 1 unavailable):")
        items = select_existing_items(session, user.user_id)
        for idx, item in enumerate(items, 1):
            availability_status = "✅ AVAILABLE" if item.available else "❌ UNAVAILABLE"
            print(
                f"  Selected Item {idx}: ID {item.clothing_id} | {item.clothing_type} | "
                f"{item.brand} | {availability_status} | ${float(item.sell_price):.2f}"
            )
        
        # Add items to cart
        print("\n🛍️  Adding Items to Cart:")
        add_items_to_cart(session, user.user_id, items)
        
        # Display summary
        print("\n" + "="*60)
        print("📊 CART SUMMARY")
        print("="*60)
        print(f"User: {user.username} (ID: {user.user_id})")
        print(f"Email: {user.email}")
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
