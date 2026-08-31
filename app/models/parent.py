# app/models/parent.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from passlib.context import CryptContext
import pytz
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tanzania timezone
TZ = pytz.timezone("Africa/Dar_es_Salaam")

def get_tz_now():
    """Get current time in Tanzania timezone (UTC+3)"""
    return datetime.now(TZ)


class Parent(Base):
    __tablename__ = "parents"

    # ==============================
    # 🔹 Basic Fields
    # ==============================
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # ============================================================
    # 🔥🔥🔥 RESET PASSWORD TOKEN FIELDS (NEW!) 🔥🔥🔥
    # ============================================================
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # ==============================
    # 🔹 Timestamps
    # ==============================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ==============================
    # 🔹 Relationships
    # ==============================
    school = relationship("School", back_populates="parents")
    children = relationship("ParentChild", back_populates="parent", cascade="all, delete-orphan")

    # ==============================
    # 🔹 Password & Authentication
    # ==============================
    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)

    # ============================================================
    # 🔹 RESET PASSWORD HELPER METHODS (NEW!)
    # ============================================================
    def set_reset_token(self, token: str, expires_in_hours: int = 1) -> None:
        """Set reset token with expiration"""
        self.reset_token = token
        self.reset_token_expires = get_tz_now() + timedelta(hours=expires_in_hours)

    def is_reset_token_valid(self, token: str) -> bool:
        """Check if reset token is valid"""
        return (
            self.reset_token == token and
            self.reset_token_expires is not None and
            self.reset_token_expires > get_tz_now()
        )

    def clear_reset_token(self) -> None:
        """Clear reset token after use"""
        self.reset_token = None
        self.reset_token_expires = None

    # ==============================
    # 🔹 Representation
    # ==============================
    def __repr__(self):
        return f"<Parent {self.name} ({self.username})>"