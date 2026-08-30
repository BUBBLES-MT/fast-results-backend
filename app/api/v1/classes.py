from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.school_class import SchoolClass
from app.models.school import School
from pydantic import BaseModel

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
# API Endpoints
# ================================

router = APIRouter()

# 🔥🔥🔥 SECONDARY ROLES ONLY - KINGEREZA TU! 🔥🔥🔥
ALLOWED_ROLES_FOR_MANAGEMENT = [
    "SuperAdmin",
    "Headmaster", 
    "Headmistress",
    "HEADMISTRESS",   # 🔥 IMEANDIKWA HIVI KWENYE DB!
    "Second Master",
    "Second Mistress",
    "Academic",
    "ACADEMIC",       # 🔥 IMEANDIKWA HIVI KWENYE DB!
    "Teacher",
    "TEACHER",        # 🔥 IMEANDIKWA HIVI KWENYE DB!
]

# ============================================================
# 🔥 GET CLASSES - SECONDARY ONLY
# ============================================================

@router.get("/classes", response_model=List[ClassResponse])
def get_all_classes(
    school_id: Optional[int] = Query(None, description="Filter by school"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all classes with optional filter by school.
    🔥 SECONDARY SCHOOLS ONLY!
    """
    
    user_school_id = getattr(current_user, 'school_id', None)
    
    if not user_school_id:
        raise HTTPException(
            status_code=400, 
            detail="School ID not found for current user"
        )
    
    query = db.query(SchoolClass)
    target_school_id = school_id if school_id else user_school_id
    query = query.filter(SchoolClass.school_id == target_school_id)
    classes = query.order_by(SchoolClass.name).all()
    
    return classes


# ============================================================
# 🔥 GET SINGLE CLASS - SECONDARY ONLY
# ============================================================

@router.get("/classes/{class_id}", response_model=ClassResponse)
def get_class(
    class_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single class by ID - SECONDARY ONLY"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and class_obj.school_id != user_school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this class"
            )
    
    return class_obj


# ============================================================
# 🔥 CREATE CLASS - SECONDARY ONLY
# ============================================================

@router.post("/classes", response_model=ClassResponse)
def create_class(
    class_data: ClassCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new class - SECONDARY ONLY"""
    
    user_role = getattr(current_user, 'role', None)
    
    # 🔥 ANGALIA KAMA MTUMIAJI ANA RUHUSA (SECONDARY ROLES)
    if user_role not in ALLOWED_ROLES_FOR_MANAGEMENT:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized to create classes. Allowed: {', '.join(ALLOWED_ROLES_FOR_MANAGEMENT)}"
            )
    
    school = db.query(School).filter(School.id == class_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and user_school_id != class_data.school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You can only create classes for your school"
            )
    
    existing = db.query(SchoolClass).filter(
        SchoolClass.name == class_data.name,
        SchoolClass.school_id == class_data.school_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Class with this name already exists in this school"
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
# 🔥 UPDATE CLASS - SECONDARY ONLY
# ============================================================

@router.put("/classes/{class_id}")
def update_class(
    class_id: int, 
    class_data: ClassCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a class - SECONDARY ONLY"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    user_role = getattr(current_user, 'role', None)
    user_school_id = getattr(current_user, 'school_id', None)
    
    if user_school_id and class_obj.school_id != user_school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this class"
            )
    
    # 🔥 HAKIKISHA MTUMIAJI ANA RUHUSA (SECONDARY ROLES)
    if user_role not in ALLOWED_ROLES_FOR_MANAGEMENT:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized to update classes. Allowed: {', '.join(ALLOWED_ROLES_FOR_MANAGEMENT)}"
            )
    
    school = db.query(School).filter(School.id == class_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    class_obj.name = class_data.name
    class_obj.school_id = class_data.school_id
    
    db.commit()
    db.refresh(class_obj)
    return {"message": "Class updated successfully", "class": class_obj}


# ============================================================
# 🔥 DELETE CLASS - SECONDARY ONLY
# ============================================================

@router.delete("/classes/{class_id}")
def delete_class(
    class_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a class - SECONDARY ONLY"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    user_role = getattr(current_user, 'role', None)
    user_school_id = getattr(current_user, 'school_id', None)
    
    if user_school_id and class_obj.school_id != user_school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this class"
            )
    
    # 🔥 HAKIKISHA MTUMIAJI ANA RUHUSA (SECONDARY ROLES)
    if user_role not in ALLOWED_ROLES_FOR_MANAGEMENT:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized to delete classes. Allowed: {', '.join(ALLOWED_ROLES_FOR_MANAGEMENT)}"
            )
    
    db.delete(class_obj)
    db.commit()
    return {"message": "Class deleted successfully"}


# ============================================================
# 🔥 GET SCHOOL CLASSES - SHORTCUT
# ============================================================

@router.get("/schools/{school_id}/classes", response_model=List[ClassResponse])
def get_school_classes(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all classes for a specific school - SECONDARY ONLY"""
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and user_school_id != school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this school"
            )
    
    classes = db.query(SchoolClass).filter(
        SchoolClass.school_id == school_id
    ).order_by(SchoolClass.name).all()
    
    return classes