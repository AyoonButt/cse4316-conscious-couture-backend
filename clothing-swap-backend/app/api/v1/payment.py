# app/api/v1/payments.py

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse, PaymentStatusResponse
from app.services.payment import (
    create_payment,
    handle_stripe_webhook,
    get_payment_status,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentCreateResponse)
def create_payment_endpoint(
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
):
    payment, client_secret = create_payment(
        db,
        sale_id=payload.sale_id,
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
        sale_id=payment.sale_id,
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
