from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.mark import Mark
from app.models.student import Student
from app.models.school_class import SchoolClass
from app.models.superadmin import SuperAdmin
from app.models.school import School
from app.models.teacher_subject import TeacherSubject
from app.models.teacher import Teacher
from pydantic import BaseModel

router = APIRouter(prefix="/primary/reports", tags=["Primary Reports"])

class TopStudentResponse(BaseModel):
    position: int
    student_id: int
    name: str
    roll_number: Optional[str]
    average: float
    total: float
    grade: str
    subjects_count: int

class TopStudentsResponse(BaseModel):
    class_name: str
    exam_type: str
    total_students: int
    top_students: List[TopStudentResponse]

# ============================================================
# 🔥 PRIMARY GRADING (0-50 SCALE)
# ============================================================
def calculate_primary_grade(score: float) -> str:
    """Calculate grade for PRIMARY school (0-50 scale)"""
    if score >= 41:
        return "A"
    elif score >= 31:
        return "B"
    elif score >= 21:
        return "C"
    elif score >= 11:
        return "D"
    else:
        return "E"

def calculate_primary_average(marks: List[float]) -> float:
    """Calculate average for PRIMARY (masomo yote, sio top 7 tu)"""
    if not marks:
        return 0
    return round(sum(marks) / len(marks), 2)

# ============================================================
# HELPER FUNCTIONS - PRIMARY ROLES (IMEBORESHA!)
# ============================================================
def get_role_string(role):
    """Convert role to string"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

# 🔥🔥🔥 BADILISHA HAPA - RUHUSU MWALIMU! 🔥🔥🔥
def has_primary_access(user_role: str) -> bool:
    """Check if role has PRIMARY access (admin OR teacher)"""
    allowed_roles = [
        "Mwalimu Mkuu",
        "Mwalimu Mkuu Msaidizi",
        "Mtaaluma",
        "Mwalimu",      # 🔥 ONGEZA MWALIMU!
        "Teacher"       # 🔥 PIA KINGELEZA!
    ]
    return user_role in allowed_roles

def is_primary_teacher(user_role: str) -> bool:
    """Check if role is a PRIMARY teacher"""
    return user_role in ["Mwalimu", "Teacher"]

# ============================================================
# 🔥🔥🔥 ENDPOINT: GET TOP STUDENTS - PRIMARY (IMEBORESHA!) 🔥🔥🔥
# ============================================================
@router.get("/class/{class_id}/top-students", response_model=TopStudentsResponse)
def get_primary_top_students(
    class_id: int,
    exam_type: str = Query(..., description="Aina ya mtihani"),
    limit: Optional[int] = Query(10, description="Idadi ya wanafunzi bora"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 GET TOP STUDENTS - PRIMARY SCHOOL
    RUHUSU: Mwalimu, Mtaaluma, Mwalimu Mkuu, Mwalimu Mkuu Msaidizi
    """
    
    # ============================================================
    # 🔥 PERMISSION CHECK - RUHUSU MWALIMU!
    # ============================================================
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    # ✅ RUHUSU ROLES ZOTE
    if not has_primary_access(user_role) and not isinstance(current_user, SuperAdmin):
        raise HTTPException(
            status_code=403,
            detail=f"Huna ruhusa. Jukumu lako: {user_role}. Inaruhusiwa: Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Mtaaluma, Mwalimu"
        )
    
    # ============================================================
    # 🔥 IKIWA MWALIMU, ANGAZA KAMA ANAFUNDISHA DARASA HILI
    # ============================================================
    if is_primary_teacher(user_role):
        # Angalia kama mwalimu amepangiwa darasa hili
        assignment = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == current_user.id,
            TeacherSubject.class_id == class_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=403,
                detail="Huna ruhusa ya kuona wanafunzi wa darasa hili. Huwezi kufundisha darasa hili."
            )
    
    # ============================================================
    # 🔥 PATA DARASA
    # ============================================================
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Darasa halijapatikana")
    
    # Hakikisha ni shule ya msingi
    school = db.query(School).filter(School.id == school_class.school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Darasa hili si la shule ya msingi")
    
    # ============================================================
    # 🔥 PATA WANAFUNZI
    # ============================================================
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        return TopStudentsResponse(
            class_name=school_class.name,
            exam_type=exam_type,
            total_students=0,
            top_students=[]
        )
    
    student_results = []
    for student in students:
        # Pata alama za mwanafunzi
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type == exam_type
        ).all()
        
        if not marks:
            continue
        
        # PRIMARY: Tumia masomo YOTE (sio top 7 tu)
        scores = [m.score for m in marks]
        total = sum(scores)
        avg = calculate_primary_average(scores)
        grade = calculate_primary_grade(avg)
        
        student_results.append({
            "student_id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "total": total,
            "average": avg,
            "grade": grade,
            "subjects_count": len(scores)
        })
    
    # Pangilia kwa wastani
    student_results.sort(key=lambda x: x["average"], reverse=True)
    
    # Weka limit
    if limit and limit > 0:
        student_results = student_results[:limit]
    
    # Weka nafasi
    for idx, result in enumerate(student_results, 1):
        result["position"] = idx
    
    return TopStudentsResponse(
        class_name=school_class.name,
        exam_type=exam_type,
        total_students=len(students),
        top_students=student_results
    )