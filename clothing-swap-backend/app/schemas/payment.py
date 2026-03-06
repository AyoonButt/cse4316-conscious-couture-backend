from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class PaymentCreateRequest(BaseModel):
    sale_id: int = Field(..., gt=0, description="ID of the sale to process payment for")
    amount: Optional[Decimal] = Field(None, gt=0, description="Purchase amount (optional, defaults to sale price)")


class PaymentCreateResponse(BaseModel):
    payment_id: int
    client_secret: str
    status: str


class PaymentStatusResponse(BaseModel):
    payment_id: int
    sale_id: Optional[int] = None
    transaction_id: Optional[int] = None  # Deprecated, use sale_id
    transaction_type: str
    stripe_payment_intent_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: str


class CardVerificationRequest(BaseModel):
    payment_method_id: str = Field(..., description="Stripe PaymentMethod ID from frontend (e.g., pm_xxx)")


class CardVerificationResponse(BaseModel):
    valid: bool
    card_brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    errors: Optional[list[str]] = None
