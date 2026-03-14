from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Index, JSON, ForeignKey, UniqueConstraint
from sqlalchemy import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class UserImpactStatistics(Base):
    __tablename__ = 'user_impact_statistics'

    user_stat_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), unique=True, nullable=False)

    # Swap Counts
    total_swaps_completed = Column(Integer, default=0)
    total_clothing_given = Column(Integer, default=0)
    total_clothing_received = Column(Integer, default=0)

    # Cumulative Environmental Impact
    cumulative_co2_saved_kg = Column(Numeric(12, 3), default=Decimal('0'))
    cumulative_water_saved_liters = Column(Numeric(15, 1), default=Decimal('0'))
    cumulative_energy_saved_kwh = Column(Numeric(12, 2), default=Decimal('0'))

    # Equivalents (Pre-calculated for performance)
    equivalent_km_not_driven = Column(Numeric(12, 2))
    equivalent_trees_planted = Column(Numeric(10, 2))
    equivalent_days_drinking_water = Column(Numeric(10, 1))
    equivalent_smartphone_charges = Column(Integer)

    # Breakdown by Category
    top_category_swapped = Column(String(50))
    top_category_count = Column(Integer)
    top_category_impact_co2 = Column(Numeric(10, 3))

    # Timeline Data (JSON for charts)
    monthly_impact_timeline = Column(JSON)

    # Rankings/Gamification
    platform_percentile = Column(Numeric(5, 2))
    impact_rank = Column(Integer)
    badges_earned = Column(JSON, default=lambda: [])

    # Statistics Window
    stats_period = Column(String(20), default='all_time')
    last_updated = Column(DateTime, default=func.now())

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship('User', back_populates='statistics')

    # Indexes
    __table_args__ = (
        Index('ix_user_impact_statistics_user_id', 'user_id'),
        Index('ix_user_impact_statistics_impact_rank', 'impact_rank'),
        Index('ix_user_impact_statistics_cumulative_co2_saved_kg', 'cumulative_co2_saved_kg'),
        UniqueConstraint('user_id', name='uq_user_impact_statistics_user_id'),
    )

    def __repr__(self):
        return f"<UserImpactStatistics(user_stat_id={self.user_stat_id}, " \
               f"user_id={self.user_id}, cumulative_co2_saved_kg={self.cumulative_co2_saved_kg})>"

    def to_dict(self):
        return {
            'user_stat_id': self.user_stat_id,
            'user_id': self.user_id,
            'total_swaps_completed': self.total_swaps_completed,
            'total_clothing_given': self.total_clothing_given,
            'total_clothing_received': self.total_clothing_received,
            'cumulative_co2_saved_kg': float(self.cumulative_co2_saved_kg) if self.cumulative_co2_saved_kg else None,
            'cumulative_water_saved_liters': float(self.cumulative_water_saved_liters) if self.cumulative_water_saved_liters else None,
            'cumulative_energy_saved_kwh': float(self.cumulative_energy_saved_kwh) if self.cumulative_energy_saved_kwh else None,
            'equivalent_km_not_driven': float(self.equivalent_km_not_driven) if self.equivalent_km_not_driven else None,
            'equivalent_trees_planted': float(self.equivalent_trees_planted) if self.equivalent_trees_planted else None,
            'equivalent_days_drinking_water': float(self.equivalent_days_drinking_water) if self.equivalent_days_drinking_water else None,
            'equivalent_smartphone_charges': self.equivalent_smartphone_charges,
            'top_category_swapped': self.top_category_swapped,
            'top_category_count': self.top_category_count,
            'top_category_impact_co2': float(self.top_category_impact_co2) if self.top_category_impact_co2 else None,
            'monthly_impact_timeline': self.monthly_impact_timeline,
            'platform_percentile': float(self.platform_percentile) if self.platform_percentile else None,
            'impact_rank': self.impact_rank,
            'badges_earned': self.badges_earned,
            'stats_period': self.stats_period,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def update_from_swaps(self, session):
        """Recalculate all stats from user's swaps"""
        from .swap import Swap
        from .impact import SwapEnvironmentalImpact
        
        # Query all completed swaps for this user
        completed_swaps = session.query(Swap).filter(
            (Swap.user1_id == self.user_id) | (Swap.user2_id == self.user_id),
            Swap.status == 'completed'
        ).all()
        
        # Reset counters
        self.total_swaps_completed = len(completed_swaps)
        self.total_clothing_given = 0
        self.total_clothing_received = 0
        self.cumulative_co2_saved_kg = Decimal('0')
        self.cumulative_water_saved_liters = Decimal('0')
        self.cumulative_energy_saved_kwh = Decimal('0')
        
        # Sum up impacts from all swaps
        for swap in completed_swaps:
            if swap.user1_id == self.user_id:
                self.total_clothing_given += 1
            if swap.user2_id == self.user_id:
                self.total_clothing_received += 1
            
            # Add environmental impact if available
            if swap.environmental_impact:
                impact = swap.environmental_impact
                if impact.net_swap_impact_co2:
                    # User gets half credit for each swap
                    self.cumulative_co2_saved_kg += impact.net_swap_impact_co2 / 2
                if impact.total_swap_avoided_water:
                    self.cumulative_water_saved_liters += impact.total_swap_avoided_water / 2
                if impact.total_swap_avoided_energy:
                    self.cumulative_energy_saved_kwh += impact.total_swap_avoided_energy / 2
        
        # Calculate equivalents
        co2_kg = float(self.cumulative_co2_saved_kg)
        water_liters = float(self.cumulative_water_saved_liters)
        energy_kwh = float(self.cumulative_energy_saved_kwh)
        
        self.equivalent_km_not_driven = Decimal(str(co2_kg * 5.26))
        self.equivalent_trees_planted = Decimal(str(co2_kg / 21))
        self.equivalent_days_drinking_water = Decimal(str(water_liters / 2))
        self.equivalent_smartphone_charges = int(energy_kwh * 125)
        
        self.last_updated = func.now()
        session.commit()

    def calculate_percentile(self, session):
        """Calculate user's percentile ranking"""
        # Count users with lower cumulative CO2 savings
        lower_users = session.query(UserImpactStatistics).filter(
            UserImpactStatistics.cumulative_co2_saved_kg < self.cumulative_co2_saved_kg
        ).count()
        
        # Count total users with statistics
        total_users = session.query(UserImpactStatistics).count()
        
        if total_users > 0:
            self.platform_percentile = Decimal(str((lower_users / total_users) * 100))
        else:
            self.platform_percentile = Decimal('0')
        
        session.commit()


class PlatformImpactStatistics(Base):
    __tablename__ = 'platform_impact_statistics'

    platform_stat_id = Column(Integer, primary_key=True, autoincrement=True)
    stat_period = Column(String(20), nullable=False)
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=True)

    # User Metrics
    total_active_users = Column(Integer)
    new_users_this_period = Column(Integer)
    users_with_swaps = Column(Integer)

    # Swap Metrics
    total_swaps_completed = Column(Integer)
    total_clothing_swapped = Column(Integer)
    swaps_this_period = Column(Integer)

    # Environmental Impact
    total_co2_saved_kg = Column(Numeric(15, 3))
    total_co2_saved_tons = Column(Numeric(12, 3))
    total_water_saved_liters = Column(Numeric(18, 1))
    total_water_saved_million_liters = Column(Numeric(12, 3))
    total_energy_saved_kwh = Column(Numeric(15, 2))
    total_energy_saved_mwh = Column(Numeric(12, 2))

    # Equivalents
    equivalent_km_not_driven = Column(Numeric(15, 2))
    equivalent_cars_off_road = Column(Integer)
    equivalent_trees_planted = Column(Numeric(12, 2))
    equivalent_olympic_pools = Column(Numeric(8, 2))

    # Category Breakdown
    top_categories_swapped = Column(JSON)

    # Geographic Distribution
    top_cities = Column(JSON)
    top_countries = Column(JSON)

    # Growth Metrics
    growth_rate_swaps = Column(Numeric(8, 2))
    growth_rate_users = Column(Numeric(8, 2))
    growth_rate_impact = Column(Numeric(8, 2))

    # Average Metrics
    avg_co2_per_swap = Column(Numeric(10, 3))
    avg_swaps_per_user = Column(Numeric(10, 2))
    avg_impact_per_user = Column(Numeric(10, 3))

    # Timestamps
    calculated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_platform_impact_statistics_period_start_date', 'period_start_date'),
        UniqueConstraint('stat_period', 'period_start_date', name='uq_platform_impact_statistics_period_start'),
    )

    def __repr__(self):
        return f"<PlatformImpactStatistics(platform_stat_id={self.platform_stat_id}, " \
               f"stat_period='{self.stat_period}', period_start_date={self.period_start_date})>"

    def to_dict(self):
        return {
            'platform_stat_id': self.platform_stat_id,
            'stat_period': self.stat_period,
            'period_start_date': self.period_start_date.isoformat() if self.period_start_date else None,
            'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
            'total_active_users': self.total_active_users,
            'new_users_this_period': self.new_users_this_period,
            'users_with_swaps': self.users_with_swaps,
            'total_swaps_completed': self.total_swaps_completed,
            'total_clothing_swapped': self.total_clothing_swapped,
            'swaps_this_period': self.swaps_this_period,
            'total_co2_saved_kg': float(self.total_co2_saved_kg) if self.total_co2_saved_kg else None,
            'total_co2_saved_tons': float(self.total_co2_saved_tons) if self.total_co2_saved_tons else None,
            'total_water_saved_liters': float(self.total_water_saved_liters) if self.total_water_saved_liters else None,
            'total_water_saved_million_liters': float(self.total_water_saved_million_liters) if self.total_water_saved_million_liters else None,
            'total_energy_saved_kwh': float(self.total_energy_saved_kwh) if self.total_energy_saved_kwh else None,
            'total_energy_saved_mwh': float(self.total_energy_saved_mwh) if self.total_energy_saved_mwh else None,
            'equivalent_km_not_driven': float(self.equivalent_km_not_driven) if self.equivalent_km_not_driven else None,
            'equivalent_cars_off_road': self.equivalent_cars_off_road,
            'equivalent_trees_planted': float(self.equivalent_trees_planted) if self.equivalent_trees_planted else None,
            'equivalent_olympic_pools': float(self.equivalent_olympic_pools) if self.equivalent_olympic_pools else None,
            'top_categories_swapped': self.top_categories_swapped,
            'top_cities': self.top_cities,
            'top_countries': self.top_countries,
            'growth_rate_swaps': float(self.growth_rate_swaps) if self.growth_rate_swaps else None,
            'growth_rate_users': float(self.growth_rate_users) if self.growth_rate_users else None,
            'growth_rate_impact': float(self.growth_rate_impact) if self.growth_rate_impact else None,
            'avg_co2_per_swap': float(self.avg_co2_per_swap) if self.avg_co2_per_swap else None,
            'avg_swaps_per_user': float(self.avg_swaps_per_user) if self.avg_swaps_per_user else None,
            'avg_impact_per_user': float(self.avg_impact_per_user) if self.avg_impact_per_user else None,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def calculate_for_period(cls, session, period: str, start_date: date, end_date: date = None):
        """Calculate statistics for given period"""
        from .user import User
        from .swap import Swap
        from .impact import SwapEnvironmentalImpact
        
        # Create or get existing record
        stats = session.query(cls).filter_by(
            stat_period=period,
            period_start_date=start_date
        ).first()
        
        if not stats:
            stats = cls(
                stat_period=period,
                period_start_date=start_date,
                period_end_date=end_date
            )
            session.add(stats)
        else:
            stats.period_end_date = end_date
        
        # Calculate user metrics
        if end_date:
            stats.total_active_users = session.query(User).filter(
                User.created_at <= end_date
            ).count()
            stats.new_users_this_period = session.query(User).filter(
                User.created_at >= start_date,
                User.created_at <= end_date
            ).count()
        else:
            stats.total_active_users = session.query(User).count()
            stats.new_users_this_period = 0
        
        # Calculate swap metrics
        swap_filter = [Swap.status == 'completed']
        if end_date:
            swap_filter.append(Swap.completed_date <= end_date)
        
        stats.total_swaps_completed = session.query(Swap).filter(*swap_filter).count()
        stats.total_clothing_swapped = stats.total_swaps_completed * 2  # 2 items per swap
        
        # Period-specific swaps
        if end_date:
            stats.swaps_this_period = session.query(Swap).filter(
                Swap.status == 'completed',
                Swap.completed_date >= start_date,
                Swap.completed_date <= end_date
            ).count()
        else:
            stats.swaps_this_period = 0
        
        # Calculate environmental impact
        total_co2 = Decimal('0')
        total_water = Decimal('0')
        total_energy = Decimal('0')
        
        impacts = session.query(SwapEnvironmentalImpact).join(Swap).filter(*swap_filter).all()
        for impact in impacts:
            if impact.net_swap_impact_co2:
                total_co2 += impact.net_swap_impact_co2
            if impact.total_swap_avoided_water:
                total_water += impact.total_swap_avoided_water
            if impact.total_swap_avoided_energy:
                total_energy += impact.total_swap_avoided_energy
        
        stats.total_co2_saved_kg = total_co2
        stats.total_co2_saved_tons = total_co2 / 1000
        stats.total_water_saved_liters = total_water
        stats.total_water_saved_million_liters = total_water / 1000000
        stats.total_energy_saved_kwh = total_energy
        stats.total_energy_saved_mwh = total_energy / 1000
        
        # Calculate equivalents
        co2_kg = float(total_co2)
        water_liters = float(total_water)
        
        stats.equivalent_km_not_driven = Decimal(str(co2_kg * 5.26))
        stats.equivalent_cars_off_road = int(co2_kg * 5.26 / 15000)  # 15,000 km/year per car
        stats.equivalent_trees_planted = Decimal(str(co2_kg / 21))
        stats.equivalent_olympic_pools = Decimal(str(water_liters / 2500000))  # 2.5M liters per pool
        
        # Calculate averages
        if stats.total_swaps_completed > 0:
            stats.avg_co2_per_swap = total_co2 / stats.total_swaps_completed
            stats.avg_swaps_per_user = Decimal(str(stats.total_swaps_completed / stats.total_active_users)) if stats.total_active_users > 0 else Decimal('0')
            stats.avg_impact_per_user = total_co2 / stats.total_active_users if stats.total_active_users > 0 else Decimal('0')
        
        stats.calculated_at = func.now()
        session.commit()
        
        return stats