# app/models/payment.py
# SQLAlchemy model for Payment

from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Link to Sale (primary reference for purchase payments)
    sale_id = Column(Integer, ForeignKey('sales.sale_id'), nullable=True, index=True)

    # Legacy field - kept for backwards compatibility, will be deprecated
    transaction_id = Column(Integer, nullable=True)

    transaction_type = Column(String(50), default="purchase", nullable=False)

    # Allow null/temporary values before a real Stripe PaymentIntent ID is available
    stripe_payment_intent_id = Column(String, index=True, nullable=True)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="usd", nullable=False)

    status = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to Sale
    sale = relationship('Sale', back_populates='payment')
