from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

# ============================================================
# 🔥 ENUMS ZA MALIPO
# ============================================================

class TransactionStatus(str, enum.Enum):
    """Hali ya malipo"""
    PENDING = "pending"         # Inasubiri
    PROCESSING = "processing"   # Inachakatwa
    SUCCESS = "success"         # Imefanikiwa
    FAILED = "failed"           # Imeshindwa
    CANCELLED = "cancelled"     # Imefutwa
    REFUNDED = "refunded"       # Imerejeshwa

class PaymentProvider(str, enum.Enum):
    """Mtoa huduma wa malipo"""
    CLICKPESA = "ClickPesa"
    MPESA = "M-Pesa"
    TIGOPESA = "TigoPesa"
    AIRTELMONEY = "AirtelMoney"
    HALOPESA = "HaloPesa"

class SubscriptionPlan(str, enum.Enum):
    """Mipango ya usajili"""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    TWO_MONTHS = "2months"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

class PaymentMethod(str, enum.Enum):
    """Njia ya malipo"""
    MOBILE = "mobile"
    BANK = "bank"
    CARD = "card"
    CASH = "cash"


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # ============================================================
    # 🔥 FOREIGN KEYS
    # ============================================================
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)

    # ============================================================
    # 🔥 CUSTOMER INFO
    # ============================================================
    phone_number = Column(String(20), nullable=False)
    customer_name = Column(String(200), nullable=True)
    customer_email = Column(String(200), nullable=True)

    # ============================================================
    # 🔥 PAYMENT DETAILS
    # ============================================================
    amount = Column(Float, nullable=False)
    plan = Column(String(50), nullable=False)  # weekly, biweekly, monthly, 2months, quarterly, annual
    payment_method = Column(String(50), nullable=True, default="mobile")  # mobile, bank, card, cash

    # ============================================================
    # 🔥 TRANSACTION STATUS
    # ============================================================
    status = Column(String(50), default="pending")  # pending, processing, success, failed, cancelled, refunded
    provider = Column(String(50), default="ClickPesa")  # ClickPesa, M-Pesa, TigoPesa, AirtelMoney, HaloPesa

    # ============================================================
    # 🔥 TRANSACTION REFERENCES
    # ============================================================
    transaction_id = Column(String(100), unique=True, nullable=True, index=True)
    reference_number = Column(String(100), unique=True, nullable=True, index=True)
    provider_reference = Column(String(100), nullable=True)  # Reference kutoka provider

    # ============================================================
    # 🔥 RESPONSE DATA
    # ============================================================
    request_data = Column(Text, nullable=True)  # Data iliyotumwa kwa provider
    response_data = Column(Text, nullable=True)  # Data iliyopokelewa kutoka provider
    error_message = Column(Text, nullable=True)  # Kama imeshindwa

    # ============================================================
    # 🔥 SUBSCRIPTION INFO
    # ============================================================
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)

    # ============================================================
    # 🔥 METADATA
    # ============================================================
    created_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Tarehe ya kukamilika

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 School (Shule)
    school = relationship("School", back_populates="payment_transactions")
    
    # 🔥 Created By (Aliyeanzisha malipo)
    created_by_teacher = relationship("Teacher", foreign_keys=[created_by])

    # ============================================================
    # 🔥 METHODS
    # ============================================================

    def __repr__(self):
        return f"<PaymentTransaction {self.id} - {self.phone_number} - {self.amount} - {self.status}>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "school_id": self.school_id,
            "phone_number": self.phone_number,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "amount": self.amount,
            "plan": self.plan,
            "payment_method": self.payment_method,
            "status": self.status,
            "provider": self.provider,
            "transaction_id": self.transaction_id,
            "reference_number": self.reference_number,
            "provider_reference": self.provider_reference,
            "error_message": self.error_message,
            "subscription_start": self.subscription_start.isoformat() if self.subscription_start else None,
            "subscription_end": self.subscription_end.isoformat() if self.subscription_end else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    def is_pending(self) -> bool:
        """Check if transaction is pending"""
        return self.status == "pending"

    def is_processing(self) -> bool:
        """Check if transaction is being processed"""
        return self.status == "processing"

    def is_successful(self) -> bool:
        """Check if transaction was successful"""
        return self.status == "success"

    def is_failed(self) -> bool:
        """Check if transaction failed"""
        return self.status == "failed"

    def is_cancelled(self) -> bool:
        """Check if transaction was cancelled"""
        return self.status == "cancelled"

    def is_refunded(self) -> bool:
        """Check if transaction was refunded"""
        return self.status == "refunded"

    def can_retry(self) -> bool:
        """Check if transaction can be retried"""
        return self.status in ["failed", "cancelled"]

    def mark_success(self, transaction_id: str = None, provider_reference: str = None) -> None:
        """Mark transaction as successful"""
        self.status = "success"
        self.completed_at = func.now()
        if transaction_id:
            self.transaction_id = transaction_id
        if provider_reference:
            self.provider_reference = provider_reference

    def mark_failed(self, error_message: str = None) -> None:
        """Mark transaction as failed"""
        self.status = "failed"
        self.error_message = error_message

    def mark_processing(self) -> None:
        """Mark transaction as processing"""
        self.status = "processing"

    def mark_cancelled(self) -> None:
        """Mark transaction as cancelled"""
        self.status = "cancelled"

    def mark_refunded(self) -> None:
        """Mark transaction as refunded"""
        self.status = "refunded"

    def get_plan_display_name(self) -> str:
        """Get display name for subscription plan"""
        plan_names = {
            "weekly": "Wiki 1",
            "biweekly": "Wiki 2",
            "monthly": "Mwezi 1",
            "2months": "Miezi 2",
            "quarterly": "Miezi 3",
            "annual": "Mwaka 1"
        }
        return plan_names.get(self.plan, self.plan)

    def get_status_display_name(self) -> str:
        """Get display name for status"""
        status_names = {
            "pending": "Inasubiri",
            "processing": "Inachakatwa",
            "success": "Imefanikiwa",
            "failed": "Imeshindwa",
            "cancelled": "Imefutwa",
            "refunded": "Imerejeshwa"
        }
        return status_names.get(self.status, self.status)