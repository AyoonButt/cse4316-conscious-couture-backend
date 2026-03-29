#!/usr/bin/env python3
"""
Verify cart items are in the database.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_database_session, init_db
from app.models.cart import CartItem
from app.models.clothing import ClothingItem


TARGET_USERNAME = "sarah_wilson"


def verify_cart():
    """Verify test cart items in database."""
    
    try:
        init_db()
        session = get_database_session()
        
        from app.models.user import User

        user = session.query(User).filter(User.username == TARGET_USERNAME).first()
        if not user:
            print(f"❌ User {TARGET_USERNAME} was not found")
            return

        cart_items = session.query(CartItem).filter(
            CartItem.user_id == user.user_id
        ).all()
        
        if not cart_items:
            print(f"❌ No cart items found for {TARGET_USERNAME}")
            return
        
        print(f"✅ Found {len(cart_items)} items in cart for {TARGET_USERNAME}:\n")
        
        for idx, cart_item in enumerate(cart_items, 1):
            item = cart_item.clothing
            status = "✅ AVAILABLE" if item.available else "❌ UNAVAILABLE"
            print(f"  {idx}. {item.clothing_type} - {item.brand} ({item.color})")
            print(f"     ID: {item.clothing_id} | Status: {status}")
            if not item.available:
                print(f"     Reason: {item.unavailable_reason}")
            print()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    verify_cart()
