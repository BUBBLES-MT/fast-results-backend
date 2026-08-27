from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SuperAdmin(Base):
    __tablename__ = "superadmins"

    # ==============================
    # 🔹 Basic Identity Fields
    # ==============================
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # ==============================
    # 🔹 Status Flags
    # ==============================
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=True)
    is_system_admin = Column(Boolean, default=False)

    # ==============================
    # 🔹 Metadata
    # ==============================
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ==============================
    # 🔹 Password & Authentication
    # ==============================
    def set_password(self, password: str):
        """Hash and set password securely."""
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self.password_hash = pwd_context.hash(password.strip())

    def check_password(self, password: str) -> bool:
        """Verify password correctness."""
        return pwd_context.verify(password.strip(), self.password_hash)

    # ==============================
    # 🔹 Convenience Methods
    # ==============================
    def can_login(self) -> bool:
        """Control login eligibility."""
        return self.is_active

    @property
    def role(self):
        """For unified interface with Teacher, etc."""
        return "SuperAdmin"

    def get_full_name(self):
        """Return formatted display name."""
        return self.name.title()

    def __repr__(self):
        return f"<SuperAdmin {self.username}>"
    