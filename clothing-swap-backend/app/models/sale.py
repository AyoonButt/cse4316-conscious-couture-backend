from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, CheckConstraint, Numeric, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Sale(Base):
    __tablename__ = 'sales'

    sale_id = Column(Integer, primary_key=True, autoincrement=True)

    # Participants
    seller_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    buyer_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)

    # Sale details
    sale_price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default='USD')

    # Status: pending, payment_received, shipped, delivered, completed, cancelled, refunded
    status = Column(String(20), default='pending', index=True)

    # Shipping
    shipping_address = Column(Text, nullable=True)
    tracking_number = Column(String(100), nullable=True)

    # Dates
    payment_date = Column(DateTime, nullable=True)
    shipped_date = Column(DateTime, nullable=True)
    completed_date = Column(Date, nullable=True)
    cancelled_date = Column(DateTime, nullable=True)

    # Notes
    seller_notes = Column(Text, nullable=True)
    buyer_notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    seller = relationship('User', foreign_keys=[seller_id], back_populates='sales_as_seller')
    buyer = relationship('User', foreign_keys=[buyer_id], back_populates='sales_as_buyer')
    clothing = relationship('ClothingItem', back_populates='sales')
    payment = relationship('Payment', back_populates='sale', uselist=False)

    __table_args__ = (
        Index('ix_sales_seller_id', 'seller_id'),
        Index('ix_sales_buyer_id', 'buyer_id'),
        Index('ix_sales_clothing_id', 'clothing_id'),
        CheckConstraint('seller_id != buyer_id', name='different_sale_users'),
        CheckConstraint('sale_price > 0', name='positive_sale_price'),
    )

    def to_dict(self):
        return {
            'sale_id': self.sale_id,
            'seller_id': self.seller_id,
            'buyer_id': self.buyer_id,
            'clothing_id': self.clothing_id,
            'sale_price': float(self.sale_price) if self.sale_price else None,
            'original_price': float(self.original_price) if self.original_price else None,
            'currency': self.currency,
            'status': self.status,
            'tracking_number': self.tracking_number,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'shipped_date': self.shipped_date.isoformat() if self.shipped_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def complete_sale(self, session):
        """Mark sale as completed and transfer ownership"""
        self.status = 'completed'
        self.completed_date = func.current_date()
        if self.clothing:
            self.clothing.owner_user_id = self.buyer_id
            self.clothing.status = 'sold'
        session.commit()

    def cancel_sale(self, session, reason=None):
        """Cancel sale and restore item availability"""
        self.status = 'cancelled'
        self.cancelled_date = func.now()
        self.cancellation_reason = reason
        if self.clothing:
            self.clothing.status = 'available'
        session.commit()
