from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    
    # Stripe Connect
    stripe_account_id = Column(String(255), nullable=True, index=True)

    # Profile Information
    display_name = Column(String(100))
    location = Column(String(100))
    birth_date = Column(Date, nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    postal_code = Column(String(10), nullable=True)
    country = Column(String(2), nullable=True, default='US')
    joined_date = Column(Date, default=func.current_date())

    # Preferences
    preferred_units = Column(String(10), default='metric')
    email_notifications = Column(Boolean, default=True)

    # Gamification
    total_swaps = Column(Integer, default=0)
    impact_points = Column(Integer, default=0)
    badges = Column(JSON, default=lambda: [])

    # Sales tracking
    total_sales = Column(Integer, default=0)
    total_purchases = Column(Integer, default=0)

    # Privacy Settings
    profile_public = Column(Boolean, default=True)
    share_stats = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    clothing_items = relationship('ClothingItem', back_populates='owner', cascade='all, delete-orphan')
    statistics = relationship('UserImpactStatistics', back_populates='user', uselist=False)
    swaps_initiated = relationship('Swap', foreign_keys='Swap.user1_id', back_populates='user1')
    swaps_received = relationship('Swap', foreign_keys='Swap.user2_id', back_populates='user2')
    sales_as_seller = relationship('Sale', foreign_keys='Sale.seller_id', back_populates='seller')
    sales_as_buyer = relationship('Sale', foreign_keys='Sale.buyer_id', back_populates='buyer')
    reviews_written = relationship('Review', back_populates='reviewer', cascade='all, delete-orphan')
    cart_items = relationship('CartItem', back_populates='user', cascade='all, delete-orphan')


    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

    def to_dict(self, exclude_sensitive=True):
        """Convert to dictionary, optionally excluding sensitive information"""
        data = {
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'location': self.location,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'phone_number': self.phone_number,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'joined_date': self.joined_date.isoformat() if self.joined_date else None,
            'preferred_units': self.preferred_units,
            'email_notifications': self.email_notifications,
            'total_swaps': self.total_swaps,
            'impact_points': self.impact_points,
            'badges': self.badges,
            'total_sales': self.total_sales,
            'total_purchases': self.total_purchases,
            'profile_public': self.profile_public,
            'share_stats': self.share_stats,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if not exclude_sensitive:
            data['email'] = self.email

        return data

    def add_badge(self, badge_id: str):
        """Add a badge to the user's collection"""
        if self.badges is None:
            self.badges = []
        if badge_id not in self.badges:
            self.badges = self.badges + [badge_id]

    def has_badge(self, badge_id: str) -> bool:
        """Check if user has a specific badge"""
        return badge_id in (self.badges or [])