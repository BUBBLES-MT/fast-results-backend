from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
from passlib.context import CryptContext
import pytz

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tanzania timezone
TZ = pytz.timezone("Africa/Dar_es_Salaam")

def get_tz_now():
    """Get current time in Tanzania timezone (UTC+3)"""
    return datetime.now(TZ)


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

    # ============================================================
    # 🔥🔥🔥 RESET PASSWORD TOKEN FIELDS (NEW!) 🔥🔥🔥
    # ============================================================
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

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