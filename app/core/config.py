# app/core/config.py

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, EmailStr, field_validator
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# 🔥 CONFIGURATION CLASS - PRO MAX VERSION (FIXED)
# ============================================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or system environment.
    """
    
    # ============================================================
    # 🔥 APP SETTINGS
    # ============================================================
    APP_NAME: str = "MASI FAST RESULTS API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "School Management System API"
    APP_ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, testing, production"
    )
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    # ============================================================
    # 🔥 SERVER SETTINGS
    # ============================================================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    BACKEND_URL: str = Field(
        default="http://localhost:8000",
        description="Backend URL for CORS"
    )
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for CORS"
    )
    
    # ============================================================
    # 🔥 CORS SETTINGS
    # ============================================================
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "https://*.vercel.app",
            "https://*.onrender.com",
        ],
        description="Allowed CORS origins"
    )
    
    # ============================================================
    # 🔥 DATABASE SETTINGS
    # ============================================================
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/dbname",
        description="PostgreSQL database URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, description="Connection pool timeout")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")
    
    # ============================================================
    # 🔥 AUTHENTICATION SETTINGS
    # ============================================================
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        description="JWT secret key - MUST CHANGE IN PRODUCTION!"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,  # 24 hours
        description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration in days"
    )
    
    # ============================================================
    # 🔥 SECURITY SETTINGS
    # ============================================================
    BCRYPT_ROUNDS: int = Field(default=12, description="Bcrypt hashing rounds")
    PASSWORD_MIN_LENGTH: int = Field(default=6, description="Minimum password length")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, description="Max login attempts before lockout")
    LOCKOUT_DURATION_MINUTES: int = Field(default=30, description="Lockout duration in minutes")
    
    # ============================================================
    # 🔥 EMAIL SETTINGS (Optional)
    # ============================================================
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server host")
    SMTP_PORT: Optional[int] = Field(default=587, description="SMTP server port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_FROM_EMAIL: Optional[str] = Field(default=None, description="From email address")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    
    # ============================================================
    # 🔥 OPENAI SETTINGS (Optional)
    # ============================================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    OPENAI_MAX_TOKENS: int = Field(default=1000, description="Max tokens for OpenAI responses")
    OPENAI_TEMPERATURE: float = Field(default=0.7, description="OpenAI temperature")
    
    # ============================================================
    # 🔥 REDIS SETTINGS (Optional - for caching)
    # ============================================================
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for caching")
    REDIS_CACHE_TTL: int = Field(default=300, description="Cache TTL in seconds")
    
    # ============================================================
    # 🔥 FILE UPLOAD SETTINGS
    # ============================================================
    MAX_UPLOAD_SIZE: int = Field(default=5 * 1024 * 1024, description="Max upload size in bytes (5MB)")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"],
        description="Allowed file extensions"
    )
    UPLOAD_DIR: str = Field(default="uploads", description="Upload directory")
    
    # ============================================================
    # 🔥 LOGGING SETTINGS
    # ============================================================
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    
    # ============================================================
    # 🔥 VALIDATORS - FIXED! (Using field_validator for Pydantic v2)
    # ============================================================
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Ensure secret key is not default in production"""
        # Get APP_ENVIRONMENT from values
        # Since we can't access other fields directly, we check context
        env = os.getenv("APP_ENVIRONMENT", "development")
        if env == "production" and v == "your-super-secret-key-change-this-in-production":
            raise ValueError("SECRET_KEY must be changed in production!")
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is set"""
        if not v or v == "postgresql://user:password@localhost:5432/dbname":
            raise ValueError("DATABASE_URL must be set!")
        return v
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
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
        """Get CORS origins with environment-specific overrides"""
        if self.is_development:
            return ["http://localhost:3000", "http://localhost:8000"]
        return self.ALLOWED_ORIGINS
    
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
    """
    Get cached settings instance.
    Use this function to access settings throughout the application.
    """
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
    print("=" * 60)