from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Order(Base):
    """
    Order model for the new Stripe Connect payment flow.
    Tracks the full lifecycle of a purchase from checkout to seller payout.
    """
    __tablename__ = 'orders'

    # Primary key
    order_id = Column(Integer, primary_key=True, autoincrement=True)

    # Participants
    buyer_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    seller_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False, index=True)

    # Stripe Connect fields
    seller_stripe_account_id = Column(String(255), nullable=True)  # Seller's connected account ID
    payment_intent_id = Column(String(255), nullable=True, index=True)  # Stripe PaymentIntent ID
    transfer_id = Column(String(255), nullable=True, index=True)  # Stripe Transfer ID for seller payout

    # Order status: created, payment_processing, payment_succeeded, payment_failed, shipped, delivered, completed, cancelled, refunded
    order_status = Column(String(50), default='created', nullable=False, index=True)

    # Financial details
    amount_total = Column(Numeric(10, 2), nullable=False)  # Total amount charged to buyer
    seller_net = Column(Numeric(10, 2), nullable=True)  # Net amount transferred to seller (after platform fees)
    platform_fee = Column(Numeric(10, 2), nullable=True)  # Platform fee amount
    currency = Column(String(3), default='usd', nullable=False)

    # Shipping information
    shipping_address = Column(Text, nullable=True)
    tracking_number = Column(String(100), nullable=True)
    shipping_carrier = Column(String(100), nullable=True)
    shipping_label_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    payment_succeeded_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    buyer_notified_at = Column(DateTime(timezone=True), nullable=True)
    delivery_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    payout_released_at = Column(DateTime(timezone=True), nullable=True)

    # Notes and metadata
    buyer_notes = Column(Text, nullable=True)
    seller_notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)  # For admin/debugging

    # Relationships
    buyer = relationship('User', foreign_keys=[buyer_user_id], backref='orders_as_buyer')
    seller = relationship('User', foreign_keys=[seller_user_id], backref='orders_as_seller')
    clothing = relationship('ClothingItem', backref='orders')

    __table_args__ = (
        CheckConstraint('buyer_user_id != seller_user_id', name='different_order_users'),
        CheckConstraint('amount_total > 0', name='positive_order_amount'),
    )

    def to_dict(self):
        """Convert order to dictionary representation"""
        return {
            'order_id': self.order_id,
            'buyer_user_id': self.buyer_user_id,
            'seller_user_id': self.seller_user_id,
            'clothing_id': self.clothing_id,
            'seller_stripe_account_id': self.seller_stripe_account_id,
            'payment_intent_id': self.payment_intent_id,
            'transfer_id': self.transfer_id,
            'order_status': self.order_status,
            'amount_total': float(self.amount_total) if self.amount_total else None,
            'seller_net': float(self.seller_net) if self.seller_net else None,
            'platform_fee': float(self.platform_fee) if self.platform_fee else None,
            'currency': self.currency,
            'shipping_address': self.shipping_address,
            'tracking_number': self.tracking_number,
            'shipping_carrier': self.shipping_carrier,
            'shipping_label_url': self.shipping_label_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'payment_succeeded_at': self.payment_succeeded_at.isoformat() if self.payment_succeeded_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'buyer_notified_at': self.buyer_notified_at.isoformat() if self.buyer_notified_at else None,
            'delivery_confirmed_at': self.delivery_confirmed_at.isoformat() if self.delivery_confirmed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'payout_released_at': self.payout_released_at.isoformat() if self.payout_released_at else None,
            'buyer_notes': self.buyer_notes,
            'seller_notes': self.seller_notes,
            'cancellation_reason': self.cancellation_reason,
        }

    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled"""
        return self.order_status in ['created', 'payment_processing', 'payment_succeeded']

    def can_mark_shipped(self) -> bool:
        """Check if order can be marked as shipped"""
        return self.order_status == 'payment_succeeded'

    def can_mark_delivered(self) -> bool:
        """Check if order can be marked as delivered"""
        return self.order_status == 'shipped'

    def can_release_funds(self) -> bool:
        """Check if seller funds can be released"""
        return self.order_status == 'delivered' and not self.transfer_id
