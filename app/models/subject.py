from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=True, index=True)
    
    # ============================================================
    # 🔥 COLUMNS - ZIMEBORESHA!
    # ============================================================
    
    # 🔥 Aina ya somo (Core, Optional, Extra)
    subject_type = Column(String(20), nullable=True, default="Core")
    
    # 🔥 Daraja la somo (Primary, Secondary, Advanced)
    # 🔥 FIXED: nullable=False na default="secondary"
    level = Column(String(20), nullable=False, default="secondary")  # primary, secondary, advanced
    
    # 🔥 Ikiwa somo linahesabiwa kwenye average
    is_calculated = Column(Boolean, default=True)
    
    # 🔥 Ikiwa somo ni la lazima
    is_required = Column(Boolean, default=True)
    
    # 🔥 Mpangilio wa somo (kwa ajili ya UI)
    display_order = Column(Integer, nullable=True, default=0)

    # ============================================================
    # 🔥 RELATIONSHIPS
    # ============================================================
    
    # 🔥 School (Shule)
    school = relationship("School", back_populates="subjects")
    
    # 🔥 Marks (Alama za somo hili)
    marks = relationship("Mark", back_populates="subject", cascade="all, delete-orphan")
    
    # 🔥 Teacher Subjects (Mapangio ya walimu kwa somo hili)
    teacher_subjects = relationship("TeacherSubject", back_populates="subject", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subject {self.name} ({self.code}) - {self.level}>"