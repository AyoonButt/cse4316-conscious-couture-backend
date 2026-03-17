from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Review(Base):
    __tablename__ = 'reviews'

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)
    reviewer_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    clothing_item = relationship('ClothingItem', back_populates='reviews')
    reviewer = relationship('User', back_populates='reviews_written')

    __table_args__ = (
        UniqueConstraint('clothing_id', 'reviewer_id', name='uq_one_review_per_user_per_item'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='valid_rating_range'),
        Index('ix_reviews_clothing_id', 'clothing_id'),
        Index('ix_reviews_reviewer_id', 'reviewer_id'),
    )

    def to_dict(self):
        return {
            'review_id': self.review_id,
            'clothing_id': self.clothing_id,
            'reviewer_id': self.reviewer_id,
            'rating': self.rating,
            'title': self.title,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }