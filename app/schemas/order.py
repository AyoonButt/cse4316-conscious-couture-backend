from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.config import settings


# ======= Checkout Schemas =======

class CheckoutCreateOrderRequest(BaseModel):
    """Request to create an order in checkout process"""
    clothing_id: int = Field(..., gt=0, description="ID of the clothing item to purchase")
    shipping_address: str = Field(..., min_length=1, description="Shipping address for the order")
    buyer_notes: Optional[str] = Field(None, description="Optional notes from buyer")


class CheckoutCreateOrderResponse(BaseModel):
    """Response when order is created"""
    order_id: int
    seller_user_id: int
    buyer_user_id: int
    clothing_id: int
    amount_total: Decimal
    currency: str
    order_status: str
    created_at: datetime


class CheckoutShippingRateRequest(BaseModel):
    """Request shipping quote for checkout page totals."""
    clothing_id: int = Field(..., gt=0, description="ID of the clothing item")
    destination_country: str = Field("US", min_length=2, max_length=2, description="ISO country code")


class CheckoutShippingRateResponse(BaseModel):
    """Shipping quote used by frontend checkout pricing summary."""
    clothing_id: int
    item_subtotal: Decimal
    shipping_rate: Decimal
    order_total: Decimal
    currency: str
    estimated_delivery_days: int


# ======= Payment Intent Schemas =======

class CreatePaymentIntentRequest(BaseModel):
    """Request to create a Stripe PaymentIntent for an order"""
    order_id: int = Field(..., gt=0, description="ID of the order to create payment for")
    payment_method_id: Optional[str] = Field(None, description="Stripe PaymentMethod ID (optional)")


class CreatePaymentIntentResponse(BaseModel):
    """Response with PaymentIntent client secret"""
    payment_intent_id: str
    client_secret: str
    amount_total: Decimal
    currency: str
    requires_payment_method: bool


# ======= Order Management Schemas =======

class OrderResponse(BaseModel):
    """Full order details response"""
    order_id: int
    buyer_user_id: int
    seller_user_id: int
    clothing_id: int
    seller_stripe_account_id: Optional[str]
    payment_intent_id: Optional[str]
    transfer_id: Optional[str]
    order_status: str
    amount_total: Decimal
    seller_net: Optional[Decimal]
    platform_fee: Optional[Decimal]
    currency: str
    shipping_address: Optional[str]
    tracking_number: Optional[str]
    shipping_carrier: Optional[str]
    shipping_label_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    payment_succeeded_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivery_confirmed_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    payout_released_at: Optional[datetime]
    buyer_notes: Optional[str]
    seller_notes: Optional[str]


class MarkDeliveredRequest(BaseModel):
    """Request to mark an order as delivered"""
    delivery_notes: Optional[str] = Field(None, description="Optional notes about delivery")


class MarkDeliveredResponse(BaseModel):
    """Response when order is marked as delivered"""
    order_id: int
    order_status: str
    delivery_confirmed_at: datetime
    message: str


class ReleaseSellerFundsRequest(BaseModel):
    """Request to release funds to seller"""
    pass  # No additional fields needed


class ReleaseSellerFundsResponse(BaseModel):
    """Response when seller funds are released"""
    order_id: int
    transfer_id: str
    seller_net: Decimal
    payout_released_at: datetime
    message: str


class MarkShippedRequest(BaseModel):
    """Request to mark an order as shipped"""
    tracking_number: Optional[str] = Field(None, description="Shipping tracking number")
    shipping_label_url: Optional[str] = Field(None, description="Shipping label URL for buyer download")
    seller_notes: Optional[str] = Field(None, description="Optional notes from seller")


class MarkShippedResponse(BaseModel):
    """Response when order is marked as shipped"""
    order_id: int
    order_status: str
    shipped_at: datetime
    tracking_number: Optional[str]
    shipping_carrier: Optional[str] = settings.SHIPPING_DEFAULT_CARRIER
    shipping_label_url: Optional[str]
    message: str


class BuyerNotificationItem(BaseModel):
    notification_type: str
    order_id: int
    message: str
    created_at: datetime
    shipping_label_url: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None


class BuyerNotificationsResponse(BaseModel):
    buyer_user_id: int
    unread_count: int
    notifications: list[BuyerNotificationItem]


class CancelOrderRequest(BaseModel):
    """Request to cancel an order"""
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")


class CancelOrderResponse(BaseModel):
    """Response when order is cancelled"""
    order_id: int
    order_status: str
    cancelled_at: datetime
    refund_id: Optional[str]
    message: str
