from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🔥 TIMEZONE KWA TANZANIA (UTC+3)
# ============================================================
TZ = pytz.timezone("Africa/Dar_es_Salaam")

def get_tz_now():
    """Get current time in Tanzania timezone (UTC+3)"""
    return datetime.now(TZ)


# ============================================================
# 🔥 ENUMS ZILIZOBORESHA
# ============================================================

class SchoolType(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ADVANCED = "advanced"

class SchoolStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

class SubscriptionPlan(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMESTER = "semester"
    ANNUAL = "annual"

class SchoolLevel(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ADVANCED = "advanced"


# ============================================================
# 🔥 MODEL YA SCHOOL ILIYOBORESHA KAMILI
# ============================================================

class School(Base):
    __tablename__ = "schools"

    # ============================================================
    # 🔹 Basic Information
    # ============================================================
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(120), unique=True, nullable=True)
    admin_email = Column(String(200), nullable=True)
    sender_id = Column(String(20), nullable=True, unique=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(200), nullable=True)
    region = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)

    # ============================================================
    # 🔹 School Classification
    # ============================================================
    school_type = Column(Enum(SchoolType), nullable=False, default=SchoolType.SECONDARY)
    school_level = Column(Enum(SchoolLevel), nullable=False, default=SchoolLevel.SECONDARY)
    registration_number = Column(String(50), nullable=True, unique=True)

    # ============================================================
    # 🔹 Status Flags
    # ============================================================
    is_active = Column(Boolean, default=True)
    status = Column(Enum(SchoolStatus), nullable=False, default=SchoolStatus.ACTIVE)
    is_locked_by_superadmin = Column(Boolean, default=False)
    
    is_trial = Column(Boolean, default=False)
    trial_expires_at = Column(DateTime(timezone=True), nullable=True)

    # ============================================================
    # 🔹 Subscription Fields
    # ============================================================
    subscription_plan = Column(Enum(SubscriptionPlan), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_overridden = Column(Boolean, default=False)

    # ============================================================
    # 🔹 Metadata
    # ============================================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ============================================================
    # 🔥 RELATIONSHIPS
    # ============================================================
    
    students = relationship("Student", back_populates="school", cascade="all, delete-orphan", passive_deletes=True)
    classes = relationship("SchoolClass", back_populates="school", cascade="all, delete-orphan", passive_deletes=True)
    streams = relationship("Stream", back_populates="school", cascade="all, delete-orphan", passive_deletes=True)
    subjects = relationship("Subject", back_populates="school", cascade="all, delete-orphan", passive_deletes=True)
    parents = relationship("Parent", back_populates="school", cascade="all, delete-orphan", passive_deletes=True)
    payment_transactions = relationship("PaymentTransaction", back_populates="school", cascade="all, delete-orphan", passive_deletes=True)

    # ============================================================
    # 🔹 Methods
    # ============================================================

    def __repr__(self) -> str:
        return f"<School {self.name} ({self.school_level.value})>"

    @staticmethod
    def _get_tz():
        return TZ

    def get_level_display_name(self) -> str:
        level_names = {
            SchoolLevel.PRIMARY: "Primary School",
            SchoolLevel.SECONDARY: "Secondary School",
            SchoolLevel.ADVANCED: "Advanced Level"
        }
        return level_names.get(self.school_level, "School")

    def get_dashboard_path(self) -> str:
        if self.school_level == SchoolLevel.PRIMARY:
            return "/primary/dashboard"
        elif self.school_level == SchoolLevel.ADVANCED:
            return "/advanced/dashboard"
        return "/secondary/dashboard"

    # ============================================================
    # 🔥🔥🔥 SUBSCRIPTION HELPERS - ILIYOBORESHA KABISA! 🔥🔥🔥
    # ============================================================

    def is_subscription_active(self) -> bool:
        """
        🔥 MUHIMU SANA: Check if school subscription is active.
        
        Returns:
            bool: True if subscription is active, False otherwise
        """
        # 🔥 IKIWA IMELOCKED NA SUPERADMIN
        if self.is_locked_by_superadmin:
            logger.debug(f"🔒 School {self.id} is locked by superadmin")
            return False

        # 🔥 IKIWA HAKUNA TAREHE YA MALIPO
        if not self.subscription_expires_at:
            logger.debug(f"❌ School {self.id} has no subscription expiry date")
            return False

        # ✅ HESABU TIMEZONE
        now = get_tz_now()
        expires = self.subscription_expires_at

        # ✅ HAKIKISHA TAREHE IKO SAHIHI
        if expires.tzinfo is None:
            expires = TZ.localize(expires)

        # 🔥 ANGALIA KAMA TAREHE IMEPITA
        if expires < now:
            days_overdue = (now - expires).days
            logger.warning(f"🔴 School {self.id} ({self.name}) subscription EXPIRED on {expires.strftime('%Y-%m-%d')}. {days_overdue} days overdue")
            return False

        # ✅ SUBSCRIPTION IKO ACTIVE
        days_left = (expires - now).days
        logger.debug(f"✅ School {self.id} subscription active, {days_left} days left")
        return True

    def extend_subscription(self, plan: str, days: int = None) -> None:
        """Extend subscription based on plan name."""
        PLANS = {
            "monthly": 30,
            "quarterly": 90,
            "semester": 180,
            "annual": 365
        }

        if plan not in PLANS:
            raise ValueError(f"Invalid subscription plan: {plan}. Must be one of: {', '.join(PLANS.keys())}")

        now = get_tz_now()
        days_to_add = days or PLANS[plan]

        expires = self.subscription_expires_at
        if expires and expires.tzinfo is None:
            expires = TZ.localize(expires)

        if expires and expires > now:
            self.subscription_expires_at = expires + timedelta(days=days_to_add)
        else:
            self.subscription_expires_at = now + timedelta(days=days_to_add)

        self.subscription_plan = SubscriptionPlan(plan)
        self.is_overridden = False
        
        self.is_active = True
        if self.status == SchoolStatus.EXPIRED or self.status == SchoolStatus.INACTIVE:
            self.status = SchoolStatus.ACTIVE
        
        logger.info(f"✅ School {self.id} ({self.name}) subscription extended by {days_to_add} days. New expiry: {self.subscription_expires_at}")

    def subscription_status(self):
        """Returns (status_str, days_left)"""
        if not self.subscription_expires_at:
            return "expired", 0

        now = get_tz_now()
        expires = self.subscription_expires_at

        if expires.tzinfo is None:
            expires = TZ.localize(expires)

        if expires < now:
            days_overdue = (now - expires).days
            return "expired", days_overdue

        days_left = (expires - now).days
        
        if days_left <= 7:
            return "near_expiry", days_left

        return "active", days_left

    def get_days_left(self) -> int:
        if not self.subscription_expires_at:
            return 0
        
        now = get_tz_now()
        expires = self.subscription_expires_at
        
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        
        if expires < now:
            return 0
        
        return (expires - now).days

    def get_days_overdue(self) -> int:
        if not self.subscription_expires_at:
            return 0
        
        now = get_tz_now()
        expires = self.subscription_expires_at
        
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        
        if expires > now:
            return 0
        
        return (now - expires).days

    # ============================================================
    # 🔥🔥🔥 ACCESS CONTROL HELPERS - ILIYOBORESHA KABISA! 🔥🔥🔥
    # ============================================================

    def can_login(self) -> bool:
        """
        Check if school allows login.
        
        Returns:
            bool: True if users can login, False otherwise
        """
        # 🔥 IKIWA IMELOCKED NA SUPERADMIN
        if self.is_locked_by_superadmin:
            logger.warning(f"🔒 School {self.id} ({self.name}) is locked by superadmin")
            return False
        
        # 🔥 IKIWA INA TRIAL
        if self.is_trial:
            if self.trial_expires_at:
                now = get_tz_now()
                if self.trial_expires_at < now:
                    logger.warning(f"⏰ School {self.id} ({self.name}) trial expired")
                    return False
            return True
        
        # ✅ ANGALIA SUBSCRIPTION - HAPA NDIO MUHIMU!
        if not self.is_subscription_active():
            logger.warning(f"🔴 School {self.id} ({self.name}) subscription is NOT active")
            return False
        
        return True

    def lock_by_superadmin(self) -> None:
        self.is_locked_by_superadmin = True
        self.status = SchoolStatus.SUSPENDED
        self.is_active = False
        logger.warning(f"🔒 School {self.id} ({self.name}) locked by superadmin")

    def unlock_by_superadmin(self) -> None:
        self.is_locked_by_superadmin = False
        
        if self.is_subscription_active():
            self.status = SchoolStatus.ACTIVE
            self.is_active = True
        else:
            self.status = SchoolStatus.EXPIRED
            self.is_active = False
        
        logger.info(f"🔓 School {self.id} ({self.name}) unlocked by superadmin. Status: {self.status.value}")

    # ============================================================
    # 🔥 TRIAL PERIOD MANAGEMENT
    # ============================================================

    def start_trial(self, days: int = 30) -> None:
        now = get_tz_now()
        self.is_trial = True
        self.trial_expires_at = now + timedelta(days=days)
        self.status = SchoolStatus.ACTIVE
        self.is_active = True
        self.is_locked_by_superadmin = False
        logger.info(f"🎉 School {self.id} ({self.name}) trial started for {days} days. Expires: {self.trial_expires_at}")

    def end_trial(self) -> None:
        self.is_trial = False
        self.trial_expires_at = None
        
        if self.is_subscription_active():
            self.status = SchoolStatus.ACTIVE
            self.is_active = True
        else:
            self.status = SchoolStatus.EXPIRED
            self.is_active = False
        
        logger.info(f"⏹️ School {self.id} ({self.name}) trial ended. Status: {self.status.value}")

    # ============================================================
    # 🔥 SCHOOL TYPE HELPERS
    # ============================================================

    @property
    def is_primary(self) -> bool:
        return self.school_level == SchoolLevel.PRIMARY

    @property
    def is_secondary(self) -> bool:
        return self.school_level == SchoolLevel.SECONDARY

    @property
    def is_advanced(self) -> bool:
        return self.school_level == SchoolLevel.ADVANCED

    # ============================================================
    # 🔥 STATUS DISPLAY
    # ============================================================

    def get_status_display(self) -> str:
        if self.is_locked_by_superadmin:
            return "Locked"
        
        if not self.is_subscription_active():
            return "Expired"
        
        if self.is_trial:
            if self.trial_expires_at:
                now = get_tz_now()
                if self.trial_expires_at < now:
                    return "Trial Expired"
            return "Active (Trial)"
        
        return "Active"

    def get_status_color(self) -> str:
        status = self.get_status_display()
        if status == "Active" or status == "Active (Trial)":
            return "green"
        elif status == "Expired" or status == "Trial Expired":
            return "red"
        elif status == "Locked":
            return "yellow"
        else:
            return "gray"

    # ============================================================
    # 🔥 UPDATE STATUS AUTOMATICALLY
    # ============================================================

    def update_status(self) -> None:
        """Automatically update status based on current state."""
        if self.is_locked_by_superadmin:
            self.status = SchoolStatus.SUSPENDED
            self.is_active = False
            logger.debug(f"School {self.id} status set to SUSPENDED (locked)")
            return
        
        if self.is_trial:
            if self.trial_expires_at:
                now = get_tz_now()
                if self.trial_expires_at < now:
                    self.status = SchoolStatus.EXPIRED
                    self.is_active = False
                    logger.debug(f"School {self.id} status set to EXPIRED (trial expired)")
                    return
            self.status = SchoolStatus.ACTIVE
            self.is_active = True
            logger.debug(f"School {self.id} status set to ACTIVE (trial)")
            return
        
        if self.is_subscription_active():
            self.status = SchoolStatus.ACTIVE
            self.is_active = True
            logger.debug(f"School {self.id} status set to ACTIVE (subscription active)")
        else:
            self.status = SchoolStatus.EXPIRED
            self.is_active = False
            logger.debug(f"School {self.id} status set to EXPIRED (subscription expired)")