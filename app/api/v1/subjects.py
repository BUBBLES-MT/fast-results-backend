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
# Helper function to get role string
# ================================
def get_role_string(role):
    """Convert Enum role to string if needed"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

# ================================
# 🔥 Pydantic Schemas - ZIMEBADILISHWA!
# ================================

class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    school_id: int
    level: str = "secondary"  # 🔥 ADDED: default secondary
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
# 🔥 API Endpoints - ZIMEBADILISHWA KABISA!
# ================================

router = APIRouter()

@router.get("/subjects", response_model=List[SubjectResponse])
def get_all_subjects(
    school_id: Optional[int] = Query(None, description="Filter by school"),
    level: Optional[str] = Query(None, description="Filter by level: primary, secondary, advanced"),
    subject_type: Optional[str] = Query(None, description="Filter by subject type: Core, Optional, Extra"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all subjects with optional filters.
    🔥 NEW: Auto-filters by user's school_id and level!
    """
    logger.info(f"🔍 User: {current_user.id}, Role: {getattr(current_user, 'role', 'Unknown')}")
    logger.info(f"🔍 Level filter: {level}")
    logger.info(f"🔍 School filter: {school_id}")
    
    query = db.query(Subject)
    
    # 🔥 AUTO-FILTER: If user is not SuperAdmin, filter by their school_id
    if not isinstance(current_user, SuperAdmin):
        # Get user's school_id from user object
        user_school_id = getattr(current_user, 'school_id', None)
        if user_school_id:
            logger.info(f"🔍 Filtering by user's school_id: {user_school_id}")
            query = query.filter(Subject.school_id == user_school_id)
        else:
            # If user has no school_id, try to get it from teacher or academic
            if hasattr(current_user, 'teacher') and current_user.teacher:
                teacher_school_id = getattr(current_user.teacher, 'school_id', None)
                if teacher_school_id:
                    logger.info(f"🔍 Filtering by teacher's school_id: {teacher_school_id}")
                    query = query.filter(Subject.school_id == teacher_school_id)
    
    # 🔥 Override if school_id is provided in query
    if school_id:
        logger.info(f"🔍 Overriding with provided school_id: {school_id}")
        query = query.filter(Subject.school_id == school_id)
    
    # 🔥 Filter by level
    if level:
        logger.info(f"🔍 Filtering by level: {level}")
        query = query.filter(Subject.level == level)
    
    # 🔥 Filter by subject type
    if subject_type:
        logger.info(f"🔍 Filtering by subject_type: {subject_type}")
        query = query.filter(Subject.subject_type == subject_type)
    
    subjects = query.order_by(Subject.display_order, Subject.name).all()
    
    logger.info(f"📚 Found {len(subjects)} subjects")
    for sub in subjects:
        logger.info(f"   - {sub.name} ({sub.level}) - School: {sub.school_id}")
    
    return subjects

@router.get("/subjects/by-level/{level}", response_model=List[SubjectResponse])
def get_subjects_by_level(
    level: str,
    school_id: Optional[int] = Query(None, description="Filter by school"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 NEW ENDPOINT: Get all subjects for a specific level.
    Automatically filters by user's school.
    """
    logger.info(f"🔍 Getting subjects for level: {level}")
    
    query = db.query(Subject).filter(Subject.level == level)
    
    # 🔥 Auto-filter by user's school
    if not isinstance(current_user, SuperAdmin):
        user_school_id = getattr(current_user, 'school_id', None)
        if user_school_id:
            query = query.filter(Subject.school_id == user_school_id)
    
    if school_id:
        query = query.filter(Subject.school_id == school_id)
    
    subjects = query.order_by(Subject.display_order, Subject.name).all()
    
    logger.info(f"📚 Found {len(subjects)} subjects for level {level}")
    return subjects

@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
def get_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single subject by ID"""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.post("/subjects", response_model=SubjectResponse)
def create_subject(
    subject_data: SubjectCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new subject - only for superadmin, headmaster, academic
    🔥 NEW: Automatically sets level based on school or uses provided level
    """
    
    # Check permissions
    allowed_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not isinstance(current_user, SuperAdmin):
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized. Your role: {user_role}. Allowed roles: {', '.join(allowed_roles)} or SuperAdmin"
            )
    
    # Check if school exists
    school = db.query(School).filter(School.id == subject_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
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

@router.put("/subjects/{subject_id}")
def update_subject(
    subject_id: int, 
    subject_data: SubjectCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update a subject - only for superadmin, headmaster, academic
    🔥 NEW: Can now update 'level'
    """
    
    # Check permissions
    allowed_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not isinstance(current_user, SuperAdmin):
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized. Your role: {user_role}. Allowed roles: {', '.join(allowed_roles)} or SuperAdmin"
            )
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Check if school exists
    school = db.query(School).filter(School.id == subject_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
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

@router.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a subject - only for superadmin, headmaster, academic"""
    
    # Check permissions
    allowed_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not isinstance(current_user, SuperAdmin):
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized. Your role: {user_role}. Allowed roles: {', '.join(allowed_roles)} or SuperAdmin"
            )
    
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    db.delete(subject)
    db.commit()
    return {"message": "Subject deleted successfully"}