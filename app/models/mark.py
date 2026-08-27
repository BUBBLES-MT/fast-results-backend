from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Mark(Base):
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    
    # ============================================================
    # 🔥 MUHIMU SANA! - Mwalimu akifutwa, alama zibaki!
    # ============================================================
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    
    score = Column(Float, nullable=False)
    exam_type = Column(String(50), nullable=True)  # MIDTERM3, MIDTERM9, TERMINAL, ANNUAL
    
    # ============================================================
    # 🔥 COLUMNS MPYA - MUHIMU SANA!
    # ============================================================
    
    # 🔥 Darasa la mwanafunzi wakati wa mtihani
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=True)
    
    # 🔥 Mwaka wa mtihani (2024, 2025, 2026)
    year = Column(Integer, nullable=True)
    
    # 🔥 Mkondo wa mwanafunzi wakati wa mtihani
    stream_id = Column(Integer, ForeignKey("streams.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================================
    # 🔥 UNIQUE CONSTRAINT - KUZUIZA DUPLICATES!
    # ============================================================
    __table_args__ = (
        UniqueConstraint(
            'student_id', 
            'subject_id', 
            'teacher_id', 
            'exam_type', 
            'year',
            'class_id',
            name='unique_mark_per_exam_year_class'
        ),
    )

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 Student (Mwanafunzi)
    student = relationship("Student", back_populates="marks")
    
    # 🔥 Subject (Somo)
    subject = relationship("Subject", back_populates="marks")
    
    # 🔥 Teacher (Mwalimu) - Inaruhusu NULL!
    teacher = relationship("Teacher", back_populates="marks")
    
    # 🔥 School Class (Darasa)
    school_class = relationship("SchoolClass", back_populates="marks", foreign_keys=[class_id])
    
    # 🔥 Stream (Mkondo)
    stream = relationship("Stream", back_populates="marks")

    def __repr__(self):
        return f"<Mark Student={self.student_id} Subject={self.subject_id} Score={self.score} Exam={self.exam_type} Year={self.year} Class={self.class_id} Stream={self.stream_id}>"