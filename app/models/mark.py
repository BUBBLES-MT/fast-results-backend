# app/models/mark.py

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Mark(Base):
    """
    🔥 MARK MODEL - SALAMA KWA ALAMA ZA WANAFUNZI!
    
    KANUNI MUHIMU ZA USALAMA:
    - ✅ Mwalimu akifutwa → Alama ZINABAKI (teacher_id = NULL)
    - ✅ Darasa likifutwa → Alama ZINABAKI (class_id = NULL)
    - ✅ Stream ikifutwa → Alama ZINABAKI (stream_id = NULL)
    - ✅ Somo likifutwa → Alama ZINABAKI (subject_id = NULL)
    - ✅ Mwanafunzi akifutwa → Alama zinafutika (CASCADE - kawaida kwa shule)
    
    Hii inahakikisha historia ya wanafunzi HAIHARIBIKI kamwe!
    """
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True)
    
    # ============================================================
    # 🔥 STUDENT_ID - CASCADE (Mwanafunzi akifutwa, marks zake zinafutika)
    # ============================================================
    # Hii ni sawa kwa mfumo wa shule: mwanafunzi akiondoka, 
    # rekodi zake hazihitajiki
    student_id = Column(
        Integer, 
        ForeignKey("students.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # ============================================================
    # 🔥 SUBJECT_ID - SET NULL (Somo likifutwa, marks ZINABAKI!)
    # ============================================================
    # ⚠️ BADILIKO: Badala ya CASCADE, tumia SET NULL
    # Hii inahakikisha alama za wanafunzi hazifutiki somo likiondolewa
    subject_id = Column(
        Integer, 
        ForeignKey("subjects.id", ondelete="SET NULL"),  # ✅ SET NULL
        nullable=True  # ✅ Inaruhusu NULL
    )
    
    # ============================================================
    # 🔥 TEACHER_ID - SET NULL (Mwalimu akifutwa, marks ZINABAKI!)
    # ============================================================
    teacher_id = Column(
        Integer, 
        ForeignKey("teachers.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # ============================================================
    # 🔥 SCORE - Alama ya mwanafunzi
    # ============================================================
    score = Column(Float, nullable=False)
    
    # ============================================================
    # 🔥 EXAM_TYPE - Aina ya mtihani
    # ============================================================
    # MIDTERM3, MIDTERM9, TERMINAL, ANNUAL, n.k.
    exam_type = Column(String(50), nullable=True)
    
    # ============================================================
    # 🔥 CLASS_ID - SET NULL (Darasa likifutwa, marks ZINABAKI!)
    # ============================================================
    # ⚠️ BADILIKO: Badala ya CASCADE, tumia SET NULL
    # Hii inahakikisha mwalimu hawezi kufuta marks kwa kufuta darasa
    class_id = Column(
        Integer, 
        ForeignKey("classes.id", ondelete="SET NULL"),  # ✅ SET NULL
        nullable=True
    )
    
    # ============================================================
    # 🔥 YEAR - Mwaka wa mtihani
    # ============================================================
    # (2024, 2025, 2026)
    year = Column(Integer, nullable=True)
    
    # ============================================================
    # 🔥 STREAM_ID - SET NULL (Stream ikifutwa, marks ZINABAKI!)
    # ============================================================
    stream_id = Column(
        Integer, 
        ForeignKey("streams.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # ============================================================
    # 🔥 TIMESTAMP
    # ============================================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================================
    # 🔥 UNIQUE CONSTRAINT - KUZUIZA DUPLICATES!
    # ============================================================
    # ⚠️ MUHIMU: teacher_id IMEONDOLEWA!
    # 
    # Kwa nini? Kwa sababu:
    # 1. Mwalimu akifutwa, teacher_id = NULL
    # 2. PostgreSQL inaruhusu NULL != NULL → duplicates zinaweza kutokea
    # 3. Alama ya mwanafunzi inapaswa kuwa MOJA TU kwa somo/mtihani/mwaka/darasa
    #    — haijalishi ni mwalimu gani aliingiza!
    #
    # Kwa hiyo, tunazuia duplicates kwa kutumia:
    # student_id + subject_id + exam_type + year + class_id
    __table_args__ = (
        UniqueConstraint(
            'student_id', 
            'subject_id', 
            # 'teacher_id',  # ❌ IMEONDOLEWA - inasababisha shida!
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
    
    # 🔥 Subject (Somo) - Inaruhusu NULL!
    subject = relationship("Subject", back_populates="marks")
    
    # 🔥 Teacher (Mwalimu) - Inaruhusu NULL!
    teacher = relationship("Teacher", back_populates="marks")
    
    # 🔥 School Class (Darasa) - Inaruhusu NULL!
    school_class = relationship(
        "SchoolClass", 
        back_populates="marks", 
        foreign_keys=[class_id]
    )
    
    # 🔥 Stream (Mkondo) - Inaruhusu NULL!
    stream = relationship("Stream", back_populates="marks")

    def __repr__(self):
        return (
            f"<Mark Student={self.student_id} "
            f"Subject={self.subject_id} "
            f"Score={self.score} "
            f"Exam={self.exam_type} "
            f"Year={self.year} "
            f"Class={self.class_id} "
            f"Stream={self.stream_id} "
            f"Teacher={self.teacher_id}>"
        )