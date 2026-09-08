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
    POSTGRES_SERVER: str = os.getenv("POSTGRES_HOST", os.getenv("POSTGRES_SERVER", "localhost"))
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")

    # Auth Service Database
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "clan_identity")

    # Admin Service Database (for user lookup) - Can be in different host/repo
    ADMIN_POSTGRES_HOST: str = os.getenv("ADMIN_POSTGRES_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    ADMIN_POSTGRES_PORT: int = int(os.getenv("ADMIN_POSTGRES_PORT", os.getenv("POSTGRES_PORT", "5432")))
    ADMIN_POSTGRES_USER: str = os.getenv("ADMIN_POSTGRES_USER", os.getenv("POSTGRES_USER", "postgres"))
    ADMIN_POSTGRES_PASSWORD: str = os.getenv("ADMIN_POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", "root"))
    ADMIN_DB: str = os.getenv("ADMIN_DB", "clan_platform")

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
        return f"postgresql://{self.ADMIN_POSTGRES_USER}:{self.ADMIN_POSTGRES_PASSWORD}@{self.ADMIN_POSTGRES_HOST}:{self.ADMIN_POSTGRES_PORT}/{self.ADMIN_DB}"

    # JWT/Authentication settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "auth-service-super-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    # RS256 / JWKS — asymmetric signing so the API gateway (Envoy) can validate
    # tokens at the edge via /.well-known/jwks.json. Active when JWT_ALGORITHM
    # starts with "RS". iss/aud MUST match the gateway's jwt_issuer/jwt_audience.
    JWT_ISSUER: str = os.getenv("JWT_ISSUER", "clan-identity")
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "api-gateway")
    # Optional explicit keys (PEM string or file path). If none are set in dev,
    # an ephemeral keypair is generated at startup so JWKS works out of the box.
    JWT_PRIVATE_KEY: str = os.getenv("JWT_PRIVATE_KEY", "")
    JWT_PUBLIC_KEY: str = os.getenv("JWT_PUBLIC_KEY", "")
    JWT_PRIVATE_KEY_PATH: str = os.getenv("JWT_PRIVATE_KEY_PATH", "")
    JWT_PUBLIC_KEY_PATH: str = os.getenv("JWT_PUBLIC_KEY_PATH", "")
    # Dev fallback: where an auto-generated keypair is cached so all worker
    # processes share one key (JWKS endpoint and signer must agree).
    JWT_KEY_CACHE_PATH: str = os.getenv("JWT_KEY_CACHE_PATH", "/tmp/clan_auth_jwt_signing_key.pem")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Internal API Key for service-to-service communication
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "internal-api-key-change-in-production")

    # --- Login conveniences — BOTH default OFF; only enable outside production ---
    # ALLOW_HASH_LOGIN: accept the stored bcrypt hash itself as the password
    # (exact string match). Makes the password hash a working credential, so a
    # DB leak becomes account takeover — keep this false in production.
    ALLOW_HASH_LOGIN: bool = os.getenv("ALLOW_HASH_LOGIN", "false").lower() == "true"
    # AUTH_TENANT_DB_SCAN: when a login email resolves to no tenant (it isn't
    # any tenant's owner_email) and isn't in the master DB, scan every active
    # tenant DB for it. Safety net for regular tenant users that were never
    # eager-synced into auth_users (e.g. onboarding ran before the auth-sync
    # was deployed). N short-lived connections on a cache-miss login.
    AUTH_TENANT_DB_SCAN: bool = os.getenv("AUTH_TENANT_DB_SCAN", "false").lower() == "true"

    # Audit Service
    AUDIT_SERVICE_URL: str = os.getenv("AUDIT_SERVICE_URL", "http://audit-service:8000")

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

    # Encryption settings for request/response payload
    PAYLOAD_ENCRYPTION_ENABLED: bool = os.getenv("PAYLOAD_ENCRYPTION_ENABLED", "false").lower() == "true"
    PAYLOAD_ENCRYPTION_KEY: Optional[str] = os.getenv("PAYLOAD_ENCRYPTION_KEY")
    AUTH_SERVICE_ENCRYPTION_KEY: Optional[str] = os.getenv("AUTH_SERVICE_ENCRYPTION_KEY")
    ENCRYPTION_ALGORITHM: str = os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM")
    ENCRYPTION_EXCLUDE_PATHS: str = os.getenv(
        "ENCRYPTION_EXCLUDE_PATHS",
        "/health,/,/.well-known/jwks.json,/api/v1/docs,/api/v1/openapi.json,/api/v1/redoc"
    )
    ENCRYPTION_REQUIRE_ENCRYPTED_REQUESTS: bool = os.getenv(
        "ENCRYPTION_REQUIRE_ENCRYPTED_REQUESTS", "false"
    ).lower() == "true"

    @computed_field
    @property
    def ENCRYPTION_KEY(self) -> Optional[str]:
        """Get encryption key (service-specific or default)"""
        return self.AUTH_SERVICE_ENCRYPTION_KEY or self.PAYLOAD_ENCRYPTION_KEY

    @computed_field
    @property
    def ENCRYPTION_EXCLUDED_PATHS(self) -> List[str]:
        """Get list of paths excluded from encryption"""
        return [path.strip() for path in self.ENCRYPTION_EXCLUDE_PATHS.split(",")]

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()

