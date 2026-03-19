from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class CartItem(Base):
    __tablename__ = 'cart_items'

    cart_item_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)
    added_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship('User', back_populates='cart_items')
    clothing = relationship('ClothingItem')

    __table_args__ = (
        # Each user can only have a given item in their cart once
        UniqueConstraint('user_id', 'clothing_id', name='uq_cart_user_clothing'),
        Index('ix_cart_items_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<CartItem(user_id={self.user_id}, clothing_id={self.clothing_id})>"