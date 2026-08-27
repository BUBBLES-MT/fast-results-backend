from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.school_class import SchoolClass
from app.models.school import School
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel

# ================================
# Helper function - PRIMARY ONLY
# ================================

def get_role_string(role):
    """Convert role to string"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

def has_primary_admin_access(user_role: str) -> bool:
    """Check if role has PRIMARY admin access"""
    admin_roles = [
        "Mwalimu Mkuu",
        "Mwalimu Mkuu Msaidizi", 
        "Mtaaluma"
    ]
    return user_role in admin_roles

def is_primary_school(school_id: int, db: Session) -> bool:
    """Check if a school is a primary school"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        return False
    return school.school_level == "primary"

def get_primary_school_ids(db: Session) -> List[int]:
    """Get all primary school IDs - IMEBORESHA!"""
    schools = db.query(School.id).filter(School.school_level == "primary").all()
    return [s[0] for s in schools]

def verify_primary_school_access(school_id: int, db: Session, current_user) -> None:
    """Verify user has access to this primary school"""
    # 🔥 HAKIKISHA SHULE NI PRIMARY
    if not is_primary_school(school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school. Please use secondary endpoint."
        )
    
    # 🔥 HAKIKISHA MTUMIAJI ANA SHULE HII
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and user_school_id != school_id:
        # KAMA SI SUPERADMIN, RUHUSU TU KWA SHULE YAKE
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You can only access classes in your own school"
            )

# ================================
# Pydantic Schemas
# ================================

class ClassCreate(BaseModel):
    name: str
    school_id: int

class ClassResponse(BaseModel):
    id: int
    name: str
    school_id: int
    
    class Config:
        from_attributes = True

# ================================
# API Endpoints - PRIMARY ONLY
# ================================

router = APIRouter(prefix="/primary/classes", tags=["Primary Classes"])

# ============================================================
# GET ALL CLASSES - PRIMARY ONLY
# ============================================================
@router.get("", response_model=List[ClassResponse])
def get_primary_classes(
    school_id: Optional[int] = Query(None, description="Filter by school - primary only"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all classes for PRIMARY school only"""
    
    # 🔥 DETERMINE SCHOOL ID
    target_school_id = school_id
    if not target_school_id:
        if hasattr(current_user, 'school_id') and current_user.school_id:
            target_school_id = current_user.school_id
        else:
            raise HTTPException(status_code=400, detail="School ID required")
    
    # 🔥 VERIFY PRIMARY SCHOOL ACCESS
    verify_primary_school_access(target_school_id, db, current_user)
    
    # 🔥 GET CLASSES
    classes = db.query(SchoolClass).filter(
        SchoolClass.school_id == target_school_id
    ).order_by(SchoolClass.name).all()
    
    return classes


# ============================================================
# GET SINGLE CLASS - PRIMARY ONLY
# ============================================================
@router.get("/{class_id}", response_model=ClassResponse)
def get_primary_class(
    class_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single PRIMARY class by ID"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥 VERIFY PRIMARY SCHOOL ACCESS
    verify_primary_school_access(class_obj.school_id, db, current_user)
    
    return class_obj


# ============================================================
# CREATE CLASS - PRIMARY ADMIN ONLY
# ============================================================
@router.post("", response_model=ClassResponse)
def create_primary_class(
    class_data: ClassCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new PRIMARY class - only for primary admins"""
    
    # 🔥 Check permissions - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    # 🔥 VERIFY PRIMARY SCHOOL ACCESS
    verify_primary_school_access(class_data.school_id, db, current_user)
    
    # 🔥 Check if class with same name exists in the same school
    existing = db.query(SchoolClass).filter(
        SchoolClass.name == class_data.name,
        SchoolClass.school_id == class_data.school_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Class with name '{class_data.name}' already exists in this school"
        )
    
    new_class = SchoolClass(
        name=class_data.name,
        school_id=class_data.school_id
    )
    
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


# ============================================================
# UPDATE CLASS - PRIMARY ADMIN ONLY
# ============================================================
@router.put("/{class_id}")
def update_primary_class(
    class_id: int, 
    class_data: ClassCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a PRIMARY class - only for primary admins"""
    
    # 🔥 Check permissions - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥 VERIFY PRIMARY SCHOOL ACCESS
    verify_primary_school_access(class_obj.school_id, db, current_user)
    verify_primary_school_access(class_data.school_id, db, current_user)
    
    # 🔥 Check if another class with same name exists
    existing = db.query(SchoolClass).filter(
        SchoolClass.name == class_data.name,
        SchoolClass.school_id == class_data.school_id,
        SchoolClass.id != class_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Class with name '{class_data.name}' already exists in this school"
        )
    
    class_obj.name = class_data.name
    class_obj.school_id = class_data.school_id
    
    db.commit()
    db.refresh(class_obj)
    return {"message": "Class updated successfully", "class": class_obj}


# ============================================================
# DELETE CLASS - PRIMARY ADMIN ONLY
# ============================================================
@router.delete("/{class_id}")
def delete_primary_class(
    class_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY class - only for primary admins"""
    
    # 🔥 Check permissions - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥 VERIFY PRIMARY SCHOOL ACCESS
    verify_primary_school_access(class_obj.school_id, db, current_user)
    
    db.delete(class_obj)
    db.commit()
    return {"message": "Class deleted successfully"}