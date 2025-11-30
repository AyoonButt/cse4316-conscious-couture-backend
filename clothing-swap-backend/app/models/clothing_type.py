from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy import Numeric
from sqlalchemy.sql import func
from ..database import Base


class ClothingTypeReference(Base):
    __tablename__ = 'clothing_types_reference'

    clothing_type_id = Column(Integer, primary_key=True, autoincrement=True)
    clothing_type = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(30))

    # Typical Specifications
    typical_weight_grams = Column(Integer, nullable=False)
    weight_range_min = Column(Integer)
    weight_range_max = Column(Integer)

    # Lifecycle Assumptions
    typical_wears = Column(Integer, default=50)
    wash_frequency = Column(Numeric(3, 2), default=Decimal('0.25'))

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_clothing_type', 'clothing_type'),
    )

    def __repr__(self):
        return f"<ClothingTypeReference(clothing_type='{self.clothing_type}', " \
               f"category='{self.category}', typical_weight_grams={self.typical_weight_grams})>"

    def to_dict(self):
        return {
            'clothing_type_id': self.clothing_type_id,
            'clothing_type': self.clothing_type,
            'category': self.category,
            'typical_weight_grams': self.typical_weight_grams,
            'weight_range_min': self.weight_range_min,
            'weight_range_max': self.weight_range_max,
            'typical_wears': self.typical_wears,
            'wash_frequency': float(self.wash_frequency) if self.wash_frequency else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def is_weight_in_range(self, weight_grams: int) -> bool:
        """Check if given weight falls within the typical range for this clothing type"""
        if self.weight_range_min and weight_grams < self.weight_range_min:
            return False
        if self.weight_range_max and weight_grams > self.weight_range_max:
            return False
        return True