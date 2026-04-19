#!/usr/bin/env python3
"""Clear order-flow test data for a clean end-to-end run."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import init_db, get_database_session
from app.models.cart import CartItem
from app.models.clothing import ClothingItem
from app.models.order import Order
from app.models.payment import Payment
from app.models.sale import Sale


def main() -> None:
    init_db()
    session = get_database_session()
    try:
        deleted_payments = session.query(Payment).delete(synchronize_session=False)
        deleted_sales = session.query(Sale).delete(synchronize_session=False)
        deleted_orders = session.query(Order).delete(synchronize_session=False)
        deleted_cart_items = session.query(CartItem).delete(synchronize_session=False)

        reset_items = (
            session.query(ClothingItem)
            .filter(ClothingItem.status.in_(["pending", "sold"]))
            .all()
        )
        for item in reset_items:
            item.status = "available"
            item.available = True
            item.unavailable_reason = None

        session.commit()

        print("Cleared order-related data:")
        print(f"  payments: {deleted_payments}")
        print(f"  sales: {deleted_sales}")
        print(f"  orders: {deleted_orders}")
        print(f"  cart_items: {deleted_cart_items}")
        print(f"  clothing reset to available: {len(reset_items)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
