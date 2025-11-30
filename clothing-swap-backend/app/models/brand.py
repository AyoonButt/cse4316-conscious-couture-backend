from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class BrandSustainability(Base):
    __tablename__ = 'brands_sustainability'

    brand_id = Column(Integer, primary_key=True, autoincrement=True)
    brand_name = Column(String(100), unique=True, nullable=False, index=True)
    brand_name_normalized = Column(String(100), index=True)

    # Transparency Metrics (from WikiRate)
    transparency_index_score = Column(Integer)
    transparency_year = Column(Integer)

    # Disclosure Flags
    publishes_supplier_list = Column(Boolean)
    discloses_ghg_emissions = Column(Boolean)
    discloses_water_usage = Column(Boolean)
    discloses_waste_data = Column(Boolean)
    has_living_wage_commitment = Column(Boolean)
    has_climate_targets = Column(Boolean)

    # Supply Chain Transparency
    tier1_suppliers_disclosed = Column(Integer)
    tier2_suppliers_disclosed = Column(Integer)
    countries_manufacturing = Column(Integer)

    # Optional: Good On You Scores (if API added later)
    planet_score = Column(Integer)
    people_score = Column(Integer)
    animal_score = Column(Integer)
    overall_rating = Column(String(20))

    # Metadata
    last_updated = Column(DateTime)
    api_response = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    clothing_items = relationship('ClothingItem', back_populates='brand_info')

    # Indexes
    __table_args__ = (
        Index('ix_brands_brand_name', 'brand_name'),
        Index('ix_brands_brand_name_normalized', 'brand_name_normalized'),
    )

    def __repr__(self):
        return f"<BrandSustainability(brand_name='{self.brand_name}', " \
               f"transparency_index_score={self.transparency_index_score})>"

    def to_dict(self):
        return {
            'brand_id': self.brand_id,
            'brand_name': self.brand_name,
            'brand_name_normalized': self.brand_name_normalized,
            'transparency_index_score': self.transparency_index_score,
            'transparency_year': self.transparency_year,
            'publishes_supplier_list': self.publishes_supplier_list,
            'discloses_ghg_emissions': self.discloses_ghg_emissions,
            'discloses_water_usage': self.discloses_water_usage,
            'discloses_waste_data': self.discloses_waste_data,
            'has_living_wage_commitment': self.has_living_wage_commitment,
            'has_climate_targets': self.has_climate_targets,
            'tier1_suppliers_disclosed': self.tier1_suppliers_disclosed,
            'tier2_suppliers_disclosed': self.tier2_suppliers_disclosed,
            'countries_manufacturing': self.countries_manufacturing,
            'planet_score': self.planet_score,
            'people_score': self.people_score,
            'animal_score': self.animal_score,
            'overall_rating': self.overall_rating,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'api_response': self.api_response,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def is_data_stale(self, ttl_days: int = 30) -> bool:
        """Check if data needs refresh"""
        if not self.last_updated:
            return True
        age = datetime.utcnow() - self.last_updated
        return age.days > ttl_days

    @classmethod
    def normalize_brand_name(cls, brand_name: str) -> str:
        """Normalize brand name for matching"""
        if not brand_name:
            return ''
        return brand_name.lower().replace(' ', '').replace('&', '').replace('.', '')

    def update_normalized_name(self):
        """Update the normalized name based on current brand_name"""
        self.brand_name_normalized = self.normalize_brand_name(self.brand_name)