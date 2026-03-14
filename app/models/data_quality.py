from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index, ForeignKey
from sqlalchemy import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class DataQualityTracking(Base):
    __tablename__ = 'data_quality_tracking'

    quality_id = Column(Integer, primary_key=True, autoincrement=True)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)

    # Input Data Quality Flags
    has_exact_weight = Column(Boolean, default=False)
    has_verified_composition = Column(Boolean, default=False)
    has_brand_data = Column(Boolean, default=False)
    composition_source = Column(String(30))

    # Quality Scores (0-100)
    material_data_quality = Column(Integer)
    calculation_confidence = Column(Integer)

    # Uncertainty Ranges
    co2_uncertainty_percentage = Column(Numeric(5, 2))
    water_uncertainty_percentage = Column(Numeric(5, 2))

    # Quality Rating
    overall_quality = Column(String(20))

    # Notes
    notes = Column(Text)

    # Timestamps
    calculated_at = Column(DateTime, default=func.now())

    # Relationships
    clothing_item = relationship('ClothingItem')

    # Indexes
    __table_args__ = (
        Index('ix_data_quality_tracking_clothing_id', 'clothing_id'),
    )

    def __repr__(self):
        return f"<DataQualityTracking(quality_id={self.quality_id}, " \
               f"clothing_id={self.clothing_id}, overall_quality='{self.overall_quality}')>"

    def to_dict(self):
        return {
            'quality_id': self.quality_id,
            'clothing_id': self.clothing_id,
            'has_exact_weight': self.has_exact_weight,
            'has_verified_composition': self.has_verified_composition,
            'has_brand_data': self.has_brand_data,
            'composition_source': self.composition_source,
            'material_data_quality': self.material_data_quality,
            'calculation_confidence': self.calculation_confidence,
            'co2_uncertainty_percentage': float(self.co2_uncertainty_percentage) if self.co2_uncertainty_percentage else None,
            'water_uncertainty_percentage': float(self.water_uncertainty_percentage) if self.water_uncertainty_percentage else None,
            'overall_quality': self.overall_quality,
            'notes': self.notes,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }

    def calculate_quality_score(self, clothing_item=None):
        """Calculate overall quality score based on available data"""
        if not clothing_item and self.clothing_item:
            clothing_item = self.clothing_item
        
        if not clothing_item:
            return
        
        score = 0
        max_score = 100
        
        # Weight data quality (20 points)
        if self.has_exact_weight:
            score += 20
        elif clothing_item.weight_grams:
            score += 10  # Estimated weight is better than nothing
        
        # Material composition quality (40 points)
        if self.has_verified_composition:
            score += 40
        elif clothing_item.material_composition:
            if self.composition_source == 'care_label':
                score += 30
            elif self.composition_source == 'ocr':
                score += 20
            else:  # user entry
                score += 15
        
        # Brand data quality (20 points)
        if self.has_brand_data and clothing_item.brand_info:
            score += 20
        elif clothing_item.brand:
            score += 10
        
        # Data source quality (20 points)
        if clothing_item.data_source == 'care_label':
            score += 20
        elif clothing_item.data_source == 'ocr':
            score += 15
        elif clothing_item.data_source == 'barcode':
            score += 18
        else:  # user_entry
            score += 10
        
        self.material_data_quality = min(score, max_score)
        
        # Calculate calculation confidence
        if self.material_data_quality >= 80:
            self.calculation_confidence = 90
            self.overall_quality = 'high'
            self.co2_uncertainty_percentage = Decimal('10.0')
            self.water_uncertainty_percentage = Decimal('15.0')
        elif self.material_data_quality >= 60:
            self.calculation_confidence = 70
            self.overall_quality = 'medium'
            self.co2_uncertainty_percentage = Decimal('25.0')
            self.water_uncertainty_percentage = Decimal('30.0')
        else:
            self.calculation_confidence = 45
            self.overall_quality = 'low'
            self.co2_uncertainty_percentage = Decimal('40.0')
            self.water_uncertainty_percentage = Decimal('50.0')

    @classmethod
    def create_for_clothing_item(cls, session, clothing_item):
        """Create data quality tracking for a clothing item"""
        quality_tracking = cls(clothing_id=clothing_item.clothing_id)
        
        # Set flags based on clothing item data
        quality_tracking.has_exact_weight = not clothing_item.weight_estimated
        quality_tracking.has_verified_composition = clothing_item.composition_verified
        quality_tracking.has_brand_data = clothing_item.brand_id is not None
        quality_tracking.composition_source = clothing_item.data_source
        
        # Calculate quality scores
        quality_tracking.calculate_quality_score(clothing_item)
        
        session.add(quality_tracking)
        session.commit()
        
        return quality_tracking