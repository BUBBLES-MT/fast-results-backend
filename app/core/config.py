# app/core/config.py

import os
from typing import Optional, List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# 🔥 CONFIGURATION CLASS - PRO MAX VERSION 5.0
# ============================================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or system environment.
    """
    
    # ============================================================
    # 🔥 APP SETTINGS
    # ============================================================
    APP_NAME: str = Field(
        default="MASI FAST RESULTS API",
        description="Application name"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    APP_DESCRIPTION: str = Field(
        default="School Management System API",
        description="Application description"
    )
    APP_ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, testing, production"
    )
    DEBUG: bool = Field(
        default=True,
        description="Debug mode"
    )
    
    # ============================================================
    # 🔥 SERVER SETTINGS
    # ============================================================
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    PORT: int = Field(
        default=8000,
        description="Server port"
    )
    BACKEND_URL: str = Field(
        default="http://localhost:8000",
        description="Backend URL"
    )
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend URL"
    )
    
    # ============================================================
    # 🔥 CORS SETTINGS - FIXED!
    # ============================================================
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000,https://*.vercel.app,https://*.onrender.com,https://bubblesmanage.com,https://www.bubblesmanage.com,https://fast-results-frontend.vercel.app",
        description="Allowed CORS origins (comma separated)"
    )
    
    # ============================================================
    # 🔥 DATABASE SETTINGS
    # ============================================================
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/dbname",
        description="PostgreSQL database URL"
    )
    DATABASE_POOL_SIZE: int = Field(
        default=10,
        description="Database connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=20,
        description="Max overflow connections"
    )
    DATABASE_POOL_TIMEOUT: int = Field(
        default=30,
        description="Connection pool timeout"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries"
    )
    
    # ============================================================
    # 🔥 AUTHENTICATION SETTINGS
    # ============================================================
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        description="JWT secret key - MUST CHANGE IN PRODUCTION!"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration in days"
    )
    
    # ============================================================
    # 🔥 SECURITY SETTINGS
    # ============================================================
    BCRYPT_ROUNDS: int = Field(
        default=12,
        description="Bcrypt hashing rounds"
    )
    PASSWORD_MIN_LENGTH: int = Field(
        default=6,
        description="Minimum password length"
    )
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5,
        description="Max login attempts before lockout"
    )
    LOCKOUT_DURATION_MINUTES: int = Field(
        default=30,
        description="Lockout duration in minutes"
    )
    
    # ============================================================
    # 🔥🔥🔥 EMAIL SETTINGS - MAILTRAP (ZILE ZILE ZA POS!) 🔥🔥🔥
    # ============================================================
    MAIL_SERVER: str = Field(
        default="live.smtp.mailtrap.io",
        description="SMTP server host"
    )
    MAIL_PORT: int = Field(
        default=587,
        description="SMTP server port"
    )
    MAIL_USERNAME: str = Field(
        default="api",
        description="SMTP username"
    )
    MAIL_PASSWORD: str = Field(
        default="811496902a46029b831bac1d6afe5c74",
        description="SMTP password"
    )
    MAIL_USE_TLS: bool = Field(
        default=True,
        description="Use TLS for SMTP"
    )
    MAIL_USE_SSL: bool = Field(
        default=False,
        description="Use SSL for SMTP"
    )
    MAIL_DEFAULT_SENDER: str = Field(
        default="noreply@bubblesmanage.com",
        description="Default from email address"
    )
    
    MAILTRAP_API_TOKEN: str = Field(
        default="811496902a46029b831bac1d6afe5c74",
        description="Mailtrap API token"
    )
    MAILTRAP_FROM_EMAIL: str = Field(
        default="noreply@bubblesmanage.com",
        description="Mailtrap from email"
    )
    MAILTRAP_FROM_NAME: str = Field(
        default="MASI FAST RESULTS",
        description="Mailtrap from name"
    )
    
    # 🔥🔥🔥 NEW - MAILTRAP ENABLED 🔥🔥🔥
    MAILTRAP_ENABLED: bool = Field(
        default=True,
        description="Enable Mailtrap API for sending emails"
    )
    
    # ============================================================
    # 🔥🔥🔥 REDIS SETTINGS (ZILE ZILE ZA POS!) 🔥🔥🔥
    # ============================================================
    REDIS_URL: str = Field(
        default="rediss://default:gQAAAAAAAfG3AAIgcDE0OWNjZDE2NGY2YjM0YjM4ODVhZDJhMmFiNGZhOGI3Yg@correct-mule-127415.upstash.io:6379",
        description="Redis URL for caching and tokens"
    )
    REDIS_CACHE_TTL: int = Field(
        default=3600,
        description="Cache TTL in seconds (1 hour)"
    )
    REDIS_RESET_TOKEN_TTL: int = Field(
        default=3600,
        description="Reset token TTL in seconds (1 hour)"
    )
    
    # ============================================================
    # 🔥 OPENAI SETTINGS (Optional)
    # ============================================================
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model to use"
    )
    OPENAI_MAX_TOKENS: int = Field(
        default=1000,
        description="Max tokens for OpenAI responses"
    )
    OPENAI_TEMPERATURE: float = Field(
        default=0.7,
        description="OpenAI temperature"
    )
    
    # ============================================================
    # 🔥 FILE UPLOAD SETTINGS
    # ============================================================
    MAX_UPLOAD_SIZE: int = Field(
        default=5242880,
        description="Max upload size in bytes (5MB)"
    )
    ALLOWED_EXTENSIONS: str = Field(
        default=".jpg,.jpeg,.png,.gif,.pdf,.doc,.docx",
        description="Allowed file extensions (comma separated)"
    )
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Upload directory"
    )
    
    # ============================================================
    # 🔥 LOGGING SETTINGS
    # ============================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="Log file path"
    )
    
    # ============================================================
    # 🔥 PAYMENT SETTINGS (Optional - Kwa sasa hatuitumii)
    # ============================================================
    CLICKPESA_API_KEY: Optional[str] = Field(
        default=None,
        description="ClickPesa API Key"
    )
    CLICKPESA_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="ClickPesa Client ID"
    )
    CLICKPESA_INITIATE_URL: Optional[str] = Field(
        default=None,
        description="ClickPesa Initiate URL"
    )
    CLICKPESA_PAYMENT_STATUS_URL: Optional[str] = Field(
        default=None,
        description="ClickPesa Payment Status URL"
    )
    CLICKPESA_PREVIEW_URL: Optional[str] = Field(
        default=None,
        description="ClickPesa Preview URL"
    )
    
    # ============================================================
    # 🔥 SMS SETTINGS (Optional)
    # ============================================================
    AT_API_KEY: Optional[str] = Field(
        default=None,
        description="AfricasTalking API Key"
    )
    AT_USERNAME: Optional[str] = Field(
        default=None,
        description="AfricasTalking Username"
    )
    SMS_SANDBOX: bool = Field(
        default=False,
        description="SMS Sandbox Mode"
    )
    
    # ============================================================
    # 🔥 SUPABASE SETTINGS (Optional)
    # ============================================================
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase URL"
    )
    SUPABASE_KEY: Optional[str] = Field(
        default=None,
        description="Supabase API Key"
    )
    SUPABASE_BUCKET: str = Field(
        default="uploads",
        description="Supabase Storage Bucket"
    )
    
    # ============================================================
    # 🔥 VALIDATORS
    # ============================================================
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is not default in production"""
        env = os.getenv("APP_ENVIRONMENT", "development")
        if env == "production" and v == "your-super-secret-key-change-this-in-production":
            raise ValueError("SECRET_KEY must be changed in production!")
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is set"""
        if not v or v == "postgresql://user:password@localhost:5432/dbname":
            env = os.getenv("APP_ENVIRONMENT", "development")
            if env == "production":
                raise ValueError("DATABASE_URL must be set in production!")
        return v
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> str:
        """Parse allowed origins - always return string"""
        if isinstance(v, list):
            return ",".join(v)
        return v
    
    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate Redis URL"""
        if v and not v.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
        return v
    
    # ============================================================
    # 🔥 HELPER PROPERTIES
    # ============================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.APP_ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.APP_ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.APP_ENVIRONMENT == "testing"
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as list"""
        if self.is_development:
            return ["http://localhost:3000", "http://localhost:8000"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get allowed extensions as list"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()]
    
    @property
    def is_redis_enabled(self) -> bool:
        """Check if Redis is enabled"""
        return self.REDIS_URL is not None and self.REDIS_URL != ""
    
    @property
    def is_email_enabled(self) -> bool:
        """Check if email is enabled"""
        return (
            self.MAIL_SERVER is not None and
            self.MAIL_USERNAME is not None and
            self.MAIL_PASSWORD is not None
        )
    
    @property
    def is_mailtrap_enabled(self) -> bool:
        """Check if Mailtrap API is enabled"""
        return self.MAILTRAP_ENABLED and self.MAILTRAP_API_TOKEN is not None and self.MAILTRAP_API_TOKEN != ""
    
    # ============================================================
    # 🔥 PYDANTIC V2 CONFIG
    # ============================================================
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# ============================================================
# 🔥 SINGLETON INSTANCE (Cached)
# ============================================================

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


# ============================================================
# 🔥 TYPE ALIASES FOR CONVENIENCE
# ============================================================

Config = Settings
config = settings


# ============================================================
# 🔥 USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 MASI FAST RESULTS - Configuration")
    print("=" * 60)
    print(f"APP_NAME: {settings.APP_NAME}")
    print(f"APP_ENVIRONMENT: {settings.APP_ENVIRONMENT}")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DATABASE_URL: {settings.DATABASE_URL[:30]}...")
    print(f"FRONTEND_URL: {settings.FRONTEND_URL}")
    print(f"CORS Origins: {settings.cors_origins}")
    print("-" * 60)
    print("🔐 EMAIL Settings:")
    print(f"  MAIL_SERVER: {settings.MAIL_SERVER}")
    print(f"  MAIL_PORT: {settings.MAIL_PORT}")
    print(f"  MAIL_USERNAME: {settings.MAIL_USERNAME}")
    print(f"  MAIL_DEFAULT_SENDER: {settings.MAIL_DEFAULT_SENDER}")
    print(f"  MAILTRAP_FROM_NAME: {settings.MAILTRAP_FROM_NAME}")
    print(f"  MAILTRAP_ENABLED: {settings.MAILTRAP_ENABLED}")
    print(f"  Email Enabled: {settings.is_email_enabled}")
    print(f"  Mailtrap Enabled: {settings.is_mailtrap_enabled}")
    print("-" * 60)
    print("📦 REDIS Settings:")
    print(f"  REDIS_URL: {settings.REDIS_URL[:40]}...")
    print(f"  REDIS_CACHE_TTL: {settings.REDIS_CACHE_TTL}s")
    print(f"  REDIS_RESET_TOKEN_TTL: {settings.REDIS_RESET_TOKEN_TTL}s")
    print(f"  Redis Enabled: {settings.is_redis_enabled}")
    print("=" * 60)