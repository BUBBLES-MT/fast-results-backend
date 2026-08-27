from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)

    # Foreign Keys
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 School Class (Darasa la mkondo huu)
    school_class = relationship("SchoolClass", back_populates="streams")
    
    # 🔥 School (Shule)
    school = relationship("School", back_populates="streams")
    
    # 🔥 Students (Wanafunzi wa mkondo huu)
    students = relationship("Student", back_populates="stream")
    
    # 🔥 Teacher Subjects (Mapangio ya walimu kwa mkondo huu)
    teacher_subjects = relationship("TeacherSubject", back_populates="stream")
    
    # 🔥 Marks (Alama za mkondo huu)
    marks = relationship("Mark", back_populates="stream")

    def __repr__(self):
        return f"<Stream {self.name}>"