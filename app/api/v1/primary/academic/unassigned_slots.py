from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.teacher_subject import TeacherSubject
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
    school_id: Optional[int] = Query(None, description="Kitambulisho cha shule"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get unassigned subjects for primary school"""
    
    user_role = getattr(current_user, 'role', None)
    user_role_str = user_role.value if hasattr(user_role, 'value') else str(user_role)
    allowed_roles = ["Superadmin", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    is_allowed = isinstance(current_user, SuperAdmin) or user_role_str in allowed_roles
    
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Huna ruhusa")
    
    if not school_id:
        if hasattr(current_user, 'school_id') and current_user.school_id:
            school_id = current_user.school_id
        else:
            raise HTTPException(status_code=400, detail="Tafadhali weka kitambulisho cha shule")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="Shule haijapatikana")
    
    if school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
    
    subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
    if not subjects:
        return []
    
    classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).all()
    if not classes:
        return []
    
    streams = db.query(Stream).filter(Stream.school_id == school_id).all()
    assignments = db.query(TeacherSubject).all()
    
    assigned_set = set()
    for assignment in assignments:
        assigned_set.add((assignment.subject_id, assignment.class_id, assignment.stream_id))
    
    unassigned_slots = []
    for subject in subjects:
        for class_obj in classes:
            class_streams = [s for s in streams if s.class_id == class_obj.id]
            if class_streams:
                for stream in class_streams:
                    if (subject.id, class_obj.id, stream.id) not in assigned_set:
                        unassigned_slots.append({
                            "subject_id": subject.id,
                            "subject_name": subject.name,
                            "class_id": class_obj.id,
                            "class_name": class_obj.name,
                            "stream_id": stream.id,
                            "stream_name": stream.name
                        })
            else:
                if (subject.id, class_obj.id, None) not in assigned_set:
                    unassigned_slots.append({
                        "subject_id": subject.id,
                        "subject_name": subject.name,
                        "class_id": class_obj.id,
                        "class_name": class_obj.name,
                        "stream_id": None,
                        "stream_name": None
                    })
    
    return unassigned_slots