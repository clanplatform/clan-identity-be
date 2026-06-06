"""Shared configuration utilities."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class BaseServiceConfig(BaseSettings):
    """Base configuration for all services."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Service
    service_name: str
    environment: str = "development"
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Security
    secret_key: str
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # CORS
    allowed_origins: str = "http://localhost:3000"
    
    @property
    def is_development(self) -> bool:
        """Check if environment is development."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.environment.lower() == "production"
    
    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
