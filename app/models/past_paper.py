from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class PastPaper(Base):
    __tablename__ = "past_papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject = Column(String(100), nullable=False)
    exam_type = Column(String(50), nullable=False)  # Midterm, Terminal, Annual, National
    year = Column(Integer, nullable=False)
    class_level = Column(String(50), nullable=False)  # Form 1-4, Std 1-7, Form 5-6
    school_level = Column(String(50), nullable=False)  # primary, secondary, advanced
    file_url = Column(String(500), nullable=False)  # Path to uploaded file
    file_name = Column(String(200), nullable=False)
    file_size = Column(Integer, nullable=True)  # File size in bytes
    description = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    downloads = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())