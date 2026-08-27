from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL - Badilisha na password yako ya PostgreSQL
# Format: postgresql://username:password@localhost:5432/database_name
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:yourpassword@localhost:5432/school_management")

# SQL logging: set SQL_ECHO=true in .env only when debugging queries (default off = faster, quieter logs)
_sql_echo = os.getenv("SQL_ECHO", "").strip().lower() in ("1", "true", "yes")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=_sql_echo,
)

# Create session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    """
    Dependency function that provides database session.
    Use this in your API endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()