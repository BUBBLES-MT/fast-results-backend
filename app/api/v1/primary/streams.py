from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.stream import Stream
from app.models.school_class import SchoolClass
from app.models.school import School
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel

# ================================
# Helper functions - PRIMARY ONLY
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
    """Check if school is primary"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        return False
    return school.school_level == "primary"

def get_class_name(class_id: int, db: Session) -> str:
    """Get class name by ID"""
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    return class_obj.name if class_obj else "Haijulikani"

# ================================
# Pydantic Schemas
# ================================

class StreamCreate(BaseModel):
    name: str
    class_id: int
    school_id: int

class StreamResponse(BaseModel):
    id: int
    name: str
    class_id: int
    school_id: int
    class_name: Optional[str] = None  # 🔥 ONGEZA HII!
    
    class Config:
        from_attributes = True

# ================================
# API Endpoints - PRIMARY
# ================================

router = APIRouter(prefix="/primary/streams", tags=["Primary Streams"])

# ============================================================
# GET ALL STREAMS - PRIMARY ONLY
# ============================================================
@router.get("", response_model=List[StreamResponse])
def get_primary_streams(
    class_id: Optional[int] = Query(None, description="Filter by class"),
    school_id: Optional[int] = Query(None, description="Filter by school - primary only"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all streams for PRIMARY school only.
    Returns streams with class_name included.
    """
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Determine school_id
    target_school_id = school_id
    if not target_school_id:
        if hasattr(current_user, 'school_id') and current_user.school_id:
            target_school_id = current_user.school_id
        else:
            raise HTTPException(status_code=400, detail="School ID required")
    
    # 🔥 Check if it's a primary school
    if not is_primary_school(target_school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school. Please use secondary endpoint."
        )
    
    # Get streams
    query = db.query(Stream).filter(Stream.school_id == target_school_id)
    
    if class_id:
        query = query.filter(Stream.class_id == class_id)
    
    streams = query.all()
    
    # 🔥 Add class_name to each stream
    result = []
    for stream in streams:
        class_name = get_class_name(stream.class_id, db)
        result.append({
            "id": stream.id,
            "name": stream.name,
            "class_id": stream.class_id,
            "school_id": stream.school_id,
            "class_name": class_name
        })
    
    return result

# ============================================================
# GET SINGLE STREAM - PRIMARY ONLY
# ============================================================
@router.get("/{stream_id}", response_model=StreamResponse)
def get_primary_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single PRIMARY stream by ID with class_name"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream with ID {stream_id} not found")
    
    # 🔥 Verify it's a primary school stream
    if not is_primary_school(stream.school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school stream"
        )
    
    # 🔥 Add class_name
    class_name = get_class_name(stream.class_id, db)
    
    return {
        "id": stream.id,
        "name": stream.name,
        "class_id": stream.class_id,
        "school_id": stream.school_id,
        "class_name": class_name
    }

# ============================================================
# CREATE STREAM - PRIMARY ADMIN ONLY
# ============================================================
@router.post("", response_model=StreamResponse)
def create_primary_stream(
    stream_data: StreamCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new PRIMARY stream - only for primary admins"""
    
    # 🔥 PERMISSION CHECK - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    # 🔥 VALIDATE DATA - PRIMARY ONLY
    
    # Check if class exists
    school_class = db.query(SchoolClass).filter(SchoolClass.id == stream_data.class_id).first()
    if not school_class:
        raise HTTPException(
            status_code=404, 
            detail=f"Class with ID {stream_data.class_id} not found"
        )
    
    # Check if school exists and is primary
    if not is_primary_school(stream_data.school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="Cannot create stream for non-primary school"
        )
    
    # 🔥 Check if class is in the same school
    if school_class.school_id != stream_data.school_id:
        raise HTTPException(
            status_code=400, 
            detail="Class does not belong to the specified school"
        )
    
    # 🔥 Check if user can create stream in their school
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and stream_data.school_id != user_school_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only create streams in your own school"
        )
    
    # Check if stream with same name exists in this class
    existing = db.query(Stream).filter(
        Stream.name == stream_data.name,
        Stream.class_id == stream_data.class_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Stream '{stream_data.name}' already exists in class '{school_class.name}'"
        )
    
    # 🔥 CREATE STREAM
    new_stream = Stream(
        name=stream_data.name,
        class_id=stream_data.class_id,
        school_id=stream_data.school_id
    )
    
    db.add(new_stream)
    db.commit()
    db.refresh(new_stream)
    
    # 🔥 Return with class_name
    return {
        "id": new_stream.id,
        "name": new_stream.name,
        "class_id": new_stream.class_id,
        "school_id": new_stream.school_id,
        "class_name": school_class.name
    }

# ============================================================
# UPDATE STREAM - PRIMARY ADMIN ONLY
# ============================================================
@router.put("/{stream_id}")
def update_primary_stream(
    stream_id: int,
    stream_data: StreamCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a PRIMARY stream - only for primary admins"""
    
    # 🔥 PERMISSION CHECK - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    # 🔥 UPDATE STREAM - PRIMARY ONLY
    
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream with ID {stream_id} not found")
    
    # Verify it's a primary school stream
    if not is_primary_school(stream.school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school stream"
        )
    
    # Check if class exists
    school_class = db.query(SchoolClass).filter(SchoolClass.id == stream_data.class_id).first()
    if not school_class:
        raise HTTPException(
            status_code=404, 
            detail=f"Class with ID {stream_data.class_id} not found"
        )
    
    # Check if new school is primary
    if not is_primary_school(stream_data.school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="Target school is not primary"
        )
    
    # Check if class belongs to the school
    if school_class.school_id != stream_data.school_id:
        raise HTTPException(
            status_code=400, 
            detail="Class does not belong to the specified school"
        )
    
    # 🔥 Check if user can update stream in their school
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and stream_data.school_id != user_school_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only update streams in your own school"
        )
    
    # Check if another stream with same name exists
    existing = db.query(Stream).filter(
        Stream.name == stream_data.name,
        Stream.class_id == stream_data.class_id,
        Stream.id != stream_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Stream '{stream_data.name}' already exists in class '{school_class.name}'"
        )
    
    # Update stream
    stream.name = stream_data.name
    stream.class_id = stream_data.class_id
    stream.school_id = stream_data.school_id
    
    db.commit()
    db.refresh(stream)
    
    # 🔥 Return with class_name
    return {
        "message": "Stream updated successfully",
        "stream": {
            "id": stream.id,
            "name": stream.name,
            "class_id": stream.class_id,
            "school_id": stream.school_id,
            "class_name": school_class.name
        }
    }

# ============================================================
# DELETE STREAM - PRIMARY ADMIN ONLY
# ============================================================
@router.delete("/{stream_id}")
def delete_primary_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY stream - only for primary admins"""
    
    # 🔥 PERMISSION CHECK - PRIMARY ADMIN ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: {user_role}. Allowed roles: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
        )
    
    # 🔥 DELETE STREAM - PRIMARY ONLY
    
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream with ID {stream_id} not found")
    
    # Verify it's a primary school stream
    if not is_primary_school(stream.school_id, db):
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school stream"
        )
    
    # 🔥 Check if user can delete stream in their school
    user_school_id = getattr(current_user, 'school_id', None)
    if user_school_id and stream.school_id != user_school_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only delete streams in your own school"
        )
    
    db.delete(stream)
    db.commit()
    
    return {"message": "Stream deleted successfully"}