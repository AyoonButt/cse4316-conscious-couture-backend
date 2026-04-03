from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class CartAddRequest(BaseModel):
    clothing_id: int = Field(..., gt=0, description="ID of the clothing item to add")


class CartItemResponse(BaseModel):
    cart_item_id: int
    clothing_id: int
    name: str
    owner_name: Optional[str] = None
    size: Optional[str] = None
    price: Optional[float] = None
    brand: Optional[str] = None
    image: Optional[str] = None
    clothing_type: Optional[str] = None
    condition: Optional[str] = None
    available: bool = True
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    count: int
    total: float


class CartValidationItem(BaseModel):
    clothing_id: int
    name: str
    available: bool
    reason: Optional[str] = None


class CartValidationResponse(BaseModel):
    valid: bool
    items: List[CartValidationItem]
    unavailable_count: int


class CheckoutRequest(BaseModel):
    """Sent by frontend to initiate checkout for all cart items."""
    pass  # Auth token provides user_id; cart is server-side


class CheckoutItemResult(BaseModel):
    clothing_id: int
    seller_id: int
    sale_id: int
    payment_id: int
    client_secret: str
    amount: str
    status: str


class CheckoutResponse(BaseModel):
    """One sale + payment per cart item."""
    items: List[CheckoutItemResult]
    total_amount: str


class PurchaseCompleteRequest(BaseModel):
    """Sent after Stripe confirms payment."""
    sale_ids: List[int] = Field(..., description="Sale IDs that were successfully paid")