from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.school import School
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel

router = APIRouter(prefix="/primary/promote", tags=["Primary Promote"])

class PromoteRequest(BaseModel):
    student_ids: List[int]
    from_class_id: int
    to_class_id: int
    to_stream_id: Optional[int] = None

class PromoteResponse(BaseModel):
    success: bool
    promoted_count: int
    failed_ids: List[int]
    message: str

# ============================================================
# 🔥 HELPER FUNCTION - PRIMARY ROLES
# ============================================================
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

# ============================================================
# ENDPOINT 1: Get classes with streams - PRIMARY
# ============================================================
@router.get("/classes-with-streams")
def get_primary_classes_with_streams(
    school_id: int = Query(..., description="Kitambulisho cha shule"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all PRIMARY classes with their streams for promotion dropdown"""
    
    try:
        # 🔥 Check permissions - PRIMARY ONLY
        user_role = get_role_string(getattr(current_user, 'role', None))
        
        if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role):
            raise HTTPException(
                status_code=403, 
                detail=f"Huna ruhusa. Jukumu lako: {user_role}. Inaruhusiwa: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
            )
        
        # Check if school exists
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail=f"Shule yenye kitambulisho {school_id} haijapatikana")
        
        # 🔥 Verify it's a primary school
        if school.school_level != "primary":
            raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
        
        # Get classes ordered by name
        classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).order_by(SchoolClass.name).all()
        streams = db.query(Stream).filter(Stream.school_id == school_id).all()
        
        result = []
        for cls in classes:
            class_streams = [s for s in streams if s.class_id == cls.id]
            result.append({
                "id": cls.id,
                "name": cls.name,
                "streams": [{"id": s.id, "name": s.name} for s in class_streams]
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in classes-with-streams: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ============================================================
# ENDPOINT 2: Promote students - PRIMARY
# ============================================================
@router.post("/promote", response_model=PromoteResponse)
def promote_primary_students(
    request: PromoteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Promote PRIMARY students to next class"""
    
    try:
        # 🔥 Check permissions - PRIMARY ONLY
        user_role = get_role_string(getattr(current_user, 'role', None))
        
        if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role):
            raise HTTPException(
                status_code=403, 
                detail=f"Huna ruhusa. Jukumu lako: {user_role}. Inaruhusiwa: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
            )
        
        # 🔥 Check if target class exists and is primary
        to_class = db.query(SchoolClass).filter(SchoolClass.id == request.to_class_id).first()
        if not to_class:
            raise HTTPException(status_code=404, detail=f"Darasa lengwa lenye kitambulisho {request.to_class_id} halijapatikana")
        
        # Verify target class is in a primary school
        school = db.query(School).filter(School.id == to_class.school_id).first()
        if school and school.school_level != "primary":
            raise HTTPException(status_code=400, detail="Darasa lengwa si la shule ya msingi")
        
        # 🔥 Check if target stream exists (if provided)
        if request.to_stream_id:
            to_stream = db.query(Stream).filter(Stream.id == request.to_stream_id).first()
            if not to_stream:
                raise HTTPException(status_code=404, detail=f"Mkondo lengwa wenye kitambulisho {request.to_stream_id} haujapatikana")
        
        promoted_count = 0
        failed_ids = []
        
        for student_id in request.student_ids:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                failed_ids.append(student_id)
                continue
            
            # 🔥 Verify student is in a primary school
            student_school = db.query(School).filter(School.id == student.school_id).first()
            if student_school and student_school.school_level != "primary":
                failed_ids.append(student_id)
                continue
            
            # Update student's class and stream
            student.class_id = request.to_class_id
            if request.to_stream_id:
                student.stream_id = request.to_stream_id
            
            promoted_count += 1
        
        db.commit()
        
        return PromoteResponse(
            success=True,
            promoted_count=promoted_count,
            failed_ids=failed_ids,
            message=f"Wanafunzi {promoted_count} wamepandishwa kikamilifu kwenda {to_class.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in promote_primary_students: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")