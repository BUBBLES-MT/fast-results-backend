# app/models/parent_child.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship as rel  # 🔥 NIMEBADILISHA JINA LA IMPORT!
from app.core.database import Base


class ParentChild(Base):
    __tablename__ = "parent_children"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    
    # ============================================================
    # 🔥 COLUMN - INAFANANA NA DATABASE (relationship)
    # ============================================================
    relationship = Column(String(50), default="Biological")  # 🔥 HII NI COLUMN
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================================
    # 🔥 RELATIONSHIPS - TUMIA "rel" BADALA YA "relationship"
    # ============================================================
    parent = rel("Parent", back_populates="children")
    student = rel("Student", back_populates="parents")

    def __repr__(self):
        return f"<ParentChild parent={self.parent_id} student={self.student_id}>"