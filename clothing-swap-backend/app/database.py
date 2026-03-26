from sqlalchemy import create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_session():
    """Get a database session for scripts and testing"""
    return SessionLocal()


def init_db():
    from .models import User,ClothingTypeReference,Swap
    Base.metadata.create_all(bind=engine)

    # Create indexes safely (skip if already exist)
    Index("ix_users_email", User.email, unique=True).create(bind=engine, checkfirst=True)
    Index("ix_users_username", User.username, unique=True).create(bind=engine, checkfirst=True)
    # Index("ix_clothing_items_clothing_type", Clothing_type.clothing_type).create(bind=engine, checkfirst=True)
    Index("ix_swaps_status", Swap.status).create(bind=engine, checkfirst=True)