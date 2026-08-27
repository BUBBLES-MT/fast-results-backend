# app/api/v1/school_announcements.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.school_announcement import SchoolAnnouncement
from app.models.school import School
from app.models.teacher import Teacher
from app.schemas.school_announcement import (
    SchoolAnnouncementCreate,
    SchoolAnnouncementUpdate,
    SchoolAnnouncementResponse
)

router = APIRouter(prefix="/school-announcements", tags=["School Announcements"])

# ============================================================
# 🔥 GET SCHOOL ANNOUNCEMENT - PUBLIC (HAZIHITAJI TOKEN) - KWA WAZAZI
# ============================================================

@router.get("/public/{school_id}", response_model=Optional[SchoolAnnouncementResponse])
def get_public_school_announcement(
    school_id: int,
    db: Session = Depends(get_db)
):
    """
    Get school announcement - PUBLIC (no auth required for parents)
    Inatumika na wazazi kuona tangazo kwenye dashboard yao
    """
    
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    return announcement


# ============================================================
# 🔥 GET SCHOOL ANNOUNCEMENT - KWA MZAZI ALIYEINGIA
# ============================================================

@router.get("/parent/{school_id}", response_model=Optional[SchoolAnnouncementResponse])
def get_parent_school_announcement(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get school announcement - KWA MZAZI ALIYEINGIA
    """
    
    # Check if user is a parent
    if not hasattr(current_user, 'user_type') or current_user.user_type != "parent":
        raise HTTPException(status_code=403, detail="Access denied. Parent account required.")
    
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    return announcement


# ============================================================
# 🔥 GET SCHOOL ANNOUNCEMENT - KWA TEACHER (KWA PARENT REPORT PDF)
# ============================================================

@router.get("/teacher/{school_id}", response_model=Optional[SchoolAnnouncementResponse])
def get_teacher_school_announcement(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get school announcement - KWA TEACHER
    Inatumika wakati wa kupakua Parent Report PDF
    """
    
    # Check if user is a teacher or admin
    if not hasattr(current_user, 'role'):
        raise HTTPException(status_code=403, detail="Access denied. Teacher account required.")
    
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    return announcement


# ============================================================
# 🔥 GET SCHOOL ANNOUNCEMENT - IN HITAJI TOKEN
# ============================================================

@router.get("/{school_id}", response_model=Optional[SchoolAnnouncementResponse])
def get_school_announcement(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get school announcement - REQUIRES AUTH"""
    
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    return announcement


# ============================================================
# 🔥 CREATE OR UPDATE SCHOOL ANNOUNCEMENT - KWA TEACHER TU
# ============================================================

@router.post("/{school_id}", response_model=SchoolAnnouncementResponse)
def create_or_update_school_announcement(
    school_id: int,
    data: SchoolAnnouncementCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create or update school announcement - TEACHERS ONLY
    (Mkuu, Makamu, Mtaaluma pekee wanaweza kuandika)
    """
    
    # Check if school exists
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Check if user is authorized (Headmaster, Deputy, Academic)
    if not hasattr(current_user, 'role'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 🔥 ROLES ZOTE (Secondary na Primary)
    allowed_roles = [
        # SECONDARY
        "Headmaster", "Headmistress", 
        "Second Master", "Second Mistress", 
        "Academic", "Accountant",
        # PRIMARY
        "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi",
        "Mtaaluma", "Mhasibu"
    ]
    
    # 🔥 Angalia kama user role inaruhusiwa (case insensitive)
    user_role = current_user.role if hasattr(current_user, 'role') else ""
    user_role_lower = user_role.lower()
    allowed_lower = [r.lower() for r in allowed_roles]
    
    if user_role_lower not in allowed_lower:
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Only Headmaster, Deputy, Academic can update announcements."
        )
    
    # Check if announcement exists
    existing = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    if existing:
        # Update existing
        if data.closing_date is not None:
            # 🔥 🔥 🔥 BADILISHA HAPA - ONDOA TIMEZONE
            if hasattr(data.closing_date, 'tzinfo') and data.closing_date.tzinfo is not None:
                existing.closing_date = data.closing_date.replace(tzinfo=None)
            else:
                existing.closing_date = data.closing_date
        if data.opening_date is not None:
            # 🔥 🔥 🔥 BADILISHA HAPA - ONDOA TIMEZONE
            if hasattr(data.opening_date, 'tzinfo') and data.opening_date.tzinfo is not None:
                existing.opening_date = data.opening_date.replace(tzinfo=None)
            else:
                existing.opening_date = data.opening_date
        if data.announcement_sw is not None:
            existing.announcement_sw = data.announcement_sw
        if data.announcement_en is not None:
            existing.announcement_en = data.announcement_en
        if data.parent_meeting_notes_sw is not None:
            existing.parent_meeting_notes_sw = data.parent_meeting_notes_sw
        if data.parent_meeting_notes_en is not None:
            existing.parent_meeting_notes_en = data.parent_meeting_notes_en
        if data.language is not None:
            existing.language = data.language
        existing.updated_by = current_user.id
        existing.updated_at = func.now()
        
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        # 🔥 🔥 🔥 BADILISHA HAPA - ONDOA TIMEZONE
        closing_date = data.closing_date
        opening_date = data.opening_date
        
        if closing_date and hasattr(closing_date, 'tzinfo') and closing_date.tzinfo is not None:
            closing_date = closing_date.replace(tzinfo=None)
        if opening_date and hasattr(opening_date, 'tzinfo') and opening_date.tzinfo is not None:
            opening_date = opening_date.replace(tzinfo=None)
        
        new_announcement = SchoolAnnouncement(
            school_id=school_id,
            closing_date=closing_date,
            opening_date=opening_date,
            announcement_sw=data.announcement_sw,
            announcement_en=data.announcement_en,
            parent_meeting_notes_sw=data.parent_meeting_notes_sw,
            parent_meeting_notes_en=data.parent_meeting_notes_en,
            language=data.language or "both",
            created_by=current_user.id,
            updated_by=current_user.id,
            is_active=1
        )
        db.add(new_announcement)
        db.commit()
        db.refresh(new_announcement)
        return new_announcement


# ============================================================
# 🔥 DELETE ANNOUNCEMENT (HARIRI)
# ============================================================

@router.delete("/{announcement_id}")
def delete_school_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete school announcement - TEACHERS ONLY"""
    
    # Check if user is authorized
    if not hasattr(current_user, 'role'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Soft delete
    announcement.is_active = 0
    db.commit()
    
    return {"message": "Announcement deleted successfully"}