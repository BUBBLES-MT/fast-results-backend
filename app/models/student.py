from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    # Class & Stream
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    stream_id = Column(Integer, ForeignKey("streams.id", ondelete="SET NULL"), nullable=True)

    # Roll Number
    roll_number = Column(String(20), nullable=True)

    # Gender / Sex
    sex = Column(String(1), nullable=False)  # 'M' au 'F'

    # Guardian Info
    father_name = Column(String(100), nullable=False)
    father_phone = Column(String(20), nullable=False)
    mother_name = Column(String(100), nullable=True)
    mother_phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)

    # Other Info
    health_info = Column(String(255), nullable=True)
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 Marks (Alama za mwanafunzi)
    marks = relationship("Mark", back_populates="student", cascade="all, delete-orphan")
    
    # 🔥 Reports (Ripoti za mwanafunzi)
    reports = relationship("StudentReport", back_populates="student", cascade="all, delete-orphan")
    
    # 🔥 School (Shule ya mwanafunzi)
    school = relationship("School", back_populates="students")
    
    # 🔥 School Class (Darasa la mwanafunzi)
    school_class = relationship("SchoolClass", back_populates="students", foreign_keys=[class_id])
    
    # 🔥 Stream (Mkondo wa mwanafunzi)
    stream = relationship("Stream", back_populates="students")
    
    # ============================================================
    # 🔥 PARENT RELATIONSHIP (MPYA!)
    # ============================================================
    
    # 🔥 Parents (Wazazi wa mwanafunzi - kupitia ParentChild)
    # Mwanafunzi anaweza kuwa na wazazi wengi (baba, mama, mlezi)
    parents = relationship("ParentChild", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.name} ({self.sex})>"
    
    def to_dict(self):
        """Convert student to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "sex": self.sex,
            "roll_number": self.roll_number,
            "school_id": self.school_id,
            "class_id": self.class_id,
            "stream_id": self.stream_id,
            "father_name": self.father_name,
            "father_phone": self.father_phone,
            "mother_name": self.mother_name,
            "mother_phone": self.mother_phone,
            "address": self.address,
            "health_info": self.health_info,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None
        }