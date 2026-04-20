# app/api/v1/checkout.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import (
    CheckoutCreateOrderRequest,
    CheckoutCreateOrderResponse,
    CheckoutShippingRateRequest,
    CheckoutShippingRateResponse,
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
)
from app.services.order import (
    create_order,
    create_payment_intent_for_order,
    get_checkout_shipping_quote,
)
from .users import get_current_user

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("/create-order", response_model=CheckoutCreateOrderResponse)
def create_order_endpoint(
    payload: CheckoutCreateOrderRequest,
    db: Session = Depends(get_db),
    buyer_user_id: int = Depends(get_current_user),
):
    """
    Create a new order for a clothing item.
    This is the first step in the checkout process.
    """
    order = create_order(
        db,
        buyer_user_id=buyer_user_id,
        clothing_id=payload.clothing_id,
        shipping_address=payload.shipping_address,
        buyer_notes=payload.buyer_notes,
    )

    return CheckoutCreateOrderResponse(
        order_id=order.order_id,
        seller_user_id=order.seller_user_id,
        buyer_user_id=order.buyer_user_id,
        clothing_id=order.clothing_id,
        amount_total=order.amount_total,
        currency=order.currency,
        order_status=order.order_status,
        created_at=order.created_at,
    )


@router.post("/create-payment-intent", response_model=CreatePaymentIntentResponse)
def create_payment_intent_endpoint(
    payload: CreatePaymentIntentRequest,
    db: Session = Depends(get_db),
):
    """
    Create a Stripe PaymentIntent for an order.
    This charges the buyer's card.
    
    Flow:
    1. Buyer reviews order summary
    2. Buyer enters card info (handled by Stripe.js on frontend)
    3. This endpoint creates PaymentIntent
    4. Frontend confirms payment with returned client_secret
    """
    order, client_secret = create_payment_intent_for_order(
        db,
        order_id=payload.order_id,
        payment_method_id=payload.payment_method_id,
    )
    
    return CreatePaymentIntentResponse(
        payment_intent_id=order.payment_intent_id,
        client_secret=client_secret,
        amount_total=order.amount_total,
        currency=order.currency,
        requires_payment_method=not bool(payload.payment_method_id),
    )


@router.post("/shipping-rate", response_model=CheckoutShippingRateResponse)
def checkout_shipping_rate_endpoint(
    payload: CheckoutShippingRateRequest,
    db: Session = Depends(get_db),
):
    """
    Return shipping quote and order total for checkout page summary.
    """
    quote = get_checkout_shipping_quote(
        db,
        clothing_id=payload.clothing_id,
        destination_country=payload.destination_country,
    )
    return CheckoutShippingRateResponse(**quote)
