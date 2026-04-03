from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class Notification(Base):
    __tablename__ = 'notifications'

    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    type = Column(String(50), nullable=False)   # swap_sent, swap_accepted, swap_declined, swap_cancelled
    title = Column(String(200), nullable=False)
    message = Column(String(500), nullable=False)
    swap_id = Column(Integer, ForeignKey('swaps.swap_id'), nullable=True)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
