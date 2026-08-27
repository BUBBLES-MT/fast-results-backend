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
# Helper function to get role string (case-insensitive)
# ================================
def get_role_string(role):
    """Convert Enum role to string if needed and normalize to lowercase"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        role_str = role.value
    else:
        role_str = str(role)
    
    # Normalize to lowercase for case-insensitive comparison
    return role_str.lower()

# Helper function to check if user has admin access (case-insensitive)
def has_admin_access(current_user) -> bool:
    """Check if user has admin-level access (Academic, Headmaster, etc.)"""
    # Superadmin always has access
    if isinstance(current_user, SuperAdmin):
        return True
    
    # Get user role and normalize
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    # Admin roles (all lowercase for comparison)
    admin_roles = ['academic', 'headmaster', 'headmistress', 'second master', 'second mistress']
    
    return user_role in admin_roles

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
    
    class Config:
        from_attributes = True

# ================================
# API Endpoints
# ================================

router = APIRouter()

# ============================================================
# GET ALL STREAMS (Public - any authenticated user)
# ============================================================
@router.get("/streams", response_model=List[StreamResponse])
def get_all_streams(
    class_id: Optional[int] = Query(None, description="Filter by class"),
    school_id: Optional[int] = Query(None, description="Filter by school"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all streams with optional filters - Accessible by all authenticated users"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    query = db.query(Stream)
    
    if class_id:
        query = query.filter(Stream.class_id == class_id)
    if school_id:
        query = query.filter(Stream.school_id == school_id)
    
    return query.all()

# ============================================================
# GET SINGLE STREAM (Public - any authenticated user)
# ============================================================
@router.get("/streams/{stream_id}", response_model=StreamResponse)
def get_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single stream by ID"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

# ============================================================
# CREATE STREAM (Admin only - case-insensitive)
# ============================================================
@router.post("/streams", response_model=StreamResponse)
def create_stream(
    stream_data: StreamCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new stream (only for superadmin, headmaster, headmistress, second master, second mistress, academic)"""
    
    # ============================================================
    # 🔥 CASE-INSENSITIVE PERMISSION CHECK
    # ============================================================
    allowed_roles = ['superadmin', 'headmaster', 'headmistress', 'second master', 'second mistress', 'academic']
    
    # Get user role and normalize to lowercase
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    # Superadmin bypass
    if isinstance(current_user, SuperAdmin):
        user_role = "superadmin"
    
    # Check permissions
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: '{user_role}'. Allowed roles: Headmaster, Headmistress, Second Master, Second Mistress, Academic, Superadmin"
        )
    
    # ============================================================
    # 🔥 VALIDATE DATA
    # ============================================================
    
    # Check if class exists
    school_class = db.query(SchoolClass).filter(SchoolClass.id == stream_data.class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail=f"Class with ID {stream_data.class_id} not found")
    
    # Check if school exists
    school = db.query(School).filter(School.id == stream_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail=f"School with ID {stream_data.school_id} not found")
    
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
    
    # ============================================================
    # 🔥 CREATE STREAM
    # ============================================================
    
    new_stream = Stream(
        name=stream_data.name,
        class_id=stream_data.class_id,
        school_id=stream_data.school_id
    )
    
    db.add(new_stream)
    db.commit()
    db.refresh(new_stream)
    
    return new_stream

# ============================================================
# UPDATE STREAM (Admin only - case-insensitive)
# ============================================================
@router.put("/streams/{stream_id}")
def update_stream(
    stream_id: int,
    stream_data: StreamCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a stream"""
    
    # ============================================================
    # 🔥 CASE-INSENSITIVE PERMISSION CHECK
    # ============================================================
    allowed_roles = ['superadmin', 'headmaster', 'headmistress', 'second master', 'second mistress', 'academic']
    
    # Get user role and normalize to lowercase
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    # Superadmin bypass
    if isinstance(current_user, SuperAdmin):
        user_role = "superadmin"
    
    # Check permissions
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: '{user_role}'. Allowed roles: Headmaster, Headmistress, Second Master, Second Mistress, Academic, Superadmin"
        )
    
    # ============================================================
    # 🔥 UPDATE STREAM
    # ============================================================
    
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream with ID {stream_id} not found")
    
    # Check if class exists
    school_class = db.query(SchoolClass).filter(SchoolClass.id == stream_data.class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail=f"Class with ID {stream_data.class_id} not found")
    
    stream.name = stream_data.name
    stream.class_id = stream_data.class_id
    stream.school_id = stream_data.school_id
    
    db.commit()
    db.refresh(stream)
    
    return {"message": "Stream updated successfully", "stream": stream}

# ============================================================
# DELETE STREAM (Admin only - case-insensitive)
# ============================================================
@router.delete("/streams/{stream_id}")
def delete_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a stream"""
    
    # ============================================================
    # 🔥 CASE-INSENSITIVE PERMISSION CHECK
    # ============================================================
    allowed_roles = ['superadmin', 'headmaster', 'headmistress', 'second master', 'second mistress', 'academic']
    
    # Get user role and normalize to lowercase
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    # Superadmin bypass
    if isinstance(current_user, SuperAdmin):
        user_role = "superadmin"
    
    # Check permissions
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Not authorized. Your role: '{user_role}'. Allowed roles: Headmaster, Headmistress, Second Master, Second Mistress, Academic, Superadmin"
        )
    
    # ============================================================
    # 🔥 DELETE STREAM
    # ============================================================
    
    stream = db.query(Stream).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream with ID {stream_id} not found")
    
    db.delete(stream)
    db.commit()
    
    return {"message": "Stream deleted successfully"}