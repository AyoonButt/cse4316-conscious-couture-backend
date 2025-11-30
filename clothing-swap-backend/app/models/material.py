from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Index
from sqlalchemy import Numeric
from sqlalchemy.sql import func
from ..database import Base


class MaterialReference(Base):
    __tablename__ = 'materials_reference'

    material_id = Column(Integer, primary_key=True, autoincrement=True)
    material_name = Column(String(50), unique=True, nullable=False, index=True)
    material_category = Column(String(30))

    # Environmental Impact Factors
    co2_per_kg = Column(Numeric(10, 3), nullable=False)
    water_liters_per_kg = Column(Numeric(10, 1))
    energy_mj_per_kg = Column(Numeric(10, 2))
    land_use_m2_per_kg = Column(Numeric(10, 4))

    # Processing Stage Multipliers
    spinning_multiplier = Column(Numeric(5, 3), default=Decimal('0.05'))
    weaving_multiplier = Column(Numeric(5, 3), default=Decimal('0.08'))
    dyeing_multiplier = Column(Numeric(5, 3), default=Decimal('0.25'))
    finishing_multiplier = Column(Numeric(5, 3), default=Decimal('0.10'))

    # Geographic Variations
    production_region = Column(String(50))

    # Metadata
    data_quality = Column(String(20))
    last_updated = Column(Date, nullable=False)
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_material_name', 'material_name'),
    )

    def __repr__(self):
        return f"<MaterialReference(material_name='{self.material_name}', " \
               f"category='{self.material_category}', co2_per_kg={self.co2_per_kg})>"

    def to_dict(self):
        return {
            'material_id': self.material_id,
            'material_name': self.material_name,
            'material_category': self.material_category,
            'co2_per_kg': float(self.co2_per_kg) if self.co2_per_kg else None,
            'water_liters_per_kg': float(self.water_liters_per_kg) if self.water_liters_per_kg else None,
            'energy_mj_per_kg': float(self.energy_mj_per_kg) if self.energy_mj_per_kg else None,
            'land_use_m2_per_kg': float(self.land_use_m2_per_kg) if self.land_use_m2_per_kg else None,
            'spinning_multiplier': float(self.spinning_multiplier) if self.spinning_multiplier else None,
            'weaving_multiplier': float(self.weaving_multiplier) if self.weaving_multiplier else None,
            'dyeing_multiplier': float(self.dyeing_multiplier) if self.dyeing_multiplier else None,
            'finishing_multiplier': float(self.finishing_multiplier) if self.finishing_multiplier else None,
            'production_region': self.production_region,
            'data_quality': self.data_quality,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }