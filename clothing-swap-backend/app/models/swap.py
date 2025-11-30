from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Index, ForeignKey, CheckConstraint
from sqlalchemy import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Swap(Base):
    __tablename__ = 'swaps'

    swap_id = Column(Integer, primary_key=True, autoincrement=True)

    # Swap Participants
    user1_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)

    # Clothing Items Exchanged
    user1_clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)
    user2_clothing_id = Column(Integer, ForeignKey('clothing_items.clothing_id'), nullable=False)

    # Swap Details
    swap_type = Column(String(20), default='direct')
    swap_location = Column(String(100))
    swap_event_id = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default='pending', index=True)
    completed_date = Column(Date, nullable=True)

    # Transportation (for impact calculation)
    transport_distance_km = Column(Numeric(6, 2))
    transport_method = Column(String(30))

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user1 = relationship('User', foreign_keys=[user1_id], back_populates='swaps_initiated')
    user2 = relationship('User', foreign_keys=[user2_id], back_populates='swaps_received')
    user1_clothing = relationship('ClothingItem', foreign_keys=[user1_clothing_id], back_populates='swaps_as_item1')
    user2_clothing = relationship('ClothingItem', foreign_keys=[user2_clothing_id], back_populates='swaps_as_item2')
    environmental_impact = relationship('SwapEnvironmentalImpact', back_populates='swap', uselist=False)

    # Indexes and Constraints
    __table_args__ = (
        Index('ix_swaps_user1_id', 'user1_id'),
        Index('ix_swaps_user2_id', 'user2_id'),
        Index('ix_swaps_user1_clothing_id', 'user1_clothing_id'),
        Index('ix_swaps_user2_clothing_id', 'user2_clothing_id'),
        Index('ix_swaps_user1_user2', 'user1_id', 'user2_id'),
        Index('ix_swaps_status', 'status'),
        Index('ix_swaps_completed_date', 'completed_date'),
        CheckConstraint('user1_id != user2_id', name='different_users'),
        CheckConstraint('user1_clothing_id != user2_clothing_id', name='different_clothing_items'),
    )

    def __repr__(self):
        return f"<Swap(swap_id={self.swap_id}, " \
               f"user1_id={self.user1_id}, user2_id={self.user2_id}, " \
               f"status='{self.status}')>"

    def to_dict(self):
        return {
            'swap_id': self.swap_id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'user1_clothing_id': self.user1_clothing_id,
            'user2_clothing_id': self.user2_clothing_id,
            'swap_type': self.swap_type,
            'swap_location': self.swap_location,
            'swap_event_id': self.swap_event_id,
            'status': self.status,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'transport_distance_km': float(self.transport_distance_km) if self.transport_distance_km else None,
            'transport_method': self.transport_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def complete_swap(self, session):
        """Mark swap as completed and update related records"""
        self.status = 'completed'
        self.completed_date = func.current_date()
        
        # Update clothing items ownership
        if self.user1_clothing and self.user2_clothing:
            # Swap ownership
            original_user1_id = self.user1_clothing.owner_user_id
            original_user2_id = self.user2_clothing.owner_user_id
            
            self.user1_clothing.owner_user_id = original_user2_id
            self.user2_clothing.owner_user_id = original_user1_id
            
            # Update times_swapped counter
            self.user1_clothing.times_swapped += 1
            self.user2_clothing.times_swapped += 1
            
            # Update clothing status
            self.user1_clothing.status = 'swapped'
            self.user2_clothing.status = 'swapped'
        
        # Update user swap counts
        if self.user1:
            self.user1.total_swaps += 1
        if self.user2:
            self.user2.total_swaps += 1
        
        session.commit()

    def calculate_transport_impact(self) -> float:
        """Calculate CO2 from transportation"""
        if not self.transport_distance_km:
            return 0.0
        
        # CO2 emissions per km by transport method (kg CO2-eq per km)
        transport_emissions = {
            'walking': 0.0,
            'bike': 0.0,
            'car': 0.21,  # Average car
            'public_transport': 0.05,
            'bus': 0.08,
            'train': 0.04,
            'motorcycle': 0.11
        }
        
        emission_factor = transport_emissions.get(self.transport_method, 0.15)  # Default
        return float(self.transport_distance_km) * emission_factor