from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.association_tables import teacher_classes

class SchoolClass(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)

    # Link to school
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    
    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE ZIMEACTIVATE!
    # ============================================================
    
    # 🔥 School (Shule)
    school = relationship("School", back_populates="classes")
    
    # 🔥 Students (Wanafunzi wa darasa hili)
    students = relationship("Student", back_populates="school_class", foreign_keys="Student.class_id")
    
    # 🔥 Streams (Mikondo ya darasa hili)
    streams = relationship("Stream", back_populates="school_class")
    
    # 🔥 Teacher Subjects (Mapangio ya walimu kwa darasa hili)
    teacher_subjects = relationship("TeacherSubject", back_populates="school_class")
    
    # 🔥 Teachers (Walimu wa darasa hili - kupitia association table)
    teachers = relationship("Teacher", secondary=teacher_classes, back_populates="school_classes")
    
    # 🔥 Marks (Alama za darasa hili)
    marks = relationship("Mark", back_populates="school_class", foreign_keys="Mark.class_id")
    
    # 🔥 Promote History (Historia ya upandishaji)
    #promote_history = relationship("PromoteHistory", back_populates="school_class")

    def __repr__(self):
        return f"<SchoolClass {self.name}>"