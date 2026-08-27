# app/models/teacher.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from passlib.context import CryptContext
import enum

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
# 🔥 TEACHER STATUS ENUM
# ============================================================
class TeacherStatus(str, enum.Enum):
    """Status ya mwalimu katika mfumo"""
    PENDING = "pending"       # Inasubiri approval
    ACTIVE = "active"         # Ameidhinishwa
    REJECTED = "rejected"     # Amekataliwa
    SUSPENDED = "suspended"   # Amefutwa/Simamishwa


class Teacher(Base):
    __tablename__ = "teachers"
    
    # ==========================
    # Basic fields
    # ==========================
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone1 = Column(String(20))
    phone2 = Column(String(20))
    
    # ==========================
    # Role & Status
    # ==========================
    role = Column(String(50), nullable=False, default="Mwalimu")  # PRIMARY: Kiswahili
    
    # 🔥 Teacher status - pending, active, rejected, suspended
    status = Column(String(20), nullable=False, default="pending")
    
    # 🔥 Who approved this teacher
    approved_by = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    
    # 🔥 When was this teacher approved
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # 🔥 Rejection reason (if rejected)
    rejection_reason = Column(String(500), nullable=True)
    
    # ==========================
    # Password & Auth
    # ==========================
    password_hash = Column(String(255), nullable=False)
    
    # 🔥 Can this teacher login?
    active = Column(Boolean, default=False)
    
    # ==========================
    # Timestamps
    # ==========================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # ==========================
    # Foreign Keys
    # ==========================
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    
    # 🔥 Previous school (for transfers)
    previous_school_id = Column(Integer, ForeignKey("schools.id", ondelete="SET NULL"), nullable=True)
    
    # 🔥 When was this teacher transferred
    transferred_at = Column(DateTime(timezone=True), nullable=True)

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 School (Shule ya mwalimu)
    #school = relationship("School", foreign_keys=[school_id], back_populates="teachers")
    
    # 🔥 Previous School (Shule ya awali)
    #previous_school = relationship("School", foreign_keys=[previous_school_id])
    
    # 🔥 Approver (Aliyeidhinisha mwalimu)
    approver = relationship("Teacher", foreign_keys=[approved_by], remote_side=[id])
    
    # 🔥 Marks (Alama zilizoingizwa na mwalimu huyu)
    # 🔥 MUHIMU: Mwalimu akifutwa, marks zinabaki (SET NULL kwenye model ya Mark)
    marks = relationship("Mark", back_populates="teacher")
    
    # 🔥 Teacher Subjects (Mapangio ya mwalimu huyu)
    teacher_subjects = relationship("TeacherSubject", back_populates="teacher", cascade="all, delete-orphan")
    
    # 🔥 School Classes (Madarasa anayofundisha mwalimu huyu)
    school_classes = relationship("SchoolClass", secondary="teacher_classes", back_populates="teachers")
    
    # 🔥 Student Reports (Ripoti alizoandaa mwalimu huyu)
    student_reports = relationship("StudentReport", back_populates="teacher")

    # ==========================
    # Password helpers
    # ==========================
    def set_password(self, password: str):
        if not password:
            raise ValueError("Password cannot be empty")
        truncated_password = password[:72]
        self.password_hash = pwd_context.hash(truncated_password)
    
    def check_password(self, password: str) -> bool:
        truncated_password = password[:72]
        return pwd_context.verify(truncated_password, self.password_hash)
    
    @property
    def password(self):
        raise AttributeError("Password is write-only")
    
    # ==========================
    # 🔥 Status helper methods
    # ==========================
    def is_pending(self) -> bool:
        """Check if teacher is pending approval"""
        return self.status == "pending"
    
    def is_active(self) -> bool:
        """Check if teacher is active"""
        return self.status == "active" and self.active
    
    def is_rejected(self) -> bool:
        """Check if teacher was rejected"""
        return self.status == "rejected"
    
    def is_suspended(self) -> bool:
        """Check if teacher is suspended"""
        return self.status == "suspended"
    
    def can_login(self) -> bool:
        """Check if teacher can login"""
        return self.status == "active" and self.active
    
    def approve(self, approver_id: int) -> None:
        """Approve this teacher"""
        self.status = "active"
        self.active = True
        self.approved_by = approver_id
        self.approved_at = func.now()
        self.rejection_reason = None
    
    def reject(self, reason: str = "Application rejected") -> None:
        """Reject this teacher"""
        self.status = "rejected"
        self.active = False
        self.rejection_reason = reason
    
    def suspend(self, reason: str = "Teacher suspended") -> None:
        """Suspend this teacher"""
        self.status = "suspended"
        self.active = False
        self.rejection_reason = reason
    
    def reinstate(self) -> None:
        """Reinstate a suspended teacher"""
        self.status = "active"
        self.active = True
        self.rejection_reason = None
    
    def transfer_to(self, new_school_id: int) -> None:
        """Transfer teacher to another school"""
        self.previous_school_id = self.school_id
        self.school_id = new_school_id
        self.transferred_at = func.now()
        # Status inabaki active
        self.status = "active"
        self.active = True
    
    # ==========================
    # Representation
    # ==========================
    def __repr__(self):
        return f"<Teacher {self.username} ({self.role}) - {self.status}>"
    
    def to_dict(self):
        """Convert teacher to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "email": self.email,
            "phone1": self.phone1,
            "phone2": self.phone2,
            "role": self.role,
            "status": self.status,
            "school_id": self.school_id,
            "active": self.active,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "previous_school_id": self.previous_school_id,
            "transferred_at": self.transferred_at.isoformat() if self.transferred_at else None
        }