#!/usr/bin/env python3
"""Prepare a clean cart so Sarah can place an order from John with available items only."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import init_db, get_database_session
from app.models.cart import CartItem
from app.models.clothing import ClothingItem
from app.models.user import User

BUYER_USERNAME = "sarah_wilson"
SELLER_USERNAME = "john_doe"
ITEM_COUNT = 2


def main() -> None:
    init_db()
    session = get_database_session()
    try:
        buyer = session.query(User).filter(User.username == BUYER_USERNAME).first()
        seller = session.query(User).filter(User.username == SELLER_USERNAME).first()

        if not buyer:
            raise ValueError("Buyer sarah_wilson not found")
        if not seller:
            raise ValueError("Seller john_doe not found")

        # Clear buyer cart first
        session.query(CartItem).filter(CartItem.user_id == buyer.user_id).delete(synchronize_session=False)

        # Ensure seller has available items with price
        seller_items = (
            session.query(ClothingItem)
            .filter(ClothingItem.owner_user_id == seller.user_id)
            .order_by(ClothingItem.clothing_id.asc())
            .all()
        )

        if not seller_items:
            raise ValueError("john_doe has no clothing items")

        prepared = []
        for item in seller_items:
            item.status = "available"
            item.available = True
            item.unavailable_reason = None
            if not item.sell_price or float(item.sell_price) <= 0:
                item.sell_price = 24.99
            prepared.append(item)

        selected = prepared[:ITEM_COUNT]
        if len(selected) < 1:
            raise ValueError("No items available to add to Sarah's cart")

        for item in selected:
            session.add(CartItem(user_id=buyer.user_id, clothing_id=item.clothing_id))

        session.commit()

        print(f"Buyer: {buyer.username} (id={buyer.user_id})")
        print(f"Seller: {seller.username} (id={seller.user_id})")
        print(f"Prepared {len(selected)} available item(s) in Sarah's cart:")
        for item in selected:
            print(f"  clothing_id={item.clothing_id} type={item.clothing_type} price={float(item.sell_price):.2f} status={item.status}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
