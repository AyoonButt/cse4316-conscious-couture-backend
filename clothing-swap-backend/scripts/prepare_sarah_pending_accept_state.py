#!/usr/bin/env python3
"""Seed a post-checkout, pre-acceptance test state for Sarah and John.

This script creates the same core DB state as the checkout submit step:
  - Sales: pending
  - Orders: created
  - Clothing items: pending
  - Payments + client_secret: created via Stripe PaymentIntent
  - Buyer's cart: cleared

It also prints notification payloads that can be pasted into browser localStorage
so the UI starts with:
  - Sarah: order pending notification
  - John: pending order request notifications ready to accept/reject
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import stripe

from app.config import settings
from app.database import get_database_session, init_db
from app.models.cart import CartItem
from app.models.clothing import ClothingItem
from app.models.order import Order
from app.models.payment import Payment
from app.models.sale import Sale
from app.models.user import User
from app.services.payment import create_payment

BUYER_USERNAME = "sarah_wilson"
SELLER_USERNAME = "john_doe"
ITEM_COUNT = 2


def _build_preview(item: ClothingItem, amount: Decimal) -> str:
    item_name = item.clothing_type or item.description or "Item"
    return f"{item_name} • ${amount:.2f}"


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

        # Clean order-flow state so every run starts deterministic.
        session.query(Payment).delete(synchronize_session=False)
        session.query(Sale).delete(synchronize_session=False)
        session.query(Order).delete(synchronize_session=False)
        session.query(CartItem).delete(synchronize_session=False)

        reset_items = (
            session.query(ClothingItem)
            .filter(ClothingItem.status.in_(["pending", "sold"]))
            .all()
        )
        for item in reset_items:
            item.status = "available"
            item.available = True
            item.unavailable_reason = None

        seller_items = (
            session.query(ClothingItem)
            .filter(ClothingItem.owner_user_id == seller.user_id)
            .order_by(ClothingItem.clothing_id.asc())
            .all()
        )
        if not seller_items:
            raise ValueError("john_doe has no clothing items")

        selected = []
        for item in seller_items:
            item.status = "available"
            item.available = True
            item.unavailable_reason = None
            if not item.sell_price or Decimal(str(item.sell_price)) <= 0:
                item.sell_price = Decimal("24.99")
            selected.append(item)
            if len(selected) >= ITEM_COUNT:
                break

        if not selected:
            raise ValueError("No items available for pending-order seed")

        stripe.api_key = settings.STRIPE_SECRET_KEY

        STRIPE_PERCENT = Decimal("0.029")
        STRIPE_FIXED = Decimal("0.30")
        SHIPENGINE_PER_ORDER = Decimal("0.20")

        pending_sale_ids = []
        seller_notifications = []
        buyer_items = []

        # Create one reusable test payment method for seller-accept flow.
        payment_method_id = None
        try:
            pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
            payment_method_id = pm.id
        except Exception:
            payment_method_id = "pm_card_visa"

        for idx, clothing in enumerate(selected, 1):
            price = Decimal(str(clothing.sell_price)).quantize(Decimal("0.01"))

            sale = Sale(
                seller_id=seller.user_id,
                buyer_id=buyer.user_id,
                clothing_id=clothing.clothing_id,
                sale_price=price,
                original_price=price,
                currency="USD",
                status="pending",
            )
            session.add(sale)
            session.flush()

            platform_fee = (price * STRIPE_PERCENT + STRIPE_FIXED + SHIPENGINE_PER_ORDER).quantize(Decimal("0.01"))
            seller_net = (price - platform_fee).quantize(Decimal("0.01"))
            order = Order(
                buyer_user_id=buyer.user_id,
                seller_user_id=seller.user_id,
                clothing_id=clothing.clothing_id,
                seller_stripe_account_id=seller.stripe_account_id,
                order_status="created",
                amount_total=price,
                seller_net=seller_net,
                platform_fee=platform_fee,
                currency="usd",
            )
            session.add(order)
            session.flush()

            payment, client_secret = create_payment(
                session,
                sale_id=sale.sale_id,
                amount=price,
                currency="usd",
            )

            clothing.status = "pending"
            clothing.available = False
            clothing.unavailable_reason = "pending_order"

            pending_sale_ids.append(sale.sale_id)
            buyer_items.append(
                {
                    "name": clothing.clothing_type or clothing.description or "Item",
                    "size": clothing.size or "",
                    "price": f"{price:.2f}",
                }
            )

            seller_notifications.append(
                {
                    "id": f"seed-seller-{order.order_id}-{idx}",
                    "read": False,
                    "channel": "seller",
                    "type": "seller_order_request",
                    "title": "New Order Request",
                    "message": "A buyer placed an order request. Accept to charge the buyer and finalize.",
                    "preview": _build_preview(clothing, price),
                    "status": "pending",
                    "sellerUserId": seller.user_id,
                    "buyerUserId": buyer.user_id,
                    "buyerName": buyer.display_name or "Sarah Wilson",
                    "orderTotal": f"{price:.2f}",
                    "orderId": order.order_id,
                    "saleId": sale.sale_id,
                    "clientSecret": client_secret,
                    "paymentMethodId": payment_method_id,
                    "shipmentId": None,
                    "rateId": None,
                    "items": [
                        {
                            "clothing_id": clothing.clothing_id,
                            "name": clothing.clothing_type or clothing.description or "Item",
                            "size": clothing.size or "",
                            "price": f"{price:.2f}",
                        }
                    ],
                    "shipping": {
                        "name": buyer.display_name or "Sarah Wilson",
                        "address": buyer.address_line1 or "1002 Baylor St",
                        "city": buyer.city or "Austin",
                        "state": buyer.state or "TX",
                        "zip": buyer.postal_code or "78703",
                    },
                }
            )

            # Keep a link to payment for easier debug traces in DB.
            payment.transaction_id = order.order_id
            session.add(payment)

        buyer_notification = {
            "id": "seed-buyer-order-pending",
            "read": False,
            "channel": "buyer",
            "type": "order_placed",
            "title": "Order Placed Successfully",
            "message": "Your order request is pending seller acceptance. You will be charged after acceptance.",
            "preview": f"{len(buyer_items)} item(s) • Total ${sum(Decimal(i['price']) for i in buyer_items):.2f}",
            "orderDate": None,
            "status": "pending",
            "targetUserId": buyer.user_id,
            "orderTotal": f"{sum(Decimal(i['price']) for i in buyer_items):.2f}",
            "items": buyer_items,
            "shipping": {
                "name": buyer.display_name or "Sarah Wilson",
                "address": buyer.address_line1 or "1002 Baylor St",
                "city": buyer.city or "Austin",
                "state": buyer.state or "TX",
                "zip": buyer.postal_code or "78703",
            },
            "saleIds": pending_sale_ids,
        }

        # Checkout submit clears buyer cart.
        session.query(CartItem).filter(CartItem.user_id == buyer.user_id).delete(synchronize_session=False)
        session.commit()

        print(f"Seeded pending-accept state for buyer={buyer.username} seller={seller.username}")
        print(f"  created sales: {len(pending_sale_ids)}")
        print("  sale status: pending")
        print("  order status: created")
        print("  clothing status: pending")
        print("  buyer cart: cleared")

        print("\nUse this in browser console (while logged in) to seed notifications:")
        print("----- COPY START -----")
        print("(() => {")
        print(f"  const seller = {json.dumps(seller_notifications, separators=(',', ':'))};")
        print(f"  const buyer = [{json.dumps(buyer_notification, separators=(',', ':'))}];")
        print("  const now = new Date().toISOString();")
        print("  seller.forEach(n => { if (!n.createdAt) n.createdAt = now; });")
        print("  buyer.forEach(n => { if (!n.createdAt) n.createdAt = now; if (!n.orderDate) n.orderDate = now; });")
        print("  localStorage.setItem('seller_notifications', JSON.stringify(seller));")
        print("  localStorage.setItem('buyer_notifications', JSON.stringify(buyer));")
        print("  window.dispatchEvent(new CustomEvent('buyer-notifications-updated'));")
        print("  console.log('Seeded pending notifications:', {seller: seller.length, buyer: buyer.length});")
        print("})();")
        print("----- COPY END -----")

    finally:
        session.close()


if __name__ == "__main__":
    main()
