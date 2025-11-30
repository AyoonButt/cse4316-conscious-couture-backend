
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Index, ForeignKey, UniqueConstraint
from sqlalchemy import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class ClothingEnvironmentalImpact(Base):
    __tablename__ = 'clothing_environmental_impact'

    impact_id = Column(Integer, primary_key=True, autoincrement=True)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), unique=True, nullable=False)

    # NEW ITEM IMPACT (What would be produced if buying new)
    new_material_co2 = Column(Numeric(10, 3))
    new_manufacturing_co2 = Column(Numeric(10, 3))
    new_dyeing_co2 = Column(Numeric(10, 3))
    new_transport_co2 = Column(Numeric(10, 3))
    new_packaging_co2 = Column(Numeric(10, 3))
    new_use_phase_co2 = Column(Numeric(10, 3))
    new_end_of_life_co2 = Column(Numeric(10, 3))
    new_total_co2 = Column(Numeric(10, 3), nullable=False)

    # Water Impact (New)
    new_material_water = Column(Numeric(12, 1))
    new_processing_water = Column(Numeric(12, 1))
    new_dyeing_water = Column(Numeric(12, 1))
    new_total_water = Column(Numeric(12, 1))

    # Energy Impact (New)
    new_total_energy_mj = Column(Numeric(10, 2))
    new_total_energy_kwh = Column(Numeric(10, 2))

    # REUSE IMPACT (Platform overhead)
    reuse_collection_co2 = Column(Numeric(10, 3), default=Decimal('0.05'))
    reuse_sorting_co2 = Column(Numeric(10, 3), default=Decimal('0.02'))
    reuse_transport_co2 = Column(Numeric(10, 3), default=Decimal('0.02'))
    reuse_platform_co2 = Column(Numeric(10, 3), default=Decimal('0.01'))
    reuse_total_co2 = Column(Numeric(10, 3), default=Decimal('0.08'))

    # AVOIDED IMPACT (Key metrics shown to users)
    avoided_production_co2 = Column(Numeric(10, 3))
    replacement_factor = Column(Numeric(5, 3), default=Decimal('0.70'))
    net_avoided_co2 = Column(Numeric(10, 3), nullable=False)
    net_avoided_water = Column(Numeric(12, 1))
    net_avoided_energy_kwh = Column(Numeric(10, 2))

    # Percentage Reduction
    impact_reduction_percentage = Column(Numeric(5, 2))

    # Calculation Metadata
    calculation_version = Column(String(10))
    calculation_date = Column(DateTime, default=func.now())
    data_quality_score = Column(String(20))

    # Lifecycle Assumptions Used
    assumed_wears = Column(Integer)
    assumed_washes = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    clothing_item = relationship('ClothingItem', back_populates='environmental_impact')

    # Indexes
    __table_args__ = (
        Index('ix_clothing_environmental_impact_clothing_id', 'clothing_id'),
        UniqueConstraint('clothing_id', name='uq_clothing_environmental_impact_clothing_id'),
    )

    def __repr__(self):
        return f"<ClothingEnvironmentalImpact(impact_id={self.impact_id}, " \
               f"clothing_id={self.clothing_id}, net_avoided_co2={self.net_avoided_co2})>"

    def to_dict(self):
        return {
            'impact_id': self.impact_id,
            'clothing_id': self.clothing_id,
            'new_material_co2': float(self.new_material_co2) if self.new_material_co2 else None,
            'new_manufacturing_co2': float(self.new_manufacturing_co2) if self.new_manufacturing_co2 else None,
            'new_dyeing_co2': float(self.new_dyeing_co2) if self.new_dyeing_co2 else None,
            'new_transport_co2': float(self.new_transport_co2) if self.new_transport_co2 else None,
            'new_packaging_co2': float(self.new_packaging_co2) if self.new_packaging_co2 else None,
            'new_use_phase_co2': float(self.new_use_phase_co2) if self.new_use_phase_co2 else None,
            'new_end_of_life_co2': float(self.new_end_of_life_co2) if self.new_end_of_life_co2 else None,
            'new_total_co2': float(self.new_total_co2) if self.new_total_co2 else None,
            'new_material_water': float(self.new_material_water) if self.new_material_water else None,
            'new_processing_water': float(self.new_processing_water) if self.new_processing_water else None,
            'new_dyeing_water': float(self.new_dyeing_water) if self.new_dyeing_water else None,
            'new_total_water': float(self.new_total_water) if self.new_total_water else None,
            'new_total_energy_mj': float(self.new_total_energy_mj) if self.new_total_energy_mj else None,
            'new_total_energy_kwh': float(self.new_total_energy_kwh) if self.new_total_energy_kwh else None,
            'reuse_collection_co2': float(self.reuse_collection_co2) if self.reuse_collection_co2 else None,
            'reuse_sorting_co2': float(self.reuse_sorting_co2) if self.reuse_sorting_co2 else None,
            'reuse_transport_co2': float(self.reuse_transport_co2) if self.reuse_transport_co2 else None,
            'reuse_platform_co2': float(self.reuse_platform_co2) if self.reuse_platform_co2 else None,
            'reuse_total_co2': float(self.reuse_total_co2) if self.reuse_total_co2 else None,
            'avoided_production_co2': float(self.avoided_production_co2) if self.avoided_production_co2 else None,
            'replacement_factor': float(self.replacement_factor) if self.replacement_factor else None,
            'net_avoided_co2': float(self.net_avoided_co2) if self.net_avoided_co2 else None,
            'net_avoided_water': float(self.net_avoided_water) if self.net_avoided_water else None,
            'net_avoided_energy_kwh': float(self.net_avoided_energy_kwh) if self.net_avoided_energy_kwh else None,
            'impact_reduction_percentage': float(self.impact_reduction_percentage) if self.impact_reduction_percentage else None,
            'calculation_version': self.calculation_version,
            'calculation_date': self.calculation_date.isoformat() if self.calculation_date else None,
            'data_quality_score': self.data_quality_score,
            'assumed_wears': self.assumed_wears,
            'assumed_washes': self.assumed_washes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def recalculate(self, session):
        """Recalculate all impact metrics"""
        # This would call the impact calculation service
        # For now, this is a placeholder
        self.calculation_date = func.now()
        session.commit()

    def get_equivalents(self) -> dict:
        """Calculate equivalents (km, trees, etc.)"""
        if not self.net_avoided_co2:
            return {}
        
        co2_kg = float(self.net_avoided_co2)
        water_liters = float(self.net_avoided_water) if self.net_avoided_water else 0
        energy_kwh = float(self.net_avoided_energy_kwh) if self.net_avoided_energy_kwh else 0
        
        return {
            'km_not_driven': co2_kg * 5.26,  # Average car emits 0.19 kg CO2/km
            'trees_planted': co2_kg / 21,     # Tree absorbs ~21 kg CO2/year
            'days_drinking_water': water_liters / 2,  # 2L per day average
            'smartphone_charges': int(energy_kwh * 125)  # ~8Wh per smartphone charge
        }


class SwapEnvironmentalImpact(Base):
    __tablename__ = 'swap_environmental_impact'

    swap_impact_id = Column(Integer, primary_key=True, autoincrement=True)
    swap_id = Column(Integer, ForeignKey('swaps.swap_id'), unique=True, nullable=False)

    # User 1 Clothing Impact
    user1_clothing_avoided_co2 = Column(Numeric(10, 3))
    user1_clothing_avoided_water = Column(Numeric(12, 1))
    user1_clothing_avoided_energy = Column(Numeric(10, 2))

    # User 2 Clothing Impact
    user2_clothing_avoided_co2 = Column(Numeric(10, 3))
    user2_clothing_avoided_water = Column(Numeric(12, 1))
    user2_clothing_avoided_energy = Column(Numeric(10, 2))

    # Combined Swap Impact
    total_swap_avoided_co2 = Column(Numeric(10, 3))
    total_swap_avoided_water = Column(Numeric(12, 1))
    total_swap_avoided_energy = Column(Numeric(10, 2))

    # Transportation Overhead (if applicable)
    swap_transport_co2 = Column(Numeric(10, 3))

    # Net Impact (avoided - transport overhead)
    net_swap_impact_co2 = Column(Numeric(10, 3))

    # Timestamps
    calculated_at = Column(DateTime, default=func.now())

    # Relationships
    swap = relationship('Swap', back_populates='environmental_impact')

    # Indexes
    __table_args__ = (
        Index('ix_swap_environmental_impact_swap_id', 'swap_id'),
        UniqueConstraint('swap_id', name='uq_swap_environmental_impact_swap_id'),
    )

    def __repr__(self):
        return f"<SwapEnvironmentalImpact(swap_impact_id={self.swap_impact_id}, " \
               f"swap_id={self.swap_id}, net_swap_impact_co2={self.net_swap_impact_co2})>"

    def to_dict(self):
        return {
            'swap_impact_id': self.swap_impact_id,
            'swap_id': self.swap_id,
            'user1_clothing_avoided_co2': float(self.user1_clothing_avoided_co2) if self.user1_clothing_avoided_co2 else None,
            'user1_clothing_avoided_water': float(self.user1_clothing_avoided_water) if self.user1_clothing_avoided_water else None,
            'user1_clothing_avoided_energy': float(self.user1_clothing_avoided_energy) if self.user1_clothing_avoided_energy else None,
            'user2_clothing_avoided_co2': float(self.user2_clothing_avoided_co2) if self.user2_clothing_avoided_co2 else None,
            'user2_clothing_avoided_water': float(self.user2_clothing_avoided_water) if self.user2_clothing_avoided_water else None,
            'user2_clothing_avoided_energy': float(self.user2_clothing_avoided_energy) if self.user2_clothing_avoided_energy else None,
            'total_swap_avoided_co2': float(self.total_swap_avoided_co2) if self.total_swap_avoided_co2 else None,
            'total_swap_avoided_water': float(self.total_swap_avoided_water) if self.total_swap_avoided_water else None,
            'total_swap_avoided_energy': float(self.total_swap_avoided_energy) if self.total_swap_avoided_energy else None,
            'swap_transport_co2': float(self.swap_transport_co2) if self.swap_transport_co2 else None,
            'net_swap_impact_co2': float(self.net_swap_impact_co2) if self.net_swap_impact_co2 else None,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }