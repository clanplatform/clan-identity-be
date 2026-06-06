"""
Auth Service Configuration
Separate database configuration for auth_service PostgreSQL database
Also connects to admin_service database for user authentication
"""
import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Auth Service Settings"""

    # Service Info
    PROJECT_NAME: str = "Auth Service"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # CORS settings
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:9080",
        "http://localhost:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            # Handle comma-separated string
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
            # Handle JSON string
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        elif isinstance(v, list):
            return v
        return [str(v)]

    # Database settings - PostgreSQL common settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")

    # Auth Service Database
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "auth_service")

    # Admin Service Database (for user lookup)
    ADMIN_DB: str = os.getenv("ADMIN_DB", "admin_service")

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Auth service database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Alias for SQLALCHEMY_DATABASE_URI for compatibility"""
        return self.SQLALCHEMY_DATABASE_URI

    @computed_field
    @property
    def ADMIN_DATABASE_URL(self) -> str:
        """Admin service database URL for user authentication"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.ADMIN_DB}"

    # JWT/Authentication settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "auth-service-super-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Internal API Key for service-to-service communication
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "internal-api-key-change-in-production")

    # Aliases for backward compatibility
    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET_KEY

    @property
    def ALGORITHM(self) -> str:
        return self.JWT_ALGORITHM
    
    # Redis settings for session management
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "1"))  # Use DB 1 for auth service
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    
    @computed_field
    @property
    def REDIS_URL(self) -> str:
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Email/SMTP settings for OTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@zcare.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "ZCare Auth")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"

    # OTP Development Mode - Print OTP to console when SMTP not configured
    OTP_DEV_MODE: bool = os.getenv("OTP_DEV_MODE", "true").lower() == "true"

    # OTP settings
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
    OTP_LENGTH: int = int(os.getenv("OTP_LENGTH", "6"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))

    # Rate Limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

    # Kafka settings
    # Default to Docker network (kafka:29092), fallback to localhost for local dev
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    KAFKA_CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "auth-service")
    KAFKA_ENABLED: bool = os.getenv("KAFKA_ENABLED", "true").lower() == "true"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()

