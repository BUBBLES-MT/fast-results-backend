from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class StudentReport(Base):
    __tablename__ = "student_reports"

    id = Column(Integer, primary_key=True, index=True)

    # ============================================================
    # 🔥 FOREIGN KEYS
    # ============================================================
    
    # 🔥 Student (Mwanafunzi) - Report inafutwa mwanafunzi akifutwa
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    
    # 🔥 Teacher (Mwalimu) - Report inabaki mwalimu akifutwa
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    
    # 🔥 School Class (Darasa) - Report inabaki darasa likifutwa
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    
    # 🔥 Stream (Mkondo) - Report inabaki mkondo ukifutwa
    stream_id = Column(Integer, ForeignKey("streams.id", ondelete="SET NULL"), nullable=True)

    # ============================================================
    # 🔥 ACADEMIC INFO
    # ============================================================
    
    # 🔥 Muhula wa mtihani (I, II, au II)
    term = Column(String(20), nullable=False)  # I, II, III
    
    # 🔥 Mwaka wa masomo
    year = Column(Integer, nullable=False)
    
    # 🔥 Aina ya mtihani
    exam_type = Column(String(50), nullable=True)  # MIDTERM3, MIDTERM9, TERMINAL, ANNUAL

    # ============================================================
    # 🔥 REPORT FIELDS - PRIMARY (0-50)
    # ============================================================
    
    # 🔥 Jumla ya alama
    total_marks = Column(Float, nullable=False)
    
    # 🔥 Wastani wa alama
    average = Column(Float, nullable=False)
    
    # 🔥 Daraja (A, B, C, D, E) - PRIMARY
    grade = Column(String(5), nullable=False)  # A, B, C, D, E
    
    # 🔥 Nafasi darasani
    position = Column(Integer, nullable=False)
    
    # 🔥 Jumla ya wanafunzi darasani
    total_students = Column(Integer, nullable=False)
    
    # 🔥 Maoni ya mwalimu
    teacher_remarks = Column(Text, nullable=True)
    
    # 🔥 Maoni ya mkuu wa shule
    headmaster_remarks = Column(Text, nullable=True)
    
    # ============================================================
    # 🔥 REPORT FIELDS - SECONDARY (0-100)
    # ============================================================
    
    # 🔥 Points (Kwa secondary)
    points = Column(Integer, nullable=True)
    
    # 🔥 Division (I, II, III, IV) - Kwa secondary
    division = Column(String(5), nullable=True)

    # ============================================================
    # 🔥 METADATA
    # ============================================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ============================================================
    # 🔥 INDEXES - KWA AJILI YA UFANISI
    # ============================================================
    __table_args__ = (
        # 🔥 Index ya haraka kwa queries za student + term + year
        Index('ix_student_term_year', 'student_id', 'term', 'year'),
        
        # 🔥 Index ya haraka kwa queries za class + term + year
        Index('ix_class_term_year', 'class_id', 'term', 'year'),
        
        # 🔥 Index ya haraka kwa queries za year
        Index('ix_report_year', 'year'),
        
        # 🔥 Index ya haraka kwa queries za exam_type
        Index('ix_report_exam_type', 'exam_type'),
    )

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 Student (Mwanafunzi)
    student = relationship("Student", back_populates="reports")
    
    # 🔥 Teacher (Mwalimu)
    teacher = relationship("Teacher", back_populates="student_reports")
    
    # 🔥 School Class (Darasa)
    #school_class = relationship("SchoolClass", back_populates="reports", foreign_keys=[class_id])
    
    # 🔥 Stream (Mkondo)
    #stream = relationship("Stream", back_populates="reports")

    def __repr__(self):
        return f"<StudentReport Student={self.student_id} Term={self.term} Year={self.year} Grade={self.grade}>"