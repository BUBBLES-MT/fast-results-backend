from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.teacher_subject import TeacherSubject
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/unassigned-slots")
def get_unassigned_slots(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get subjects, classes, streams without teacher assignment"""
    
    try:
        # ============================================================
        # 🔥 PERMISSION CHECK - Case-insensitive
        # ============================================================
        user_role = getattr(current_user, 'role', None)
        if hasattr(user_role, 'value'):
            user_role_str = user_role.value
        else:
            user_role_str = str(user_role) if user_role else ""
        
        user_role_upper = user_role_str.upper()
        allowed_roles = ["HEADMASTER", "HEADMISTRESS", "SECOND MASTER", "SECOND MISTRESS", "ACADEMIC"]
        
        logger.debug("unassigned_slots user_role=%s", user_role_str)

        # Superadmin anaweza kuona yote
        if not isinstance(current_user, SuperAdmin) and user_role_upper not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Not authorized. Your role: {user_role_str}. Allowed: Headmaster, Headmistress, Second Master, Second Mistress, Academic"
            )

        # ============================================================
        # 🔥 FETCH DATA
        # ============================================================
        
        # Get all subjects, classes, streams for the school
        subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
        classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).all()
        streams = db.query(Stream).filter(Stream.school_id == school_id).all()
        
        logger.debug(
            "unassigned_slots counts subjects=%s classes=%s streams=%s",
            len(subjects),
            len(classes),
            len(streams),
        )

        # Get all existing assignments
        assignments = db.query(TeacherSubject).join(Teacher).filter(
            Teacher.school_id == school_id
        ).all()
        
        assigned_lookup = {(a.subject_id, a.class_id, a.stream_id): True for a in assignments}
        logger.debug("unassigned_slots assignments=%s", len(assignments))

        # ============================================================
        # 🔥 BUILD RESPONSE - WITH CORRECT FIELD NAMES
        # ============================================================
        unassigned = []
        for subject in subjects:
            for cls in classes:
                class_streams = [s for s in streams if s.class_id == cls.id] or [None]
                for stream in class_streams:
                    key = (subject.id, cls.id, stream.id if stream else None)
                    if key not in assigned_lookup:
                        unassigned.append({
                            # 🔥 MUHIMU: Field names matching frontend
                            "subject_id": subject.id,
                            "subject_name": subject.name,      # ✅ Matches frontend
                            "class_id": cls.id,
                            "class_name": cls.name,            # ✅ Matches frontend
                            "stream_id": stream.id if stream else None,
                            "stream_name": stream.name if stream else None  # ✅ Matches frontend
                        })
        
        return unassigned

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_unassigned_slots failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")