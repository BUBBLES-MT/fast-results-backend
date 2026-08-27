from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subject import Subject
from app.models.school import School
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel
import logging

# 🔥 SETUP LOGGING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# Helper function to get role string - NO TRANSLATION
# ================================
def get_role_string(role):
    """Convert Enum role to string if needed - returns original"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

# ================================
# Helper function - PRIMARY ADMIN ONLY
# ================================
def has_primary_admin_access(user_role: str) -> bool:
    """Check if role has PRIMARY admin access - PRIMARY ROLES ONLY"""
    admin_roles = [
        "Mwalimu Mkuu",
        "Mwalimu Mkuu Msaidizi", 
        "Mtaaluma"
    ]
    return user_role in admin_roles

# ================================
# 🔥 Pydantic Schemas - ZIMEBADILISHWA!
# ================================

class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    school_id: int
    level: str = "primary"  # 🔥 ADDED: default primary
    subject_type: Optional[str] = "Core"
    is_calculated: Optional[bool] = True
    is_required: Optional[bool] = True
    display_order: Optional[int] = 0

class SubjectResponse(BaseModel):
    id: int
    name: str
    code: Optional[str]
    school_id: int
    level: str  # 🔥 ADDED: HII NDIO SCHOOL_LEVEL!
    subject_type: Optional[str]
    is_calculated: bool
    is_required: bool
    display_order: Optional[int]
    
    class Config:
        from_attributes = True

# ================================
# API Endpoints - PRIMARY ONLY
# ================================

router = APIRouter(prefix="/primary/subjects", tags=["Primary Subjects"])

# ============================================================
# GET ALL SUBJECTS - PRIMARY ONLY
# ============================================================
@router.get("", response_model=List[SubjectResponse])
def get_primary_subjects(
    school_id: Optional[int] = Query(None, description="Filter by school - primary only"),
    level: Optional[str] = Query(None, description="Filter by level: primary, secondary, advanced"),
    subject_type: Optional[str] = Query(None, description="Filter by subject type: Core, Optional, Extra"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all subjects for PRIMARY school only
    🔥 NEW: Can filter by level and subject_type
    """
    logger.info(f"🔍 Getting PRIMARY subjects for user: {current_user.id}")
    
    # Determine school_id
    target_school_id = school_id
    if not target_school_id:
        if hasattr(current_user, 'school_id') and current_user.school_id:
            target_school_id = current_user.school_id
        else:
            raise HTTPException(status_code=400, detail="School ID required")
    
    # Check if it's a primary school
    school = db.query(School).filter(School.id == target_school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if school.school_level != "primary":
        raise HTTPException(status_code=400, detail="This is not a primary school. Please use secondary endpoint.")
    
    # Get subjects
    query = db.query(Subject).filter(Subject.school_id == target_school_id)
    
    # 🔥 Filter by level
    if level:
        logger.info(f"🔍 Filtering by level: {level}")
        query = query.filter(Subject.level == level)
    
    # 🔥 Filter by subject type
    if subject_type:
        logger.info(f"🔍 Filtering by subject_type: {subject_type}")
        query = query.filter(Subject.subject_type == subject_type)
    
    subjects = query.order_by(Subject.display_order, Subject.name).all()
    
    logger.info(f"📚 Found {len(subjects)} primary subjects")
    return subjects

# ============================================================
# GET SINGLE SUBJECT - PRIMARY ONLY
# ============================================================
@router.get("/{subject_id}", response_model=SubjectResponse)
def get_primary_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single PRIMARY subject by ID"""
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Verify it's a primary school subject
    school = db.query(School).filter(School.id == subject.school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="This is not a primary school subject")
    
    return subject

# ============================================================
# CREATE SUBJECT - PRIMARY ADMIN ONLY
# ============================================================
@router.post("", response_model=SubjectResponse)
def create_primary_subject(
    subject_data: SubjectCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new PRIMARY subject - only for primary admins
    🔥 NEW: Accepts level, subject_type, etc.
    """
    
    # Check permissions - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    # Check if school exists and is primary
    school = db.query(School).filter(School.id == subject_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Cannot add subject to non-primary school")
    
    # Check if subject with same name exists in the same school
    existing = db.query(Subject).filter(
        Subject.name == subject_data.name,
        Subject.school_id == subject_data.school_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject with this name already exists in this school")
    
    # Check if code is unique (if provided)
    if subject_data.code:
        existing_code = db.query(Subject).filter(Subject.code == subject_data.code).first()
        if existing_code:
            raise HTTPException(status_code=400, detail="Subject code already exists")
    
    # 🔥 CREATE with all fields including level
    new_subject = Subject(
        name=subject_data.name,
        code=subject_data.code,
        school_id=subject_data.school_id,
        level=subject_data.level,  # 🔥 ADDED
        subject_type=subject_data.subject_type,
        is_calculated=subject_data.is_calculated,
        is_required=subject_data.is_required,
        display_order=subject_data.display_order
    )
    
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    return new_subject

# ============================================================
# UPDATE SUBJECT - PRIMARY ADMIN ONLY
# ============================================================
@router.put("/{subject_id}")
def update_primary_subject(
    subject_id: int, 
    subject_data: SubjectCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update a PRIMARY subject - only for primary admins
    🔥 NEW: Can update level, subject_type, etc.
    """
    
    # Check permissions - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Verify it's a primary school subject
    school = db.query(School).filter(School.id == subject.school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="This is not a primary school subject")
    
    # Check if school exists and is primary
    new_school = db.query(School).filter(School.id == subject_data.school_id).first()
    if not new_school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if new_school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Cannot move subject to non-primary school")
    
    # Check if another subject with same name exists
    existing = db.query(Subject).filter(
        Subject.name == subject_data.name,
        Subject.school_id == subject_data.school_id,
        Subject.id != subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject with this name already exists")
    
    # Check if code is unique
    if subject_data.code:
        existing_code = db.query(Subject).filter(
            Subject.code == subject_data.code,
            Subject.id != subject_id
        ).first()
        if existing_code:
            raise HTTPException(status_code=400, detail="Subject code already exists")
    
    # 🔥 UPDATE all fields including level
    subject.name = subject_data.name
    subject.code = subject_data.code
    subject.school_id = subject_data.school_id
    subject.level = subject_data.level  # 🔥 ADDED
    subject.subject_type = subject_data.subject_type
    subject.is_calculated = subject_data.is_calculated
    subject.is_required = subject_data.is_required
    subject.display_order = subject_data.display_order
    
    db.commit()
    db.refresh(subject)
    return {"message": "Subject updated successfully", "subject": subject}

# ============================================================
# DELETE SUBJECT - PRIMARY ADMIN ONLY
# ============================================================
@router.delete("/{subject_id}")
def delete_primary_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY subject - only for primary admins"""
    
    # Check permissions - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Verify it's a primary school subject
    school = db.query(School).filter(School.id == subject.school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="This is not a primary school subject")
    
    db.delete(subject)
    db.commit()
    return {"message": "Subject deleted successfully"}