from pydantic_settings import BaseSettings
from typing import List


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

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()