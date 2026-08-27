# app/schemas/school_announcement.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class AnnouncementLanguage(str, Enum):
    SWAHILI = "swahili"
    ENGLISH = "english"
    BOTH = "both"

class SchoolAnnouncementBase(BaseModel):
    closing_date: Optional[datetime] = None
    opening_date: Optional[datetime] = None
    announcement_sw: Optional[str] = None
    announcement_en: Optional[str] = None
    parent_meeting_notes_sw: Optional[str] = None
    parent_meeting_notes_en: Optional[str] = None
    language: Optional[AnnouncementLanguage] = AnnouncementLanguage.BOTH

class SchoolAnnouncementCreate(SchoolAnnouncementBase):
    school_id: int

class SchoolAnnouncementUpdate(SchoolAnnouncementBase):
    pass

class SchoolAnnouncementResponse(SchoolAnnouncementBase):
    id: int
    school_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True