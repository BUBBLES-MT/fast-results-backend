# app/api/v1/primary/academic.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.teacher_subject import TeacherSubject
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from app.models.school import School
from pydantic import BaseModel

router = APIRouter(prefix="/primary/academic", tags=["Primary Academic"])

class UnassignedSlotResponse(BaseModel):
    subject_id: int
    subject_name: str
    class_id: int
    class_name: str
    stream_id: Optional[int]
    stream_name: Optional[str]

@router.get("/unassigned-slots", response_model=List[UnassignedSlotResponse])
def get_primary_unassigned_slots(
    school_id: int = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get subjects, classes, streams without teacher assignment - PRIMARY ONLY
    """
    
    # 🔥 PRIMARY ROLES - Kiswahili!
    allowed_roles = ['Mwalimu Mkuu', 'Mwalimu Mkuu Msaidizi', 'Mtaaluma']
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    
    # Superadmin can access everything
    if not isinstance(current_user, SuperAdmin):
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Huna ruhusa. Jukumu lako: {user_role}. Inaruhusiwa: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma"
            )
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="Shule haijapatikana")
    
    if school.school_level != "primary":
        raise HTTPException(
            status_code=400, 
            detail="Hii sio shule ya msingi. Tafadhali tumia endpoint ya secondary."
        )
    
    # Get all subjects, classes, streams for the school
    subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
    classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).all()
    streams = db.query(Stream).filter(Stream.school_id == school_id).all()
    
    # Get all existing assignments
    assignments = db.query(TeacherSubject).join(Teacher).filter(
        Teacher.school_id == school_id
    ).all()
    
    # Create lookup for existing assignments
    assigned_lookup = {}
    for a in assignments:
        key = (a.subject_id, a.class_id, a.stream_id)
        assigned_lookup[key] = True
    
    # Find unassigned slots
    unassigned = []
    for subject in subjects:
        for cls in classes:
            # Get streams for this class
            class_streams = [s for s in streams if s.class_id == cls.id]
            if not class_streams:
                class_streams = [None]
            
            for stream in class_streams:
                stream_id = stream.id if stream else None
                stream_name = stream.name if stream else None
                
                key = (subject.id, cls.id, stream_id)
                if key not in assigned_lookup:
                    unassigned.append({
                        "subject_id": subject.id,
                        "subject_name": subject.name,
                        "class_id": cls.id,
                        "class_name": cls.name,
                        "stream_id": stream_id,
                        "stream_name": stream_name
                    })
    
    return unassigned