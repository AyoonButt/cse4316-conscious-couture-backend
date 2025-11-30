from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index, JSON, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class ClothingItem(Base):
    __tablename__ = 'clothing_items'

    clothing_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)

    # Basic Information
    clothing_type = Column(String(50), nullable=False, index=True)
    brand = Column(String(100), index=True)
    brand_id = Column(Integer, ForeignKey('brands_sustainability.brand_id'), nullable=True)
    description = Column(Text)
    size = Column(String(20))
    color = Column(String(50))
    condition = Column(String(20), nullable=False)

    # Material Composition (CRITICAL for calculations)
    material_composition = Column(JSON, nullable=False)
    composition_verified = Column(Boolean, default=False)
    composition_verification_count = Column(Integer, default=0)

    # Physical Specifications
    weight_grams = Column(Integer)
    weight_estimated = Column(Boolean, default=True)


    # Swap Status
    status = Column(String(20), default='available', index=True)
    times_swapped = Column(Integer, default=0)

    # Photos
    primary_image_url = Column(String(255))
    additional_images = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship('User', back_populates='clothing_items')
    brand_info = relationship('BrandSustainability', back_populates='clothing_items')
    environmental_impact = relationship('ClothingEnvironmentalImpact', back_populates='clothing_item', uselist=False)
    composition_contributions = relationship('MaterialCompositionContribution', back_populates='clothing_item', cascade='all, delete-orphan')
    swaps_as_item1 = relationship('Swap', foreign_keys='Swap.user1_clothing_id', back_populates='user1_clothing')
    swaps_as_item2 = relationship('Swap', foreign_keys='Swap.user2_clothing_id', back_populates='user2_clothing')

    # Indexes and Constraints
    __table_args__ = (
        Index('ix_clothing_items_owner_user_id', 'owner_user_id'),
        Index('ix_clothing_items_clothing_type', 'clothing_type'),
        Index('ix_clothing_items_brand', 'brand'),
        Index('ix_clothing_items_brand_id', 'brand_id'),
        Index('ix_clothing_items_status', 'status'),
        CheckConstraint("material_composition IS NOT NULL", name='material_composition_not_null'),
    )

    def __repr__(self):
        return f"<ClothingItem(clothing_id={self.clothing_id}, " \
               f"clothing_type='{self.clothing_type}', brand='{self.brand}', " \
               f"owner_user_id={self.owner_user_id})>"

    def to_dict(self):
        return {
            'clothing_id': self.clothing_id,
            'owner_user_id': self.owner_user_id,
            'clothing_type': self.clothing_type,
            'brand': self.brand,
            'brand_id': self.brand_id,
            'description': self.description,
            'size': self.size,
            'color': self.color,
            'condition': self.condition,
            'material_composition': self.material_composition,
            'composition_verified': self.composition_verified,
            'composition_verification_count': self.composition_verification_count,
            'weight_grams': self.weight_grams,
            'weight_estimated': self.weight_estimated,
            'status': self.status,
            'times_swapped': self.times_swapped,
            'primary_image_url': self.primary_image_url,
            'additional_images': self.additional_images,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_primary_material(self) -> str:
        """Get material with highest percentage"""
        if not self.material_composition:
            return None
        return max(self.material_composition.items(), key=lambda x: x[1])[0]

    def validate_composition(self) -> bool:
        """Validate composition sums to 100"""
        if not self.material_composition:
            return False
        total = sum(self.material_composition.values())
        return abs(total - 100) < 0.1  # Allow for small rounding errors

    def estimate_weight(self, session) -> int:
        """Estimate weight from clothing_type if not provided"""
        if self.weight_grams:
            return self.weight_grams
        
        from .clothing_type import ClothingTypeReference
        clothing_type_ref = session.query(ClothingTypeReference).filter_by(
            clothing_type=self.clothing_type
        ).first()
        
        if clothing_type_ref:
            return clothing_type_ref.typical_weight_grams
        
        return None


class MaterialCompositionContribution(Base):
    __tablename__ = 'material_composition_contributions'

    contribution_id = Column(Integer, primary_key=True, autoincrement=True)
    clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)
    contributor_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)

    # Contributed Data
    material_composition = Column(JSON, nullable=False)
    confidence_level = Column(String(20))

    # Verification
    verified_by_others = Column(Integer, default=0)
    flagged_incorrect = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationships
    clothing_item = relationship('ClothingItem', back_populates='composition_contributions')
    contributor = relationship('User')

    # Indexes
    __table_args__ = (
        Index('ix_material_composition_contributions_clothing_id', 'clothing_id'),
        Index('ix_material_composition_contributions_contributor_user_id', 'contributor_user_id'),
        Index('ix_material_composition_contributions_clothing_contributor', 'clothing_id', 'contributor_user_id'),
    )

    def __repr__(self):
        return f"<MaterialCompositionContribution(contribution_id={self.contribution_id}, " \
               f"clothing_id={self.clothing_id}, contributor_user_id={self.contributor_user_id})>"

    def to_dict(self):
        return {
            'contribution_id': self.contribution_id,
            'clothing_id': self.clothing_id,
            'contributor_user_id': self.contributor_user_id,
            'material_composition': self.material_composition,
            'confidence_level': self.confidence_level,
            'verified_by_others': self.verified_by_others,
            'flagged_incorrect': self.flagged_incorrect,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }