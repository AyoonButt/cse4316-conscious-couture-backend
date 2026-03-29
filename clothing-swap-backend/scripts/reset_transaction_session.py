#!/usr/bin/env python3
"""
Reset a transaction session between a buyer and seller.

Default: buyer=sarah_wilson, seller=john_doe

1. Deletes Payment rows tied to their Sales
2. Deletes Sale rows between them
3. Restores John Doe's clothing items to 'available'
4. Re-populates Sarah's cart with John Doe's items (2 available + 1 unavailable)
"""

import sys
import hashlib
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_database_session, init_db
from app.models.user import User
from app.models.clothing import ClothingItem
from app.models.cart import CartItem
from app.models.sale import Sale
from app.models.payment import Payment

BUYER_USERNAME = "sarah_wilson"
SELLER_USERNAME = "john_doe"
AVAILABLE_ITEMS = 2
UNAVAILABLE_ITEMS = 1
DEFAULT_PRICES = [24.99, 42.50, 35.00]


def reset(session):
    buyer = session.query(User).filter(User.username == BUYER_USERNAME).first()
    seller = session.query(User).filter(User.username == SELLER_USERNAME).first()

    if not buyer:
        raise ValueError(f"Buyer '{BUYER_USERNAME}' not found — run create_sample_users.py first.")
    if not seller:
        raise ValueError(f"Seller '{SELLER_USERNAME}' not found — run create_sample_users.py first.")

    print(f"Buyer : {buyer.username} (ID {buyer.user_id})")
    print(f"Seller: {seller.username} (ID {seller.user_id})")

    # ── 1. Delete Payments for Sales between these two users ──
    sale_ids = [
        row.sale_id
        for row in session.query(Sale.sale_id)
        .filter(Sale.buyer_id == buyer.user_id, Sale.seller_id == seller.user_id)
        .all()
    ]

    if sale_ids:
        deleted_payments = (
            session.query(Payment)
            .filter(Payment.sale_id.in_(sale_ids))
            .delete(synchronize_session=False)
        )
        session.flush()
        print(f"\n✅ Deleted {deleted_payments} Payment row(s)")
    else:
        print("\nℹ️  No existing payments to delete")

    # ── 2. Delete Sales ──
    deleted_sales = (
        session.query(Sale)
        .filter(Sale.buyer_id == buyer.user_id, Sale.seller_id == seller.user_id)
        .delete(synchronize_session=False)
    )
    session.flush()
    print(f"✅ Deleted {deleted_sales} Sale row(s)")

    # ── 3. Restore John Doe's items to available ──
    seller_items = (
        session.query(ClothingItem)
        .filter(ClothingItem.owner_user_id == seller.user_id)
        .all()
    )

    for item in seller_items:
        item.status = "available"
        item.available = True
        item.unavailable_reason = None

    session.flush()
    print(f"✅ Restored {len(seller_items)} of {seller.username}'s items to 'available'")

    # ── 4. Clear Sarah's cart ──
    session.query(CartItem).filter(CartItem.user_id == buyer.user_id).delete(synchronize_session=False)
    session.flush()
    print(f"✅ Cleared {buyer.username}'s cart")

    # ── 5. Re-populate cart (2 available + 1 unavailable from same seller) ──
    available = [i for i in seller_items if i.status == "available"]

    if len(available) < AVAILABLE_ITEMS + UNAVAILABLE_ITEMS:
        raise ValueError(
            f"{seller.username} only has {len(available)} items — need at least {AVAILABLE_ITEMS + UNAVAILABLE_ITEMS}."
        )

    items_for_cart = available[:AVAILABLE_ITEMS + UNAVAILABLE_ITEMS]

    # Mark the last one as unavailable to simulate mixed cart
    unavail_item = items_for_cart[-1]
    unavail_item.status = "sold"
    unavail_item.available = False
    unavail_item.unavailable_reason = "Item is no longer available"
    session.flush()

    for idx, item in enumerate(items_for_cart):
        if not item.sell_price or float(item.sell_price) <= 0:
            item.sell_price = DEFAULT_PRICES[idx]
        session.add(CartItem(user_id=buyer.user_id, clothing_id=item.clothing_id))

    session.commit()

    print(f"\n🛒 Cart repopulated ({AVAILABLE_ITEMS} available, {UNAVAILABLE_ITEMS} unavailable):")
    for idx, item in enumerate(items_for_cart, 1):
        status = "✅ AVAILABLE" if item.available else "❌ UNAVAILABLE"
        print(f"  {idx}. [{item.clothing_id}] {item.clothing_type} ({item.brand}) — {status} — ${float(item.sell_price):.2f}")

    print("\n" + "=" * 60)
    print("BROWSER STEP — clear localStorage notifications:")
    print("  Open DevTools → Console and run:")
    print("  localStorage.removeItem('buyer_notifications');")
    print("  localStorage.removeItem('seller_notifications');")
    print("  location.reload();")
    print("=" * 60)
    print("\n✅ Transaction session reset complete.")
    print(f"   Login as buyer : {buyer.email} / password123")
    print(f"   Login as seller: {seller.email} / password123")


def main():
    print("🔄 Resetting transaction session...\n")
    try:
        init_db()
        session = get_database_session()
        reset(session)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if "session" in dir():
            session.close()


if __name__ == "__main__":
    main()
