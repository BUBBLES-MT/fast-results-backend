from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.teacher import Teacher
from app.models.school import School
from app.models.mark import Mark
from app.models.student import Student
from app.models.teacher_subject import TeacherSubject
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.subject import Subject
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ================================
# Helper functions - PRIMARY ONLY
# ================================
def get_role_string(role):
    """Convert Enum role to string if needed and normalize"""
    if role is None:
        return None
    
    if hasattr(role, 'value'):
        role_str = role.value
    else:
        role_str = str(role)
    
    # Normalize role strings for comparison
    role_upper = role_str.upper()
    
    # Primary roles (Kiswahili)
    if role_upper == "MWALIMU":
        return "Mwalimu"
    elif role_upper == "MTAALUMA":
        return "Mtaaluma"
    elif role_upper == "MWALIMU MKUU":
        return "Mwalimu Mkuu"
    elif role_upper == "MWALIMU MKUU MSAIDIZI":
        return "Mwalimu Mkuu Msaidizi"
    # Secondary roles (Kiingereza) - for compatibility
    elif role_upper == "TEACHER":
        return "Teacher"
    elif role_upper == "ACADEMIC":
        return "Academic"
    elif role_upper == "HEADMASTER":
        return "Headmaster"
    elif role_upper == "HEADMISTRESS":
        return "Headmistress"
    elif role_upper == "SECOND MASTER":
        return "Second Master"
    elif role_upper == "SECOND MISTRESS":
        return "Second Mistress"
    elif role_upper == "ACCOUNTANT":
        return "Accountant"
    
    return role_str

def has_primary_admin_access(user_role: str) -> bool:
    """Check if role has PRIMARY admin access (case-insensitive)"""
    admin_roles = [
        "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"
    ]
    user_role_normalized = get_role_string(user_role) if user_role else ""
    return user_role_normalized in admin_roles

def is_primary_teacher_role(user_role: str) -> bool:
    """Check if role is a primary teacher (case-insensitive)"""
    teacher_roles = ["Mwalimu"]
    user_role_normalized = get_role_string(user_role) if user_role else ""
    return user_role_normalized in teacher_roles

def verify_primary_school(school_id: int, db: Session) -> School:
    """Verify school exists and is primary"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    if school.school_level != "primary":
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school. Please use secondary endpoint."
        )
    return school

# ================================
# Pydantic Schemas - PRIMARY
# ================================

class TeacherCreate(BaseModel):
    name: str
    username: str
    email: str
    password: str
    phone1: Optional[str] = None
    phone2: Optional[str] = None
    role: str = "Mwalimu"
    school_id: int

class TeacherResponse(BaseModel):
    id: int
    name: str
    username: str
    email: str
    phone1: Optional[str]
    phone2: Optional[str]
    role: str
    school_id: int
    status: str
    active: bool
    approved_at: Optional[datetime]
    approved_by: Optional[int]
    rejection_reason: Optional[str]
    
    class Config:
        from_attributes = True

class TeacherAssignRequest(BaseModel):
    subject_id: int
    class_id: int
    stream_id: int

class TeacherAssignmentResponse(BaseModel):
    teacher_id: int
    teacher_name: str
    subject_id: int
    subject_name: str
    class_id: int
    class_name: str
    stream_id: int
    stream_name: str

class RoleUpdateRequest(BaseModel):
    role: str

# ================================
# API Endpoints - PRIMARY ONLY
# ================================

router = APIRouter(prefix="/primary/teachers", tags=["Primary Teachers"])

# ================================
# 🔥 GET ALL TEACHERS - PRIMARY ONLY
# ================================
@router.get("", response_model=List[TeacherResponse])
def get_primary_teachers(
    school_id: Optional[int] = Query(None, description="Filter by school - primary only"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all teachers for PRIMARY school only"""
    
    # Get user's school
    user_school_id = getattr(current_user, 'school_id', None)
    if not user_school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    verify_primary_school(user_school_id, db)
    
    # Get user role
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    # Superadmin can see all primary teachers
    if isinstance(current_user, SuperAdmin):
        query = db.query(Teacher)
        if school_id:
            verify_primary_school(school_id, db)
            query = query.filter(Teacher.school_id == school_id)
        return query.all()
    
    # Check if user has primary admin access
    if not has_primary_admin_access(user_role_str):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role_str}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma, or SuperAdmin"
        )
    
    query = db.query(Teacher)
    if school_id:
        verify_primary_school(school_id, db)
        query = query.filter(Teacher.school_id == school_id)
    else:
        query = query.filter(Teacher.school_id == user_school_id)
    
    return query.all()

# ================================
# 🔥 GET PENDING TEACHERS - PRIMARY ONLY
# ================================
@router.get("/pending")
def get_primary_pending_teachers(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all pending PRIMARY teacher registrations.
    Only Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma can access.
    """
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    school_id = getattr(current_user, 'school_id', None)
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    verify_primary_school(school_id, db)
    
    # 🔥 Check if user has admin rights
    admin_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    if user_role_str not in admin_roles:
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can view pending teachers"
        )
    
    pending_teachers = db.query(Teacher).filter(
        Teacher.school_id == school_id,
        Teacher.status == "pending"
    ).all()
    
    return {
        "count": len(pending_teachers),
        "teachers": pending_teachers
    }

# ================================
# 🔥 APPROVE TEACHER - PRIMARY ONLY
# ================================
@router.put("/{teacher_id}/approve")
def approve_primary_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Approve a pending PRIMARY teacher.
    Only Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma can approve.
    """
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    school_id = getattr(current_user, 'school_id', None)
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    verify_primary_school(school_id, db)
    
    # 🔥 Check if user has admin rights
    admin_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    if user_role_str not in admin_roles:
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can approve teachers"
        )
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="This teacher does not belong to your school"
        )
    
    # 🔥 Check if teacher already active in another school
    existing_active = db.query(Teacher).filter(
        Teacher.email == teacher.email,
        Teacher.status == "active"
    ).first()
    
    if existing_active and existing_active.id != teacher_id:
        raise HTTPException(
            status_code=400,
            detail=f"Teacher with email '{teacher.email}' is already active in another school"
        )
    
    # 🔥 Approve teacher
    teacher.status = "active"
    teacher.active = True
    teacher.approved_by = current_user.id
    teacher.approved_at = datetime.now()
    teacher.rejection_reason = None
    
    db.commit()
    db.refresh(teacher)
    
    logger.info(f"✅ PRIMARY Teacher {teacher.name} (ID: {teacher.id}) approved by {current_user.name}")
    
    return {
        "message": f"Teacher {teacher.name} has been approved successfully",
        "teacher": {
            "id": teacher.id,
            "name": teacher.name,
            "username": teacher.username,
            "email": teacher.email,
            "role": teacher.role,
            "status": teacher.status,
            "active": teacher.active,
            "approved_at": teacher.approved_at
        }
    }

# ================================
# 🔥 REJECT TEACHER - PRIMARY ONLY
# ================================
@router.put("/{teacher_id}/reject")
def reject_primary_teacher(
    teacher_id: int,
    reason: Optional[str] = Query(None, description="Reason for rejection"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Reject a pending PRIMARY teacher.
    Only Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma can reject.
    """
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    school_id = getattr(current_user, 'school_id', None)
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    verify_primary_school(school_id, db)
    
    admin_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    if user_role_str not in admin_roles:
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can reject teachers"
        )
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="This teacher does not belong to your school"
        )
    
    # 🔥 Reject teacher
    teacher.status = "rejected"
    teacher.active = False
    teacher.rejection_reason = reason or "Application rejected"
    teacher.approved_by = None
    teacher.approved_at = None
    
    db.commit()
    db.refresh(teacher)
    
    logger.info(f"❌ PRIMARY Teacher {teacher.name} (ID: {teacher.id}) rejected by {current_user.name}")
    
    return {
        "message": f"Teacher {teacher.name} has been rejected",
        "teacher": {
            "id": teacher.id,
            "name": teacher.name,
            "username": teacher.username,
            "email": teacher.email,
            "role": teacher.role,
            "status": teacher.status,
            "rejection_reason": teacher.rejection_reason
        }
    }

# ================================
# 🔥 SUSPEND TEACHER - PRIMARY ONLY
# ================================
@router.put("/{teacher_id}/suspend")
def suspend_primary_teacher(
    teacher_id: int,
    reason: Optional[str] = Query(None, description="Reason for suspension"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Suspend a PRIMARY teacher.
    Only Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma can suspend.
    """
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    school_id = getattr(current_user, 'school_id', None)
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    verify_primary_school(school_id, db)
    
    admin_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    if user_role_str not in admin_roles:
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can suspend teachers"
        )
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="This teacher does not belong to your school"
        )
    
    if teacher_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot suspend yourself")
    
    teacher.status = "suspended"
    teacher.active = False
    teacher.rejection_reason = reason or "Teacher suspended"
    teacher.approved_by = current_user.id
    
    db.commit()
    db.refresh(teacher)
    
    logger.info(f"⛔ PRIMARY Teacher {teacher.name} (ID: {teacher.id}) suspended by {current_user.name}")
    
    return {
        "message": f"Teacher {teacher.name} has been suspended",
        "teacher": {
            "id": teacher.id,
            "name": teacher.name,
            "username": teacher.username,
            "email": teacher.email,
            "role": teacher.role,
            "status": teacher.status
        }
    }

# ================================
# 🔥 REINSTATE TEACHER - PRIMARY ONLY
# ================================
@router.put("/{teacher_id}/reinstate")
def reinstate_primary_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Reinstate a suspended PRIMARY teacher.
    Only Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma can reinstate.
    """
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    school_id = getattr(current_user, 'school_id', None)
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    verify_primary_school(school_id, db)
    
    admin_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    if user_role_str not in admin_roles:
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can reinstate teachers"
        )
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="This teacher does not belong to your school"
        )
    
    teacher.status = "active"
    teacher.active = True
    teacher.rejection_reason = None
    
    db.commit()
    db.refresh(teacher)
    
    logger.info(f"✅ PRIMARY Teacher {teacher.name} (ID: {teacher.id}) reinstated by {current_user.name}")
    
    return {
        "message": f"Teacher {teacher.name} has been reinstated",
        "teacher": {
            "id": teacher.id,
            "name": teacher.name,
            "username": teacher.username,
            "email": teacher.email,
            "role": teacher.role,
            "status": teacher.status
        }
    }

# ================================
# GET SINGLE TEACHER - PRIMARY
# ================================
@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_primary_teacher(
    teacher_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single PRIMARY teacher by ID"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # 🔥 Verify it's a primary school teacher
    verify_primary_school(teacher.school_id, db)
    
    return teacher

# ================================
# CREATE TEACHER - PRIMARY (ADMIN CREATED = ACTIVE)
# ================================
@router.post("", response_model=TeacherResponse)
def create_primary_teacher(
    teacher_data: TeacherCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new PRIMARY teacher.
    Admin created teachers are AUTO-APPROVED (active).
    """
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role_str}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma, or SuperAdmin"
        )
    
    # 🔥 Check if school exists and is primary
    verify_primary_school(teacher_data.school_id, db)
    
    # Check if username or email exists
    existing = db.query(Teacher).filter(
        (Teacher.username == teacher_data.username) | 
        (Teacher.email == teacher_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # 🔥 ADMIN CREATED = AUTO-APPROVED (active)
    new_teacher = Teacher(
        name=teacher_data.name,
        username=teacher_data.username,
        email=teacher_data.email,
        phone1=teacher_data.phone1,
        phone2=teacher_data.phone2,
        role=teacher_data.role,
        school_id=teacher_data.school_id,
        active=True,
        status="active",  # 🔥 AUTO-APPROVED
        approved_by=current_user.id,
        approved_at=datetime.now()
    )
    new_teacher.set_password(teacher_data.password)
    
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    
    logger.info(f"✅ PRIMARY Teacher created (auto-approved): {new_teacher.name} (ID: {new_teacher.id}) by {current_user.name}")
    return new_teacher



# ============================================================
# 🔥 DELETE TEACHER - PRIMARY (ILIYOBORESHA KAMILI)
# ============================================================
@router.delete("/{teacher_id}")
def delete_primary_teacher(
    teacher_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a PRIMARY teacher.
    
    🔥 HII NDO INAFANYA:
    1. Inafuta Marks zote za mwalimu huyu
    2. Inafuta Assignments zote za mwalimu huyu
    3. Inafuta mwalimu mwenyewe
    4. WANAFUNZI WANABAKI! (Hawafutwi)
    """
    
    # ============================================================
    # 🔥 PERMISSION CHECK
    # ============================================================
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role_str}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma, or SuperAdmin"
        )
    
    # ============================================================
    # 🔥 FIND TEACHER
    # ============================================================
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # ============================================================
    # 🔥 VERIFY PRIMARY SCHOOL
    # ============================================================
    verify_primary_school(teacher.school_id, db)
    
    teacher_name = teacher.name
    teacher_id_val = teacher.id
    school_id = teacher.school_id
    
    logger.info(f"🗑️ Starting deletion for PRIMARY teacher: {teacher_name} (ID: {teacher_id_val})")
    
    # ============================================================
    # 🔥 1. DELETE MARKS (Alama za mwalimu huyu)
    # ============================================================
    marks_count = db.query(Mark).filter(Mark.teacher_id == teacher_id_val).count()
    db.query(Mark).filter(Mark.teacher_id == teacher_id_val).delete()
    logger.info(f"✅ Deleted {marks_count} marks for teacher {teacher_name}")
    
    # ============================================================
    # 🔥 2. DELETE ASSIGNMENTS (Mapangio ya mwalimu huyu)
    # ============================================================
    assignments_count = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == teacher_id_val
    ).count()
    db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == teacher_id_val
    ).delete()
    logger.info(f"✅ Deleted {assignments_count} assignments for teacher {teacher_name}")
    
    # ============================================================
    # 🔥 3. DELETE THE TEACHER (Mwalimu mwenyewe)
    # ============================================================
    db.delete(teacher)
    db.commit()
    logger.info(f"✅ PRIMARY Teacher {teacher_name} (ID: {teacher_id_val}) deleted")
    
    # ============================================================
    # 🔥 4. CHECK STUDENTS REMAIN (Wanafunzi wabaki)
    # ============================================================
    students_count = db.query(Student).filter(Student.school_id == school_id).count()
    logger.info(f"👨‍🎓 Students remaining in school: {students_count}")
    
    # ============================================================
    # 🔥 RETURN RESPONSE
    # ============================================================
    return {
        "message": "Teacher deleted successfully",
        "teacher_name": teacher_name,
        "teacher_id": teacher_id_val,
        "marks_deleted": marks_count,
        "assignments_deleted": assignments_count,
        "students_remaining": students_count,
        "note": "Students and their data remain intact"
    }

# ================================
# UPDATE TEACHER ROLE - PRIMARY
# ================================
@router.put("/{teacher_id}/role")
def update_primary_teacher_role(
    teacher_id: int,
    request: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update PRIMARY teacher role"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # 🔥 Verify it's a primary school teacher
    verify_primary_school(teacher.school_id, db)
    
    teacher.role = request.role
    db.commit()
    db.refresh(teacher)
    
    return {"message": f"Role updated to {request.role}", "teacher_id": teacher.id, "role": teacher.role}

# ================================
# ASSIGN TEACHER TO SUBJECT - PRIMARY
# ================================
@router.post("/{teacher_id}/assign", response_model=TeacherAssignmentResponse)
def assign_primary_teacher_to_subject(
    teacher_id: int,
    assignment: TeacherAssignRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Assign a PRIMARY teacher to teach a specific subject in a class and stream"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if teacher exists
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # 🔥 Verify it's a primary school teacher
    verify_primary_school(teacher.school_id, db)
    
    # Check if class exists and belongs to school
    school_class = db.query(SchoolClass).filter(
        SchoolClass.id == assignment.class_id,
        SchoolClass.school_id == teacher.school_id
    ).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found or does not belong to school")
    
    # Check if stream exists and belongs to school
    stream = db.query(Stream).filter(
        Stream.id == assignment.stream_id,
        Stream.school_id == teacher.school_id
    ).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found or does not belong to school")
    
    # Check if subject exists and belongs to school
    subject = db.query(Subject).filter(
        Subject.id == assignment.subject_id,
        Subject.school_id == teacher.school_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found or does not belong to school")
    
    # Check if assignment already exists
    existing = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == teacher_id,
        TeacherSubject.class_id == assignment.class_id,
        TeacherSubject.stream_id == assignment.stream_id,
        TeacherSubject.subject_id == assignment.subject_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Teacher is already assigned to teach {subject.name} in {school_class.name} {stream.name}"
        )
    
    # Create assignment
    new_assignment = TeacherSubject(
        teacher_id=teacher_id,
        class_id=assignment.class_id,
        stream_id=assignment.stream_id,
        subject_id=assignment.subject_id
    )
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    
    logger.info(f"✅ Teacher {teacher.name} assigned to {subject.name} in {school_class.name} {stream.name}")
    
    return TeacherAssignmentResponse(
        teacher_id=teacher.id,
        teacher_name=teacher.name,
        subject_id=subject.id,
        subject_name=subject.name,
        class_id=school_class.id,
        class_name=school_class.name,
        stream_id=stream.id,
        stream_name=stream.name
    )

# ================================
# GET TEACHER ASSIGNMENTS - PRIMARY
# ================================
@router.get("/{teacher_id}/assignments")
def get_primary_teacher_assignments(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all assignments for a PRIMARY teacher"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str) and not is_primary_teacher_role(user_role_str):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Teacher can only see their own assignments
    if is_primary_teacher_role(user_role_str) and current_user.id != teacher_id:
        raise HTTPException(status_code=403, detail="You can only view your own assignments")
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher:
        verify_primary_school(teacher.school_id, db)
    
    assignments = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == teacher_id
    ).all()
    
    result = []
    for ass in assignments:
        subject = db.query(Subject).filter(Subject.id == ass.subject_id).first()
        school_class = db.query(SchoolClass).filter(SchoolClass.id == ass.class_id).first()
        stream = db.query(Stream).filter(Stream.id == ass.stream_id).first()
        
        result.append({
            "id": ass.id,
            "subject_id": ass.subject_id,
            "subject_name": subject.name if subject else "Unknown",
            "class_id": ass.class_id,
            "class_name": school_class.name if school_class else "Unknown",
            "stream_id": ass.stream_id,
            "stream_name": stream.name if stream else "Unknown"
        })
    
    return result

# ================================
# DELETE TEACHER ASSIGNMENT - PRIMARY
# ================================
@router.delete("/{teacher_id}/assignments/{assignment_id}")
def delete_primary_teacher_assignment(
    teacher_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY teacher assignment"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role_str):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    assignment = db.query(TeacherSubject).filter(
        TeacherSubject.id == assignment_id,
        TeacherSubject.teacher_id == teacher_id
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher:
        verify_primary_school(teacher.school_id, db)
    
    db.delete(assignment)
    db.commit()
    
    return {"message": "Assignment deleted successfully"}

# ================================
# GET MY ASSIGNMENTS - PRIMARY TEACHER
# ================================
@router.get("/me/assignments")
def get_my_primary_assignments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all assignments for the current logged in PRIMARY teacher"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else ""
    
    if not isinstance(current_user, Teacher) and not is_primary_teacher_role(user_role_str):
        raise HTTPException(status_code=403, detail="Only primary teachers can access this endpoint")
    
    # 🔥 Verify it's a primary school teacher
    verify_primary_school(current_user.school_id, db)
    
    assignments = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == current_user.id
    ).all()
    
    result = []
    for ass in assignments:
        subject = db.query(Subject).filter(Subject.id == ass.subject_id).first()
        school_class = db.query(SchoolClass).filter(SchoolClass.id == ass.class_id).first()
        stream = db.query(Stream).filter(Stream.id == ass.stream_id).first()
        
        result.append({
            "id": ass.id,
            "subject_id": ass.subject_id,
            "subject_name": subject.name if subject else f"Subject {ass.subject_id}",
            "class_id": ass.class_id,
            "class_name": school_class.name if school_class else f"Class {ass.class_id}",
            "stream_id": ass.stream_id,
            "stream_name": stream.name if stream else f"Stream {ass.stream_id}",
        })
    
    return result

# ================================
# GET MY SUBJECTS - PRIMARY TEACHER
# ================================
@router.get("/me/subjects")
def get_my_primary_subjects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get subjects taught by the current PRIMARY teacher"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else ""
    
    if not isinstance(current_user, Teacher) and not is_primary_teacher_role(user_role_str):
        raise HTTPException(status_code=403, detail="Only primary teachers can access this endpoint")
    
    # 🔥 Verify it's a primary school teacher
    verify_primary_school(current_user.school_id, db)
    
    assignments = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == current_user.id
    ).all()
    
    subject_ids = set()
    for assignment in assignments:
        subject_ids.add(assignment.subject_id)
    
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "code": getattr(s, 'code', '')
        }
        for s in subjects
    ]



# ============================================================
# 🔥 GET MY DASHBOARD - PRIMARY TEACHER & ADMIN
# ============================================================
@router.get("/me/dashboard")
def get_primary_teacher_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🎯 PRIMARY DASHBOARD DATA - Works for both Teacher and Admin
    
    🔥 MWALIMU: Shows their own data (students, classes, subjects)
    🔥 ADMIN (Mtaaluma, Mwalimu Mkuu, Mwalimu Mkuu Msaidizi): Shows ALL school data
    """
    
    # ============================================================
    # 🔥 SECURITY CHECK - ALLOW PRIMARY TEACHER AND ADMIN
    # ============================================================
    user_role = getattr(current_user, 'role', None)
    user_role_str = get_role_string(user_role) if user_role else "Unknown"
    
    # ✅ Ruhusu Mwalimu na Wasimamizi wote wa Primary
    allowed_roles = ["Mwalimu", "Mtaaluma", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi"]
    
    if user_role_str not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized. Your role: {user_role_str}. Allowed: Mwalimu, Mtaaluma, Mwalimu Mkuu, Mwalimu Mkuu Msaidizi"
        )
    
    # ✅ ANGALIA KAMA NI MWALIMU AU ADMIN
    is_teacher = user_role_str == "Mwalimu"
    is_admin = user_role_str in ["Mtaaluma", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi"]
    
    teacher_id = current_user.id
    school_id = current_user.school_id
    
    logger.info(f"📊 Primary dashboard requested: {current_user.name} (Role: {user_role_str}, ID: {teacher_id})")
    
    # ============================================================
    # 🔥 PATA JINA LA SHULE
    # ============================================================
    school = db.query(School).filter(School.id == school_id).first()
    school_name = school.name if school else None
    
    # ============================================================
    # 🔥 FUNCTION YA KUSAIDIA - KUJENGA CLASS DATA
    # ============================================================
    def build_class_data(classes, school_id, db):
        """Build class data with stream names from relationship"""
        class_data = {}
        
        for cls in classes:
            stream_name = None
            if cls.streams:
                for stream in cls.streams:
                    stream_name = stream.name
                    break
            
            student_count = db.query(Student).filter(
                Student.class_id == cls.id,
                Student.school_id == school_id
            ).count()
            
            class_data[cls.id] = {
                "class_id": cls.id,
                "class_name": cls.name,
                "stream_name": stream_name,
                "student_count": student_count,
                "subjects": []
            }
        
        return class_data
    
    # ============================================================
    # 🔥 FUNCTION YA KUPATA MARKS KWA SCHOOL
    # ============================================================
    def get_marks_count_by_school(school_id, db):
        """Get total marks for a school using Student relationship"""
        try:
            marks_count = db.query(Mark).join(Student, Mark.student_id == Student.id).filter(
                Student.school_id == school_id
            ).count()
            return marks_count
        except Exception as e:
            logger.error(f"Error getting marks count: {e}")
            return 0
    
    # ============================================================
    # 🔥 IKIWA ADMIN - RUDISHA DATA ZOTE ZA SHULE
    # ============================================================
    if is_admin:
        logger.info(f"🏫 Admin dashboard for school {school_id}")
        
        # Pata data zote za shule
        all_classes = db.query(SchoolClass).filter(
            SchoolClass.school_id == school_id
        ).all()
        
        all_subjects = db.query(Subject).filter(
            Subject.school_id == school_id
        ).all()
        
        all_students = db.query(Student).filter(
            Student.school_id == school_id
        ).all()
        
        all_marks = get_marks_count_by_school(school_id, db)
        
        all_teachers = db.query(Teacher).filter(
            Teacher.school_id == school_id,
            Teacher.status == "active"
        ).count()
        
        # Build class data for admin
        class_data_admin = build_class_data(all_classes, school_id, db)
        
        # ✅ FIX: Ongeza subjects kwa kila darasa
        for cls in all_classes:
            # ✅ Subject haina class_id, tumia school_id tu
            class_subjects = db.query(Subject).filter(
                Subject.school_id == school_id
            ).all()
            
            for subject in class_subjects:
                if cls.id in class_data_admin:
                    class_data_admin[cls.id]["subjects"].append({
                        "subject_id": subject.id,
                        "subject_name": subject.name,
                        "subject_code": getattr(subject, 'code', '')
                    })
        
        # Recent activities - Admin (Kiswahili)
        recent_activities_admin = [
            f"🏫 Shule: {school_name or school_id}",
            f"👨‍🎓 Jumla ya Wanafunzi: {len(all_students)}",
            f"👨‍🏫 Jumla ya Walimu: {all_teachers}",
            f"📚 Jumla ya Masomo: {len(all_subjects)}",
            f"📝 Jumla ya Alama: {all_marks}"
        ]
        
        return {
            "teacher": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "role": current_user.role,
                "phone": getattr(current_user, 'phone1', None),
                "is_admin": True,
                "school_id": school_id,
                "school_name": school_name
            },
            "stats": {
                "total_students": len(all_students),
                "total_classes": len(all_classes),
                "total_subjects": len(all_subjects),
                "marks_entered": all_marks,
                "total_teachers": all_teachers
            },
            "classes": list(class_data_admin.values()),
            "subjects": [
                {
                    "id": s.id,
                    "name": s.name,
                    "code": getattr(s, 'code', '')
                }
                for s in all_subjects
            ],
            "recent_activities": recent_activities_admin,
            "upcoming_exams": []
        }
    
    # ============================================================
    # 🔥 IKIWA MWALIMU - RUDISHA DATA ZAKE TU
    # ============================================================
    logger.info(f"👨‍🏫 Mwalimu dashboard for {current_user.name}")
    
    # 📚 1. GET TEACHER'S ASSIGNMENTS (Classes & Subjects)
    assignments = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == teacher_id
    ).all()
    
    if not assignments:
        logger.warning(f"⚠️ Mwalimu {current_user.name} hana masomo aliyopangiwa")
        return {
            "teacher": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "role": current_user.role,
                "is_admin": False,
                "school_id": school_id,
                "school_name": school_name
            },
            "stats": {
                "total_students": 0,
                "total_classes": 0,
                "total_subjects": 0,
                "marks_entered": 0
            },
            "classes": [],
            "subjects": [],
            "recent_activities": ["📚 Hujapewa masomo bado"],
            "upcoming_exams": []
        }
    
    # 🏫 2. GET UNIQUE CLASSES
    class_ids = list(set([a.class_id for a in assignments]))
    classes = db.query(SchoolClass).filter(
        SchoolClass.id.in_(class_ids)
    ).all()
    
    # 📖 3. GET UNIQUE SUBJECTS
    subject_ids = list(set([a.subject_id for a in assignments]))
    subjects = db.query(Subject).filter(
        Subject.id.in_(subject_ids)
    ).all()
    
    # 👨‍🎓 4. GET STUDENTS IN TEACHER'S CLASSES
    students = db.query(Student).filter(
        Student.class_id.in_(class_ids),
        Student.school_id == school_id
    ).all()
    
    # 📝 5. GET MARKS ENTERED BY THIS TEACHER
    marks_count = db.query(Mark).filter(
        Mark.teacher_id == teacher_id
    ).count()
    
    # 🏗️ 6. BUILD CLASS STRUCTURE WITH SUBJECTS
    class_data = build_class_data(classes, school_id, db)
    
    # Add subjects to each class
    for ass in assignments:
        if ass.class_id in class_data:
            subject = db.query(Subject).filter(Subject.id == ass.subject_id).first()
            if subject:
                class_data[ass.class_id]["subjects"].append({
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "subject_code": getattr(subject, 'code', '')
                })
    
    # 📋 7. RECENT ACTIVITIES (Last 5) - Kiswahili
    recent_activities = []
    
    # Get recent marks entered
    recent_marks = db.query(Mark).filter(
        Mark.teacher_id == teacher_id
    ).order_by(Mark.created_at.desc()).limit(3).all()
    
    for mark in recent_marks:
        student = db.query(Student).filter(Student.id == mark.student_id).first()
        subject = db.query(Subject).filter(Subject.id == mark.subject_id).first()
        if student and subject:
            recent_activities.append(
                f"📝 Umeingiza alama {mark.score}% kwa {student.name} katika {subject.name}"
            )
    
    # Get recent students added to teacher's classes
    recent_students = db.query(Student).filter(
        Student.class_id.in_(class_ids),
        Student.school_id == school_id
    ).order_by(Student.enrollment_date.desc()).limit(2).all()
    
    for student in recent_students:
        cls = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        if cls:
            recent_activities.append(
                f"👨‍🎓 Mwanafunzi mpya {student.name} ameongezwa kwenye {cls.name}"
            )
    
    # ✅ 8. RETURN RESPONSE
    return {
        "teacher": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "phone": getattr(current_user, 'phone1', None),
            "is_admin": False,
            "school_id": school_id,
            "school_name": school_name
        },
        "stats": {
            "total_students": len(students),
            "total_classes": len(classes),
            "total_subjects": len(subjects),
            "marks_entered": marks_count
        },
        "classes": list(class_data.values()),
        "subjects": [
            {
                "id": s.id,
                "name": s.name,
                "code": getattr(s, 'code', '')
            }
            for s in subjects
        ],
        "recent_activities": recent_activities[:5],
        "upcoming_exams": []
    }


















































# app/api/v1/primary/teachers.py

# ============================================================
# 🔥 GET HEADMASTER - PRIMARY (MWALIMU MKUU PEKEE!)
# ============================================================
@router.get("/schools/{school_id}/headmaster")
def get_primary_headmaster(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 GET HEADMASTER - PRIMARY SCHOOL
    Pata Mkuu wa Shule: Mwalimu Mkuu PEKEE!
    HAKUNA FALLBACK - KAMA HAKUNA, RUDISHA ERROR!
    """
    
    # ✅ HAKIKISHA SHULE IPO
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # ✅ ANGALIA SCHOOL LEVEL
    if school.school_level != "primary":
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for primary schools only"
        )
    
    # 🔥🔥🔥 TAFUTA MWALIMU MKUU PEKEE! 🔥🔥🔥
    # USITAFUTE MWALIMU MWINGINE!
    headmaster = db.query(Teacher).filter(
        Teacher.school_id == school_id,
        Teacher.role == "Mwalimu Mkuu",  # 🔥 HII TU!
        Teacher.status == "active",
        Teacher.active == True
    ).first()
    
    if headmaster:
        return {
            "id": headmaster.id,
            "name": headmaster.name,
            "email": headmaster.email,
            "role": headmaster.role,
            "phone": headmaster.phone1,
            "status": headmaster.status,
            "school_id": headmaster.school_id
        }
    
    # 🔥🔥🔥 KAMA HAKUNA MWALIMU MKUU - RUDISHA ERROR! 🔥🔥🔥
    # USICHUKUE MWALIMU MWINGINE!
    raise HTTPException(
        status_code=404,
        detail=f"No Mwalimu Mkuu found for school ID {school_id}"
    )