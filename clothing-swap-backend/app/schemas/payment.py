
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class PaymentCreateRequest(BaseModel):
    clothing_id: int = Field(..., gt=0, description="ID of the clothing item being purchased")
    buyer_user_id: int = Field(..., gt=0, description="ID of the buyer")
    amount: Decimal = Field(..., gt=0, description="Purchase amount in USD")


class PaymentCreateResponse(BaseModel):
    payment_id: int
    client_secret: str
    status: str


class PaymentStatusResponse(BaseModel):
    payment_id: int
    transaction_id: int
    transaction_type: str
    stripe_payment_intent_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: str
