from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Index
from sqlalchemy import Numeric
from sqlalchemy.sql import func
from ..database import Base


class CalculationParameter(Base):
    __tablename__ = 'calculation_parameters'

    param_id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_name = Column(String(100), unique=True, nullable=False)
    parameter_value = Column(Numeric(10, 4), nullable=False)
    unit = Column(String(50))
    description = Column(Text)
    last_updated = Column(Date)

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_parameter_name', 'parameter_name'),
    )

    def __repr__(self):
        return f"<CalculationParameter(parameter_name='{self.parameter_name}', " \
               f"parameter_value={self.parameter_value}, unit='{self.unit}')>"

    def to_dict(self):
        return {
            'param_id': self.param_id,
            'parameter_name': self.parameter_name,
            'parameter_value': float(self.parameter_value) if self.parameter_value else None,
            'unit': self.unit,
            'description': self.description,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_parameter_value(cls, session, parameter_name: str, default_value: Decimal = None):
        """Get parameter value by name, with optional default"""
        param = session.query(cls).filter_by(parameter_name=parameter_name).first()
        if param:
            return param.parameter_value
        return default_value