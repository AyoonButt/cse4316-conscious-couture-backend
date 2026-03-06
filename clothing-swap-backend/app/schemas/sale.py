from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SaleCreate(BaseModel):
    """Schema for buyer initiating a purchase"""
    clothing_id: int = Field(..., description="ID of the clothing item to purchase")
    seller_id: int = Field(..., description="ID of the seller")
    buyer_id: int = Field(..., description="ID of the buyer")
    sale_price: float = Field(..., description="Agreed sale price", gt=0)
    shipping_address: Optional[str] = Field(None, description="Shipping address for delivery")
    buyer_notes: Optional[str] = Field(None, description="Notes from buyer")


class SaleUpdate(BaseModel):
    """Schema for updating sale details"""
    shipping_address: Optional[str] = None
    tracking_number: Optional[str] = None
    seller_notes: Optional[str] = None
    buyer_notes: Optional[str] = None


class SaleStatusUpdate(BaseModel):
    """Schema for status transitions"""
    status: str = Field(..., description="New status (pending, payment_received, shipped, delivered, completed, cancelled, refunded)")


class SaleCancelRequest(BaseModel):
    """Schema for cancelling a sale"""
    reason: Optional[str] = Field(None, description="Reason for cancellation")


class SaleResponse(BaseModel):
    """Schema for API response"""
    sale_id: int
    seller_id: int
    buyer_id: int
    clothing_id: int
    sale_price: float
    original_price: Optional[float] = None
    currency: str = "USD"
    status: str
    shipping_address: Optional[str] = None
    tracking_number: Optional[str] = None
    seller_notes: Optional[str] = None
    buyer_notes: Optional[str] = None
    payment_date: Optional[datetime] = None
    shipped_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    cancelled_date: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SaleList(BaseModel):
    """Schema for paginated list of sales"""
    items: List[SaleResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class SaleFilter(BaseModel):
    """Schema for filtering sales"""
    seller_id: Optional[int] = None
    buyer_id: Optional[int] = None
    clothing_id: Optional[int] = None
    status: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
