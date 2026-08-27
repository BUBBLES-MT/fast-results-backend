from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Optional: kuhusisha na shule au class fulani
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)

    # Sender = Teacher
    sender_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    # Recipient = Student (kwa wazazi)
    recipient_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    # Hapa tunahifadhi status ya SMS na timestamp ya kutumwa
    status = Column(String(20), nullable=True)  # e.g. "sent", "failed", "pending"
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships (tutaunganisha baadaye)
    # sender = relationship("Teacher", foreign_keys=[sender_id], back_populates="sent_notifications")
    # recipient = relationship("Student", foreign_keys=[recipient_id], back_populates="received_notifications")

    def __repr__(self):
        return f"<Notification {self.title} from Teacher {self.sender_id} to Student {self.recipient_id} - {self.status}>"