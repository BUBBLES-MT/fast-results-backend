# app/models/school_announcement.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class AnnouncementLanguage(str, enum.Enum):
    SWAHILI = "swahili"
    ENGLISH = "english"
    BOTH = "both"

class SchoolAnnouncement(Base):
    __tablename__ = "school_announcements"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # 🔥 TAREHE ZA KUFUNGA NA KUFUNGUA
    closing_date = Column(DateTime, nullable=True)
    opening_date = Column(DateTime, nullable=True)
    
    # 🔥 TANGAZO - LUGA MBILI
    announcement_sw = Column(Text, nullable=True)   # Kiswahili
    announcement_en = Column(Text, nullable=True)   # Kiingereza
    
    # 🔥 MAELEZO YA MKUTANO WA WAZAZI - LUGA MBILI
    parent_meeting_notes_sw = Column(Text, nullable=True)
    parent_meeting_notes_en = Column(Text, nullable=True)
    
    # 🔥 LUGA INAYOTUMIKA
    language = Column(Enum(AnnouncementLanguage), default=AnnouncementLanguage.BOTH)
    
    # 🔥 NANI ALIYEANDIKA
    created_by = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Integer, default=1)

    def __repr__(self):
        return f"<SchoolAnnouncement school_id={self.school_id}>"