# app/services/payment.py

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

import stripe
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException

from app.config import settings
from app.models.payment import Payment
from app.models.sale import Sale


# Configure Stripe once at import time
stripe.api_key = settings.STRIPE_SECRET_KEY

# ---- helpers ----

def _to_stripe_amount_cents(amount: Decimal) -> int:
    """
    Stripe expects integer minor units (cents for USD).
    """
    if amount <= 0:
        raise ValueError("amount must be > 0")
    # quantize to 2dp then convert
    cents = int((amount.quantize(Decimal("0.01")) * 100))
    return cents


def _payment_metadata(sale_id: int, payment_id: int) -> dict:
    """
    Metadata is helpful so webhook can map back to your DB rows.
    """
    return {
        "sale_id": str(sale_id),
        "payment_id": str(payment_id),
    }


# ---- public service functions ----

def create_payment(
    db: Session,
    *,
    sale_id: int,
    amount: Optional[Decimal] = None,
    currency: str = "usd",
) -> Tuple[Payment, str]:
    """
    Creates a Payment row in your DB + creates a Stripe PaymentIntent.

    Args:
        db: Database session
        sale_id: ID of the sale to process payment for
        amount: Purchase amount as Decimal (optional, defaults to sale price)
        currency: Currency code (default: "usd")

    Returns: (Payment db row, client_secret)
    """

    # 1) Validate item exists and is available
    # prevent duplicate payments for same swap (simple rule)
    # 1) Validate sale exists and is in valid state for payment
    sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create payment for sale with status '{sale.status}'. Sale must be 'pending'."
        )

    # Use sale price if amount not provided
    if amount is None:
        amount = Decimal(str(sale.sale_price))

    # 2) Prevent duplicate payments for same sale
    existing = (
        db.query(Payment)
        .filter(Payment.sale_id == sale_id)
        .order_by(Payment.id.desc())
        .first()
    )
    if existing and existing.status in {"succeeded", "processing", "requires_action", "requires_payment_method"}:
        # - return existing client_secret (requires storing it; not recommended)
        # - block duplicates
        raise HTTPException(status_code=400, detail="Payment already exists for this swap")
        raise HTTPException(status_code=400, detail="Payment already exists for this sale")

    # 3) Create local payment row first (so we can store payment_id in Stripe metadata)
    payment = Payment(
        sale_id=sale_id,
        transaction_id=sale.clothing_id,
        transaction_type="purchase",
        amount=amount,
        currency=currency.lower(),
        status="created",
        stripe_payment_intent_id="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # 4) Create Stripe PaymentIntent
    try:
        intent = stripe.PaymentIntent.create(
            amount=_to_stripe_amount_cents(amount),
            currency=currency.lower(),
            automatic_payment_methods={"enabled": True},
            metadata=_payment_metadata(sale_id=sale_id, payment_id=payment.id),
        )
    except stripe.error.StripeError as e:
        payment.status = "failed"
        payment.stripe_payment_intent_id = "error"
        db.add(payment)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Stripe error: {getattr(e, 'user_message', str(e))}")

    # 5) Persist Stripe IDs + initial status
    payment.stripe_payment_intent_id = intent.id
    payment.status = intent.status
    db.add(payment)
    db.commit()
    db.refresh(payment)

    client_secret = intent.client_secret
    if not client_secret:
        raise HTTPException(status_code=502, detail="Stripe did not return client_secret")

    return payment, client_secret


async def handle_stripe_webhook(db: Session, request: Request) -> None:
    """
    Verifies Stripe signature, parses event, updates DB status.
    Syncs payment status with linked Sale record.
    This function raises HTTPException on validation errors.
    """

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]

    # We care mostly about PaymentIntent events
    if event_type.startswith("payment_intent."):
        intent = event["data"]["object"]
        intent_id = intent["id"]
        intent_status = intent["status"]

        payment = db.query(Payment).filter(Payment.stripe_payment_intent_id == intent_id).first()

        if not payment:
            return

        # Update payment status
        old_status = payment.status
        payment.status = intent_status
        db.add(payment)

        # Sync with Sale when payment succeeds
        if intent_status == "succeeded" and old_status != "succeeded":
            _sync_sale_on_payment_success(db, payment)

        db.commit()
        return

    # Ignore other event types (or add more handlers as you grow)
    return


def _sync_sale_on_payment_success(db: Session, payment: Payment) -> None:
    """
    Updates the linked Sale record when payment succeeds.
    Sets status to 'payment_received' and records payment_date.
    """
    if not payment.sale_id:
        return

    sale = db.query(Sale).filter(Sale.sale_id == payment.sale_id).first()
    if not sale:
        return

    # Only update if sale is still pending
    if sale.status == "pending":
        sale.status = "payment_received"
        sale.payment_date = datetime.utcnow()
        db.add(sale)


def get_payment_status(
    db: Session,
    payment_id: int,
) -> Payment:
    """
    Retrieves a Payment record from the database and syncs status with Stripe.
    
    Args:
        db: Database session
        payment_id: ID of the payment to retrieve
    
    Returns: Payment db row with current status
    
    Raises: HTTPException 404 if payment not found
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Sync with Stripe if we have a valid payment intent ID
    if payment.stripe_payment_intent_id and payment.stripe_payment_intent_id != "pending" and payment.stripe_payment_intent_id != "error":
        try:
            intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
            # Update local status if it changed in Stripe
            if intent.status != payment.status:
                payment.status = intent.status
                db.add(payment)
                db.commit()
                db.refresh(payment)
        except stripe.error.StripeError:
            # If Stripe is unreachable, just return the local status
            pass
    
    return payment


def verify_card(payment_method_id: str) -> dict:
    """
    Validates a Stripe PaymentMethod to verify the card is valid.
    The PaymentMethod should be created on the frontend using Stripe.js/Elements.
    
    Args:
        payment_method_id: Stripe PaymentMethod ID (e.g., pm_xxx)
    
    Returns: Dict with validation result and card info
    """
    try:
        # Retrieve the PaymentMethod from Stripe
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        
        # Check if it's a card payment method
        if payment_method.type != "card":
            return {
                "valid": False,
                "card_brand": None,
                "last4": None,
                "exp_month": None,
                "exp_year": None,
                "errors": ["Payment method is not a card"],
            }
        
        # Get card details
        card_info = payment_method.get("card", {})
        
        # Additional validation: check if card is expired
        exp_month = card_info.get("exp_month")
        exp_year = card_info.get("exp_year")
        
        from datetime import datetime
        current_date = datetime.now()
        if exp_year < current_date.year or (exp_year == current_date.year and exp_month < current_date.month):
            return {
                "valid": False,
                "card_brand": card_info.get("brand"),
                "last4": card_info.get("last4"),
                "exp_month": exp_month,
                "exp_year": exp_year,
                "errors": ["Card is expired"],
            }
        
        return {
            "valid": True,
            "card_brand": card_info.get("brand"),
            "last4": card_info.get("last4"),
            "exp_month": exp_month,
            "exp_year": exp_year,
            "errors": None,
        }
        
    except stripe.error.InvalidRequestError as e:
        # Invalid payment method ID or not found
        return {
            "valid": False,
            "card_brand": None,
            "last4": None,
            "exp_month": None,
            "exp_year": None,
            "errors": [f"Invalid payment method: {str(e)}"],
        }
        
    except stripe.error.StripeError as e:
        # Other Stripe errors
        return {
            "valid": False,
            "card_brand": None,
            "last4": None,
            "exp_month": None,
            "exp_year": None,
            "errors": [f"Card verification error: {str(e)}"],
        }
