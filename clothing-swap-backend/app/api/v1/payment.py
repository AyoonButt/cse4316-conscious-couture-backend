# app/api/v1/payments.py

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payment import (
    PaymentCreateRequest, 
    PaymentCreateResponse, 
    PaymentStatusResponse,
    CardVerificationRequest,
    CardVerificationResponse,
)
from app.services.payment import (
    create_payment,
    handle_stripe_webhook,
    get_payment_status,
    verify_card,
)

router = APIRouter(tags=["payments"])


@router.post("/verify-card", response_model=CardVerificationResponse)
def verify_card_endpoint(payload: CardVerificationRequest) -> CardVerificationResponse:
    """
    Verify a Stripe PaymentMethod without creating a charge.
    The frontend should create a PaymentMethod using Stripe.js/Elements,
    then send the payment_method_id to this endpoint for verification.
    """
    result = verify_card(payment_method_id=payload.payment_method_id)
    return CardVerificationResponse(**result)



@router.post("/create", response_model=PaymentCreateResponse)
def create_payment_endpoint(
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
):
    payment, client_secret = create_payment(
        db,
        transaction_id=payload.clothing_id,
        amount=payload.amount,
    )

    return PaymentCreateResponse(
        payment_id=payment.id,
        client_secret=client_secret,
        status=payment.status,
    )


@router.get("/{payment_id}", response_model=PaymentStatusResponse)
def get_payment_status_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
):
    if payment_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment_id")
    
    payment = get_payment_status(db, payment_id)
    
    return PaymentStatusResponse(
        payment_id=payment.id,
        transaction_id=payment.transaction_id,
        transaction_type=payment.transaction_type,
        stripe_payment_intent_id=payment.stripe_payment_intent_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    await handle_stripe_webhook(db, request)
    return {"status": "ok"}
