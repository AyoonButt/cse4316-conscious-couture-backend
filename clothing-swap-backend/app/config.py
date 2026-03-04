from pydantic_settings import BaseSettings
from typing import List
import os, stripe


class Settings(BaseSettings):
    APP_NAME: str = "Clothing Swap API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./clothing_swap.db"
    SECRET_KEY: str = "your-secret-key-change-this-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    WIKIRATE_API_URL: str = "https://wikirate.org"
    WIKIRATE_CACHE_TTL_DAYS: int = 30
    LOG_LEVEL: str = "INFO"
    DEFAULT_REPLACEMENT_FACTOR: float = 0.70
    REUSE_OVERHEAD_CO2_KG: float = 0.08

    # Stripe configuration - Pydantic will load these from .env file
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # ShipStation configuration - Pydantic will load these from .env file
    SHIPSTATION_API_KEY: str
    SHIPSTATION_API_SECRET: str

    # ShipEngine configuration
    SHIPENGINE_API_KEY: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set stripe API key after settings are loaded
        stripe.api_key = self.STRIPE_SECRET_KEY
        if not stripe.api_key:
            print("Warning: STRIPE_SECRET_KEY is not set")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()