from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"

    id = Column(Integer, primary_key=True, index=True)
    
    # ============================================================
    # 🔥 FOREIGN KEYS
    # ============================================================
    
    # 🔥 Teacher (Mwalimu)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    
    # 🔥 Subject (Somo)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    
    # 🔥 Class (Darasa)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    
    # 🔥 Stream (Mkondo)
    stream_id = Column(Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)

    # ============================================================
    # 🔥 COLUMNS MPYA
    # ============================================================
    
    # 🔥 Ikiwa mwalimu ndiye mwalimu mkuu wa somo hili
    is_main_teacher = Column(Boolean, default=False)
    
    # 🔥 Ikiwa assignment ni active
    is_active = Column(Boolean, default=True)
    
    # 🔥 Tarehe ya kuanza kufundisha
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # 🔥 Tarehe ya kuacha kufundisha (kama ipo)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # ============================================================
    # 🔥 UNIQUE CONSTRAINTS - KUZUIZA DUPLICATES!
    # ============================================================
    __table_args__ = (
        # 🔥 Mwalimu mmoja hawezi kufundisha somo moja katika darasa moja na mkondo mmoja mara mbili
        UniqueConstraint(
            'teacher_id', 
            'subject_id', 
            'class_id', 
            'stream_id', 
            name='uq_teacher_subject_class_stream'
        ),
        # 🔥 Somo moja katika darasa moja na mkondo mmoja linafundishwa na mwalimu mmoja tu
        UniqueConstraint(
            'subject_id', 
            'class_id', 
            'stream_id', 
            name='uq_subject_class_stream'
        ),
    )

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 Teacher (Mwalimu)
    teacher = relationship("Teacher", back_populates="teacher_subjects")
    
    # 🔥 Subject (Somo)
    subject = relationship("Subject", back_populates="teacher_subjects")
    
    # 🔥 School Class (Darasa)
    school_class = relationship("SchoolClass", back_populates="teacher_subjects")
    
    # 🔥 Stream (Mkondo)
    stream = relationship("Stream", back_populates="teacher_subjects")

    def __repr__(self):
        return f"<TeacherSubject teacher_id={self.teacher_id} subject_id={self.subject_id} class_id={self.class_id}>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "subject_id": self.subject_id,
            "class_id": self.class_id,
            "stream_id": self.stream_id,
            "is_main_teacher": self.is_main_teacher,
            "is_active": self.is_active,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None
        }