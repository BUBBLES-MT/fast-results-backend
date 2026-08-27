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

# ============================================================
# 🔥 GET CLASSES - ILIYOBORESHA KWA AUTHORIZATION!
# ============================================================

@router.get("/classes", response_model=List[ClassResponse])
def get_all_classes(
    school_id: Optional[int] = Query(None, description="Filter by school"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # 🔥 ONGEZA HII!
):
    """
    Get all classes with optional filter by school.
    🔥 SASA INACHUJA KWA SCHOOL ID YA MTUMIAJI!
    """
    
    # 🔥 PATA SCHOOL ID KUTOKA MTUMIAJI
    user_school_id = getattr(current_user, 'school_id', None)
    
    # 🔥 KAMA HAKUNA SCHOOL_ID KWENYE USER, RUDISHA ERROR
    if not user_school_id:
        raise HTTPException(
            status_code=400, 
            detail="School ID not found for current user"
        )
    
    # 🔥 BUILD QUERY
    query = db.query(SchoolClass)
    
    # 🔥 KAMA school_id IMEINGIZWA KWA PARAMETER, TUMIA HIYO
    # LAKINI HAKIKISHA INAFANANA NA school_id YA MTUMIAJI
    target_school_id = school_id if school_id else user_school_id
    
    # 🔥 CHUJA KWA SCHOOL ID YA MTUMIAJI PEKEE!
    query = query.filter(SchoolClass.school_id == target_school_id)
    
    # 🔥 ORDER BY JINA LA DARASA
    classes = query.order_by(SchoolClass.name).all()
    
    return classes


# ============================================================
# 🔥 GET SINGLE CLASS
# ============================================================

@router.get("/classes/{class_id}", response_model=ClassResponse)
def get_class(
    class_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # 🔥 ONGEZA HII!
):
    """Get a single class by ID - SASA INAHITAJI AUTHORIZATION!"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥 HAKIKISHA DARASA LIKO KWENYE SHULE YA MTUMIAJI
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and class_obj.school_id != user_school_id:
        raise HTTPException(
            status_code=403, 
            detail="You don't have access to this class"
        )
    
    return class_obj


# ============================================================
# 🔥 CREATE CLASS - INACHUJA KWA SHULE YA MTUMIAJI
# ============================================================

@router.post("/classes", response_model=ClassResponse)
def create_class(
    class_data: ClassCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # 🔥 ONGEZA HII!
):
    """Create a new class - SASA INAHITAJI AUTHORIZATION!"""
    
    # 🔥 HAKIKISHA MTUMIAJI ANA RUHUSA YA KUUNDA DARASA
    user_role = getattr(current_user, 'role', None)
    if user_role not in ["SuperAdmin", "Headmaster", "Headmistress", "Mwalimu Mkuu", "Mtaaluma"]:
        # 🔥 ANGALIA KAMA NI SUPERADMIN
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to create classes"
            )
    
    # 🔥 HAKIKISHA SHULE IPO
    school = db.query(School).filter(School.id == class_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # 🔥 HAKIKISHA MTUMIAJI ANA SHULE HII (ISIPOKUWA SUPERADMIN)
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and user_school_id != class_data.school_id:
        # KAMA SI SUPERADMIN, RUHUSU TU KWA SHULE YAKE
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You can only create classes for your school"
            )
    
    # 🔥 ANGALIA KAMA DARASA TAYARI LIPO
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
# 🔥 UPDATE CLASS - INAHITAJI AUTHORIZATION
# ============================================================

@router.put("/classes/{class_id}")
def update_class(
    class_id: int, 
    class_data: ClassCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # 🔥 ONGEZA HII!
):
    """Update a class - SASA INAHITAJI AUTHORIZATION!"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥 HAKIKISHA MTUMIAJI ANAWEZA KUBADILISHA DARASA HILI
    user_role = getattr(current_user, 'role', None)
    user_school_id = getattr(current_user, 'school_id', None)
    
    # 🔥 ANGALIA KAMA DARASA LIKO KWENYE SHULE YA MTUMIAJI
    if user_school_id and class_obj.school_id != user_school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this class"
            )
    
    # 🔥 HAKIKISHA MTUMIAJI ANA RUHUSA
    if user_role not in ["SuperAdmin", "Headmaster", "Headmistress", "Mwalimu Mkuu", "Mtaaluma"]:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to update classes"
            )
    
    # 🔥 ANGALIA KAMA SCHOOL IPO
    school = db.query(School).filter(School.id == class_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    class_obj.name = class_data.name
    class_obj.school_id = class_data.school_id
    
    db.commit()
    db.refresh(class_obj)
    return {"message": "Class updated successfully", "class": class_obj}


# ============================================================
# 🔥 DELETE CLASS - INAHITAJI AUTHORIZATION
# ============================================================

@router.delete("/classes/{class_id}")
def delete_class(
    class_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # 🔥 ONGEZA HII!
):
    """Delete a class - SASA INAHITAJI AUTHORIZATION!"""
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥 HAKIKISHA MTUMIAJI ANAWEZA KUFUTA DARASA HILI
    user_role = getattr(current_user, 'role', None)
    user_school_id = getattr(current_user, 'school_id', None)
    
    # 🔥 ANGALIA KAMA DARASA LIKO KWENYE SHULE YA MTUMIAJI
    if user_school_id and class_obj.school_id != user_school_id:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this class"
            )
    
    # 🔥 HAKIKISHA MTUMIAJI ANA RUHUSA
    if user_role not in ["SuperAdmin", "Headmaster", "Headmistress", "Mwalimu Mkuu", "Mtaaluma"]:
        from app.models.superadmin import SuperAdmin
        if not isinstance(current_user, SuperAdmin):
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to delete classes"
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
    current_user = Depends(get_current_user)  # 🔥 ONGEZA HII!
):
    """Get all classes for a specific school"""
    
    # 🔥 HAKIKISHA SHULE IPO
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # 🔥 HAKIKISHA MTUMIAJI ANA SHULE HII (ISIPOKUWA SUPERADMIN)
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