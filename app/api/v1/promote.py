from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel

router = APIRouter()

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
# HELPER FUNCTION - Normalize role (case-insensitive)
# ============================================================
def normalize_role(role):
    if role is None:
        return None
    if hasattr(role, 'value'):
        role_str = role.value
    else:
        role_str = str(role)
    role_upper = role_str.upper()
    
    if role_upper == "HEADMASTER":
        return "Headmaster"
    elif role_upper == "HEADMISTRESS":
        return "Headmistress"
    elif role_upper == "SECOND MASTER":
        return "Second Master"
    elif role_upper == "SECOND MISTRESS":
        return "Second Mistress"
    elif role_upper == "ACADEMIC":
        return "Academic"
    return role_str

# ============================================================
# ENDPOINT 1: Get classes with streams
# ============================================================
@router.get("/classes-with-streams")
def get_classes_with_streams(
    school_id: int = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all classes with their streams for promotion dropdown"""
    
    try:
        # Check permissions (case-insensitive)
        user_role_raw = getattr(current_user, 'role', None)
        user_role = normalize_role(user_role_raw)
        
        allowed_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
        
        if not isinstance(current_user, SuperAdmin) and user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Not authorized. Your role: {user_role}")
        
        # Check if school exists
        from app.models.school import School
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail=f"School with id {school_id} not found")
        
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
# ENDPOINT 2: Promote students
# ============================================================
@router.post("/promote", response_model=PromoteResponse)
def promote_students(
    request: PromoteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Promote students to next class - only for academic/headmaster"""
    
    try:
        # Check permissions (case-insensitive)
        user_role_raw = getattr(current_user, 'role', None)
        user_role = normalize_role(user_role_raw)
        
        allowed_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
        
        if not isinstance(current_user, SuperAdmin) and user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Not authorized. Your role: {user_role}")
        
        # Check if target class exists
        to_class = db.query(SchoolClass).filter(SchoolClass.id == request.to_class_id).first()
        if not to_class:
            raise HTTPException(status_code=404, detail=f"Target class with id {request.to_class_id} not found")
        
        # Check if target stream exists (if provided)
        if request.to_stream_id:
            to_stream = db.query(Stream).filter(Stream.id == request.to_stream_id).first()
            if not to_stream:
                raise HTTPException(status_code=404, detail=f"Target stream with id {request.to_stream_id} not found")
        
        promoted_count = 0
        failed_ids = []
        
        for student_id in request.student_ids:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
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
            message=f"Successfully promoted {promoted_count} students to {to_class.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in promote_students: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")