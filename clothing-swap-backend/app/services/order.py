# app/services/order.py

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

import stripe
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.config import settings
from app.models.order import Order
from app.models.user import User
from app.models.clothing import ClothingItem

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Net-zero platform fee constants: covers only actual service costs, zero profit
_STRIPE_PERCENT = Decimal("0.029")   # Stripe: 2.9% of transaction
_STRIPE_FIXED = Decimal("0.30")       # Stripe: $0.30 fixed per transaction
_SHIPENGINE_PER_ORDER = Decimal("0.20")  # ShipEngine: avg $0.20 per label


# ---- Helper Functions ----

def _to_stripe_amount_cents(amount: Decimal) -> int:
    """Convert Decimal amount to Stripe integer cents"""
    if amount <= 0:
        raise ValueError("amount must be > 0")
    cents = int((amount.quantize(Decimal("0.01")) * 100))
    return cents


def _calculate_platform_fee(amount: Decimal) -> Decimal:
    """Platform fee = Stripe processing cost + ShipEngine label cost (net zero profit)."""
    fee = (amount * _STRIPE_PERCENT + _STRIPE_FIXED + _SHIPENGINE_PER_ORDER).quantize(Decimal("0.01"))
    return fee


def _calculate_seller_net(amount_total: Decimal, platform_fee: Decimal) -> Decimal:
    """Calculate net amount for seller after platform fee"""
    return (amount_total - platform_fee).quantize(Decimal("0.01"))


def _calculate_shipping_rate(weight_grams: int | None, destination_country: str) -> tuple[Decimal, int]:
    """Return a simple deterministic shipping quote for checkout preview."""
    normalized_country = (destination_country or "US").upper()
    effective_weight = weight_grams or 500

    if normalized_country == "US":
        base = Decimal("5.99")
        per_500g = Decimal("1.50")
        eta_days = 5
    else:
        base = Decimal("14.99")
        per_500g = Decimal("3.00")
        eta_days = 10

    increments = max(0, (effective_weight - 1) // 500)
    shipping = (base + (Decimal(increments) * per_500g)).quantize(Decimal("0.01"))
    return shipping, eta_days


# ---- Public Service Functions ----

def create_order(
    db: Session,
    *,
    buyer_user_id: int,
    clothing_id: int,
    shipping_address: str,
    buyer_notes: Optional[str] = None,
) -> Order:
    """
    Create a new order for a clothing item.
    This is the first step in the checkout process.
    
    Args:
        db: Database session
        buyer_user_id: ID of the buyer
        clothing_id: ID of the clothing item
        shipping_address: Shipping address for delivery
        buyer_notes: Optional notes from buyer
    
    Returns: Created Order object
    """
    # Validate clothing item exists and is available
    clothing = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not clothing:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    if clothing.status != "available":
        raise HTTPException(
            status_code=400,
            detail=f"Clothing item is not available (status: {clothing.status})"
        )
    
    # Get seller info
    seller = db.query(User).filter(User.user_id == clothing.owner_user_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Validate buyer exists and is different from seller
    buyer = db.query(User).filter(User.user_id == buyer_user_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    if buyer_user_id == clothing.owner_user_id:
        raise HTTPException(status_code=400, detail="Cannot purchase your own item")
    
    # Use sell_price if available, otherwise raise error
    if not clothing.sell_price or clothing.sell_price <= 0:
        raise HTTPException(status_code=400, detail="Item has no sell price set")
    
    amount_total = Decimal(str(clothing.sell_price))
    platform_fee = _calculate_platform_fee(amount_total)
    seller_net = _calculate_seller_net(amount_total, platform_fee)
    
    # Create order
    order = Order(
        buyer_user_id=buyer_user_id,
        seller_user_id=clothing.owner_user_id,
        clothing_id=clothing_id,
        seller_stripe_account_id=seller.stripe_account_id,
        order_status="created",
        amount_total=amount_total,
        seller_net=seller_net,
        platform_fee=platform_fee,
        currency="usd",
        shipping_address=shipping_address,
        buyer_notes=buyer_notes,
    )
    
    db.add(order)
    
    # Mark clothing as pending (reserved for this order)
    clothing.status = "pending"
    db.add(clothing)
    
    db.commit()
    db.refresh(order)
    
    return order


def get_checkout_shipping_quote(
    db: Session,
    *,
    clothing_id: int,
    destination_country: str = "US",
) -> dict:
    """
    Compute shipping quote and checkout totals for frontend summary UI.
    """
    normalized_country = (destination_country or "US").upper()
    if normalized_country != "US":
        raise HTTPException(status_code=400, detail="Shipping is currently limited to the US")

    clothing = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not clothing:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    if not clothing.sell_price or clothing.sell_price <= 0:
        raise HTTPException(status_code=400, detail="Item has no sell price set")

    item_subtotal = Decimal(str(clothing.sell_price)).quantize(Decimal("0.01"))
    shipping_rate, eta_days = _calculate_shipping_rate(clothing.weight_grams, normalized_country)
    order_total = (item_subtotal + shipping_rate).quantize(Decimal("0.01"))

    return {
        "clothing_id": clothing.clothing_id,
        "item_subtotal": item_subtotal,
        "shipping_rate": shipping_rate,
        "order_total": order_total,
        "currency": "usd",
        "estimated_delivery_days": eta_days,
    }


def create_payment_intent_for_order(
    db: Session,
    *,
    order_id: int,
    payment_method_id: Optional[str] = None,
) -> Tuple[Order, str]:
    """
    Create a Stripe PaymentIntent for an existing order.
    This charges the buyer's card.
    
    Args:
        db: Database session
        order_id: ID of the order to create payment for
        payment_method_id: Optional Stripe PaymentMethod ID
    
    Returns: Tuple of (Order, client_secret)
    """
    # Get order
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validate order status
    if order.order_status not in ["created", "payment_failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create payment for order with status '{order.order_status}'"
        )
    
    # Prevent duplicate payment intents
    if order.payment_intent_id and order.order_status not in ["payment_failed"]:
        raise HTTPException(status_code=400, detail="Payment intent already exists for this order")
    
    # Create Stripe PaymentIntent
    try:
        intent_params = {
            "amount": _to_stripe_amount_cents(order.amount_total),
            "currency": order.currency.lower(),
            "metadata": {
                "order_id": str(order.order_id),
                "buyer_user_id": str(order.buyer_user_id),
                "seller_user_id": str(order.seller_user_id),
                "clothing_id": str(order.clothing_id),
            },
            "description": f"Order #{order.order_id} - Clothing Item #{order.clothing_id}",
        }
        
        # Add payment method if provided
        if payment_method_id:
            intent_params["payment_method"] = payment_method_id
            intent_params["confirm"] = True
            intent_params["automatic_payment_methods"] = {"enabled": True, "allow_redirects": "never"}
        else:
            intent_params["automatic_payment_methods"] = {"enabled": True}
        
        intent = stripe.PaymentIntent.create(**intent_params)
        
    except stripe.error.StripeError as e:
        order.order_status = "payment_failed"
        order.internal_notes = f"Stripe error: {str(e)}"
        db.add(order)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Stripe error: {getattr(e, 'user_message', str(e))}"
        )
    
    # Update order with payment intent info
    order.payment_intent_id = intent.id
    order.order_status = "payment_processing"
    db.add(order)
    db.commit()
    db.refresh(order)
    
    client_secret = intent.client_secret
    if not client_secret:
        raise HTTPException(status_code=502, detail="Stripe did not return client_secret")
    
    return order, client_secret


def handle_payment_succeeded(db: Session, payment_intent_id: str) -> None:
    """
    Handle successful payment for an order.
    Called by Stripe webhook when payment succeeds.
    
    Args:
        db: Database session
        payment_intent_id: Stripe PaymentIntent ID
    """
    order = db.query(Order).filter(Order.payment_intent_id == payment_intent_id).first()
    if not order:
        return  # Order not found, might be from different flow
    
    # Update order status
    if order.order_status != "payment_succeeded":
        order.order_status = "payment_succeeded"
        order.payment_succeeded_at = datetime.utcnow()
        db.add(order)
        db.commit()


def mark_order_shipped(
    db: Session,
    *,
    order_id: int,
    seller_user_id: int,
    tracking_number: Optional[str] = None,
    shipping_label_url: Optional[str] = None,
    seller_notes: Optional[str] = None,
) -> Order:
    """
    Mark an order as shipped.
    Can only be done by the seller after payment succeeds.
    
    Args:
        db: Database session
        order_id: ID of the order
        seller_user_id: ID of the seller (for authorization)
        tracking_number: Optional tracking number
        seller_notes: Optional notes from seller
    
    Returns: Updated Order object
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify seller owns this order
    if order.seller_user_id != seller_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to mark this order as shipped")
    
    # Verify order can be marked as shipped
    if not order.can_mark_shipped():
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be marked as shipped (status: {order.order_status})"
        )
    
    # If transitioning from 'created', record payment timestamp
    if order.order_status == "created":
        order.payment_succeeded_at = datetime.utcnow()

    # Update order
    order.order_status = "shipped"
    order.shipped_at = datetime.utcnow()
    order.shipping_carrier = settings.SHIPPING_DEFAULT_CARRIER
    if tracking_number:
        order.tracking_number = tracking_number
    if shipping_label_url:
        order.shipping_label_url = shipping_label_url
    # Buyer notification feed can rely on this timestamp to show new shipment updates.
    order.buyer_notified_at = datetime.utcnow()
    if seller_notes:
        order.seller_notes = seller_notes
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return order


def get_buyer_notifications(
    db: Session,
    *,
    buyer_user_id: int,
) -> list[dict]:
    """Return shipping-related notifications for buyer header dropdown."""
    orders = (
        db.query(Order)
        .filter(Order.buyer_user_id == buyer_user_id)
        .filter(Order.order_status.in_(["shipped", "delivered", "completed"]))
        .order_by(Order.buyer_notified_at.desc().nullslast(), Order.shipped_at.desc().nullslast())
        .limit(25)
        .all()
    )

    notifications: list[dict] = []
    for order in orders:
        if order.shipping_label_url:
            notifications.append(
                {
                    "notification_type": "shipping_label_ready",
                    "order_id": order.order_id,
                    "message": f"Your shipping label is ready for order #{order.order_id}.",
                    "created_at": order.buyer_notified_at or order.shipped_at or order.created_at,
                    "shipping_label_url": order.shipping_label_url,
                    "tracking_number": order.tracking_number,
                    "shipping_carrier": order.shipping_carrier,
                }
            )

    return notifications


def mark_order_delivered(
    db: Session,
    *,
    order_id: int,
    buyer_user_id: int,
) -> Order:
    """
    Mark an order as delivered.
    Can only be done by the buyer after shipping.
    
    Args:
        db: Database session
        order_id: ID of the order
        buyer_user_id: ID of the buyer (for authorization)
    
    Returns: Updated Order object
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify buyer owns this order
    if order.buyer_user_id != buyer_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to mark this order as delivered")
    
    # Verify order can be marked as delivered
    if not order.can_mark_delivered():
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be marked as delivered (status: {order.order_status})"
        )
    
    # Update order
    order.order_status = "delivered"
    order.delivery_confirmed_at = datetime.utcnow()
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return order


def release_seller_funds(
    db: Session,
    *,
    order_id: int,
) -> Order:
    """
    Release funds to seller via Stripe Transfer.
    Can only be done after delivery is confirmed.
    
    Args:
        db: Database session
        order_id: ID of the order
    
    Returns: Updated Order object with transfer_id
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify order can release funds
    if not order.can_release_funds():
        raise HTTPException(
            status_code=400,
            detail=f"Cannot release funds for order (status: {order.order_status}, transfer_id: {order.transfer_id})"
        )
    
    # Verify seller has Stripe Connect account
    if not order.seller_stripe_account_id:
        raise HTTPException(
            status_code=400,
            detail="Seller does not have a connected Stripe account"
        )
    
    # Create Stripe Transfer
    try:
        transfer = stripe.Transfer.create(
            amount=_to_stripe_amount_cents(order.seller_net),
            currency=order.currency.lower(),
            destination=order.seller_stripe_account_id,
            metadata={
                "order_id": str(order.order_id),
                "seller_user_id": str(order.seller_user_id),
            },
            description=f"Payout for Order #{order.order_id}",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe transfer error: {getattr(e, 'user_message', str(e))}"
        )
    
    # Update order with transfer info
    order.transfer_id = transfer.id
    order.payout_released_at = datetime.utcnow()
    order.order_status = "completed"
    order.completed_at = datetime.utcnow()
    
    db.add(order)
    
    # Update clothing item to sold status
    clothing = db.query(ClothingItem).filter(ClothingItem.clothing_id == order.clothing_id).first()
    if clothing:
        clothing.status = "sold"
        clothing.owner_user_id = order.buyer_user_id  # Transfer ownership
        db.add(clothing)
    
    db.commit()
    db.refresh(order)
    
    return order


def get_order_by_id(db: Session, order_id: int) -> Order:
    """
    Get an order by ID.
    
    Args:
        db: Database session
        order_id: ID of the order
    
    Returns: Order object
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def cancel_order(
    db: Session,
    *,
    order_id: int,
    user_id: int,
    cancellation_reason: Optional[str] = None,
) -> Tuple[Order, Optional[str]]:
    """
    Cancel an order and refund if payment was made.
    Can be done by buyer or seller before delivery.
    
    Args:
        db: Database session
        order_id: ID of the order
        user_id: ID of the user cancelling (buyer or seller)
        cancellation_reason: Reason for cancellation
    
    Returns: Tuple of (Updated Order, refund_id if refund was created)
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify user is buyer or seller
    if user_id not in [order.buyer_user_id, order.seller_user_id]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
    # Verify order can be cancelled
    if not order.can_be_cancelled():
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be cancelled (status: {order.order_status})"
        )
    
    refund_id = None
    
    # If payment was successful, create refund
    if order.order_status == "payment_succeeded" and order.payment_intent_id:
        try:
            refund = stripe.Refund.create(
                payment_intent=order.payment_intent_id,
                metadata={
                    "order_id": str(order.order_id),
                    "cancellation_reason": cancellation_reason or "Order cancelled",
                },
            )
            refund_id = refund.id
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Stripe refund error: {getattr(e, 'user_message', str(e))}"
            )
    
    # Update order status
    order.order_status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    order.cancellation_reason = cancellation_reason
    
    db.add(order)
    
    # Restore clothing item to available status
    clothing = db.query(ClothingItem).filter(ClothingItem.clothing_id == order.clothing_id).first()
    if clothing:
        clothing.status = "available"
        db.add(clothing)
    
    db.commit()
    db.refresh(order)
    
    return order, refund_id
