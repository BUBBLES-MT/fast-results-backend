from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import logging
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import get_current_user, create_access_token, get_password_hash
from app.core.email import email_service
from app.core.config import settings
from app.models.parent import Parent
from app.models.parent_child import ParentChild
from app.models.student import Student
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.subject import Subject
from app.models.mark import Mark

# ============================================================
# 🔥 LOGGER - IMEONGEZWA!
# ============================================================

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parents", tags=["Parents"])

# ============================================================
# 🔥 PYDANTIC SCHEMAS
# ============================================================

class ParentRegister(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    username: str
    password: str
    confirm_password: str
    school_id: int

class ParentResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    address: Optional[str]
    username: str
    school_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ParentLogin(BaseModel):
    username: str
    password: str

class ChildRegistration(BaseModel):
    student_id: int
    relationship: Optional[str] = "Biological"

class ChildResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_roll_number: str
    class_name: str
    stream_name: Optional[str]
    school_name: Optional[str] = None
    school_id: Optional[int] = None
    relationship: str
    is_active: bool

class ParentChildResponse(BaseModel):
    parent_id: int
    child: ChildResponse

class StudentLookup(BaseModel):
    class_id: int
    stream_id: Optional[int] = None
    roll_number: Optional[str] = None

class StudentLookupResponse(BaseModel):
    id: int
    name: str
    roll_number: str
    class_name: str
    stream_name: Optional[str]

class ParentDashboardResponse(BaseModel):
    parent: ParentResponse
    children: List[ChildResponse]
    total_children: int

# ============================================================
# 🔥 FORGOT PASSWORD SCHEMAS
# ============================================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str


# ============================================================
# 🔥 HELPER FUNCTIONS - GRADING
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


def calculate_secondary_grade(score: float) -> tuple:
    """Calculate grade for SECONDARY school (0-100 scale)"""
    if score is None:
        return "N/A", 0
    if score >= 75:
        return "A", 1
    elif score >= 65:
        return "B", 2
    elif score >= 45:
        return "C", 3
    elif score >= 30:
        return "D", 4
    else:
        return "F", 5


def calculate_division(points_sum: int, subject_count: int) -> str:
    """Calculate division based on points sum and subject count (7 subjects)"""
    if subject_count < 7:
        return "N/A"
    if 7 <= points_sum <= 17:
        return "I"
    elif 18 <= points_sum <= 21:
        return "II"
    elif 22 <= points_sum <= 25:
        return "III"
    elif 26 <= points_sum <= 33:
        return "IV"
    elif 34 <= points_sum <= 35:
        return "O"
    else:
        return "N/A"


def calculate_grade(score: float, school_level: str = "secondary") -> tuple:
    """Calculate grade based on school level"""
    if school_level == "primary":
        return calculate_primary_grade(score), None
    else:
        return calculate_secondary_grade(score)


def calculate_division_from_grade(grade: str) -> str:
    """Convert grade to division"""
    grade_map = {"A": "I", "B": "II", "C": "III", "D": "IV", "F": "O"}
    return grade_map.get(grade, "N/A")


def calculate_best_7_average(scores: List[float]) -> tuple:
    """Calculate average of best 7 subjects for SECONDARY"""
    if not scores:
        return 0, 0, "N/A", "N/A"
    
    top_7 = sorted(scores, reverse=True)[:7]
    avg_best_7 = sum(top_7) / 7
    points_sum = 0
    for score in top_7:
        _, points = calculate_secondary_grade(score)
        points_sum += points
    
    grade, _ = calculate_secondary_grade(avg_best_7)
    division = calculate_division(points_sum, 7)
    
    return round(avg_best_7, 2), points_sum, grade, division


# ============================================================
# 🔥 REMARKS FUNCTIONS - KISWAHILI
# ============================================================

def get_primary_teacher_remarks(grade: str, average: float) -> str:
    if grade == "A":
        return f"Amefanya vizuri sana! Wastani {average:.1f}%. Endelea kusoma kwa bidii."
    elif grade == "B":
        return f"Amefanya vizuri. Wastani {average:.1f}%. Anaweza kufanya vizuri zaidi."
    elif grade == "C":
        return f"Wastani wa kuridhisha. Wastani {average:.1f}%. Anahitaji kuongeza juhudi."
    elif grade == "D":
        return f"Inaridhisha. Wastani {average:.1f}%. Anahitaji msaada zaidi."
    else:
        return f"Haijaridhisha. Wastani {average:.1f}%. Anahitaji msaada wa haraka."


def get_primary_headmaster_remarks(grade: str, average: float) -> str:
    if grade == "A":
        return f"Hongera kwa utendaji bora. Mtoto ana uwezo mkubwa. Wastani {average:.1f}%."
    elif grade == "B":
        return f"Utendaji mzuri. Tunamshauri kuongeza bidii zaidi. Wastani {average:.1f}%."
    elif grade == "C":
        return f"Wastani wa kuridhisha. Tunamshauri kufanya marudio makini. Wastani {average:.1f}%."
    elif grade == "D":
        return f"Haijatosheleza. Tunawashauri wazazi kufuatilia kwa karibu. Wastani {average:.1f}%."
    else:
        return f"Haijaridhisha. Tunatoa wito kwa mzazi kushirikiana na shule. Wastani {average:.1f}%."


def get_secondary_teacher_remarks(division: str, average: float) -> str:
    if division == "I":
        return ("Amefaulu vizuri sana! Ana uwezo mkubwa wa kitaaluma. "
                "Aendelee kuhifadhi na kuboresha utendaji wake.")
    elif division == "II":
        return ("Amefanya vizuri. Ana msingi mzuri wa kitaaluma. "
                "Anahitaji kuongeza juhudi katika masomo anayodhoofika.")
    elif division == "III":
        return ("Wastani wa kuridhisha. Anaweza kufanya vizuri zaidi kwa "
                "kuongeza muda wa kusoma na kufanya marudio ya kutosha.")
    elif division == "IV":
        return ("Ana hitaji msaada zaidi kitaaluma. Anapaswa kufanya kazi "
                "kwa bidii na kuhudhuria masomo ya ziada.")
    else:
        return ("Haijaweza kufikia matarajio. Anahitaji kuwa makini zaidi "
                "na masomo yake.")


def get_secondary_headmaster_remarks(division: str, average: float) -> str:
    if division == "I":
        return ("Hongera kwa utendaji bora. Mtoto ana uwezo wa kuwa kwenye "
                "ngazi za juu kitaaluma. Tunamshauri aendelee kwa kasi hiyo.")
    elif division == "II":
        return ("Utendaji mzuri. Tunamshauri kuongeza bidii zaidi ili kufikia "
                "Daraja la Kwanza katika mitihani ijayo.")
    elif division == "III":
        return ("Wastani wa kuridhisha. Tunamshauri kufanya marudio makini na "
                "kuhudhuria masomo yote kwa umakini.")
    elif division == "IV":
        return ("Haijatosheleza. Tunawashauri wazazi kufuatilia kwa karibu "
                "maendeleo ya mtoto na kushirikiana na shule.")
    else:
        return ("Haijaridhisha. Tunatoa wito kwa mzazi/mlezi kushirikiana na "
                "shule kumsaidia mtoto kuboresha tabia na utendaji wake.")


def get_teacher_remarks(grade: str, average: float, school_level: str) -> str:
    if school_level == "primary":
        return get_primary_teacher_remarks(grade, average)
    else:
        division = calculate_division_from_grade(grade)
        return get_secondary_teacher_remarks(division, average)


def get_headmaster_remarks(grade: str, average: float, school_level: str) -> str:
    if school_level == "primary":
        return get_primary_headmaster_remarks(grade, average)
    else:
        division = calculate_division_from_grade(grade)
        return get_secondary_headmaster_remarks(division, average)


# ============================================================
# 🔥 HELPER FUNCTIONS - POSITION CALCULATIONS
# ============================================================

def calculate_term_subject_position_fast(db, student_id, subject_id, exam_a, exam_b, all_class_student_ids):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return 1
    
    marks = db.query(Mark).filter(
        Mark.subject_id == subject_id,
        Mark.exam_type.in_([exam_a, exam_b]),
        Mark.student_id.in_(all_class_student_ids)
    ).all()
    
    student_marks = {}
    for mark in marks:
        if mark.student_id not in student_marks:
            student_marks[mark.student_id] = []
        student_marks[mark.student_id].append(mark.score)
    
    subject_scores = []
    for s_id in all_class_student_ids:
        if s_id in student_marks and student_marks[s_id]:
            avg_score = sum(student_marks[s_id]) / len(student_marks[s_id])
            subject_scores.append((s_id, avg_score))
    
    subject_scores.sort(key=lambda x: x[1], reverse=True)
    position = 1
    for idx, (s_id, _) in enumerate(subject_scores, 1):
        if s_id == student_id:
            position = idx
            break
    
    return position


def calculate_term_overall_position_fast(db, student_id, exam_a, exam_b, all_class_student_ids, school_level):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return 1
    
    all_marks = db.query(Mark).filter(
        Mark.exam_type.in_([exam_a, exam_b]),
        Mark.student_id.in_(all_class_student_ids)
    ).all()
    
    student_marks = {}
    for mark in all_marks:
        if mark.student_id not in student_marks:
            student_marks[mark.student_id] = []
        student_marks[mark.student_id].append(mark.score)
    
    class_scores = []
    for s_id in all_class_student_ids:
        if s_id in student_marks and student_marks[s_id]:
            scores = student_marks[s_id]
            if school_level == "secondary":
                top_scores = sorted(scores, reverse=True)[:7]
                avg_best_7 = sum(top_scores) / 7
                class_scores.append((s_id, avg_best_7))
            else:
                avg_score = sum(scores) / len(scores)
                class_scores.append((s_id, avg_score))
    
    class_scores.sort(key=lambda x: x[1], reverse=True)
    position = 1
    for idx, (s_id, _) in enumerate(class_scores, 1):
        if s_id == student_id:
            position = idx
            break
    
    return position


def calculate_single_exam_position_fast(db, student_id, subject_id, exam_type, all_class_student_ids):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return 1
    
    marks = db.query(Mark).filter(
        Mark.subject_id == subject_id,
        Mark.exam_type == exam_type,
        Mark.student_id.in_(all_class_student_ids)
    ).all()
    
    student_marks = {}
    for mark in marks:
        if mark.student_id not in student_marks:
            student_marks[mark.student_id] = []
        student_marks[mark.student_id].append(mark.score)
    
    subject_scores = []
    for s_id in all_class_student_ids:
        if s_id in student_marks and student_marks[s_id]:
            avg_score = sum(student_marks[s_id]) / len(student_marks[s_id])
            subject_scores.append((s_id, avg_score))
    
    subject_scores.sort(key=lambda x: x[1], reverse=True)
    position = 1
    for idx, (s_id, _) in enumerate(subject_scores, 1):
        if s_id == student_id:
            position = idx
            break
    
    return position


def calculate_single_exam_overall_position_fast(db, student_id, exam_type, all_class_student_ids, school_level):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return 1
    
    all_marks = db.query(Mark).filter(
        Mark.exam_type == exam_type,
        Mark.student_id.in_(all_class_student_ids)
    ).all()
    
    student_marks = {}
    for mark in all_marks:
        if mark.student_id not in student_marks:
            student_marks[mark.student_id] = []
        student_marks[mark.student_id].append(mark.score)
    
    class_scores = []
    for s_id in all_class_student_ids:
        if s_id in student_marks and student_marks[s_id]:
            scores = student_marks[s_id]
            if school_level == "secondary":
                top_scores = sorted(scores, reverse=True)[:7]
                avg_best_7 = sum(top_scores) / 7
                class_scores.append((s_id, avg_best_7))
            else:
                avg_score = sum(scores) / len(scores)
                class_scores.append((s_id, avg_score))
    
    class_scores.sort(key=lambda x: x[1], reverse=True)
    position = 1
    for idx, (s_id, _) in enumerate(class_scores, 1):
        if s_id == student_id:
            position = idx
            break
    
    return position


# ============================================================
# 🔥 REGISTER PARENT
# ============================================================

@router.post("/register", response_model=ParentResponse)
def register_parent(
    data: ParentRegister,
    db: Session = Depends(get_db)
):
    """Register a new parent account"""
    
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    school = db.query(School).filter(School.id == data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    existing = db.query(Parent).filter(Parent.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    existing_phone = db.query(Parent).filter(Parent.phone == data.phone).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    new_parent = Parent(
        name=data.name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        username=data.username,
        school_id=data.school_id,
        is_active=True
    )
    new_parent.set_password(data.password)
    
    db.add(new_parent)
    db.commit()
    db.refresh(new_parent)
    
    return new_parent


# ============================================================
# 🔥 PARENT LOGIN
# ============================================================

@router.post("/login")
def parent_login(
    data: ParentLogin,
    db: Session = Depends(get_db)
):
    """Login as parent"""
    
    parent = db.query(Parent).filter(Parent.username == data.username).first()
    if not parent:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not parent.check_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not parent.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    access_token = create_access_token(
        data={
            "sub": str(parent.id),
            "user_type": "parent",
            "parent_id": parent.id,
            "school_id": parent.school_id
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "parent_id": parent.id,
        "name": parent.name,
        "username": parent.username,
        "school_id": parent.school_id
    }


# ============================================================
# 🔥 GET PARENT PROFILE
# ============================================================

@router.get("/profile", response_model=ParentResponse)
def get_parent_profile(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current parent profile"""
    
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    parent = db.query(Parent).filter(Parent.id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    return parent


# ============================================================
# 🔥 PUBLIC ENDPOINTS
# ============================================================

@router.get("/public/classes")
def get_public_classes(
    school_id: int = Query(...),
    school_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get classes for a school - PUBLIC"""
    query = db.query(SchoolClass).filter(SchoolClass.school_id == school_id)
    
    if school_level:
        school = db.query(School).filter(School.id == school_id).first()
        if school and school.school_level == school_level:
            classes = query.all()
            return [{"id": c.id, "name": c.name} for c in classes]
        else:
            return []
    
    classes = query.all()
    return [{"id": c.id, "name": c.name} for c in classes]


@router.get("/public/streams")
def get_public_streams(
    class_id: int = Query(...),
    school_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get streams for a class - PUBLIC"""
    query = db.query(Stream).filter(Stream.class_id == class_id)
    
    if school_level:
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if class_obj:
            school = db.query(School).filter(School.id == class_obj.school_id).first()
            if school and school.school_level == school_level:
                streams = query.all()
                return [{"id": s.id, "name": s.name} for s in streams]
            else:
                return []
    
    streams = query.all()
    return [{"id": s.id, "name": s.name} for s in streams]


@router.get("/public/students")
def get_public_students(
    school_id: int = Query(...),
    class_id: int = Query(...),
    stream_id: Optional[int] = Query(None),
    roll_number: Optional[str] = Query(None),
    school_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get students for a class - PUBLIC"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if school_level and school.school_level != school_level:
        return []
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    query = db.query(Student).filter(
        Student.school_id == school_id,
        Student.class_id == class_id
    )
    
    if stream_id:
        query = query.filter(Student.stream_id == stream_id)
    
    if roll_number:
        query = query.filter(Student.roll_number.ilike(f"%{roll_number}%"))
    
    students = query.all()
    result = []
    for s in students:
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == s.class_id).first()
        stream_obj = db.query(Stream).filter(Stream.id == s.stream_id).first()
        result.append({
            "id": s.id,
            "name": s.name,
            "roll_number": s.roll_number or "",
            "class_name": class_obj.name if class_obj else "Unknown",
            "stream_name": stream_obj.name if stream_obj else ""
        })
    
    return result


@router.get("/public/schools")
def get_public_schools(
    school_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all schools - PUBLIC"""
    query = db.query(School).filter(School.is_active == True)
    if school_level:
        query = query.filter(School.school_level == school_level)
    
    schools = query.all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "school_level": s.school_level,
            "school_type": s.school_type
        }
        for s in schools
    ]


# ============================================================
# 🔥 REGISTER CHILDREN
# ============================================================

@router.post("/children", response_model=ChildResponse)
def register_child(
    data: ChildRegistration,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Link a child to a parent"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    parent = db.query(Parent).filter(Parent.id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    existing = db.query(ParentChild).filter(
        ParentChild.parent_id == parent.id,
        ParentChild.student_id == data.student_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Student already linked to this parent")
    
    new_child = ParentChild(
        parent_id=parent.id,
        student_id=data.student_id,
        relationship=data.relationship
    )
    
    db.add(new_child)
    db.commit()
    db.refresh(new_child)
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
    stream_obj = db.query(Stream).filter(Stream.id == student.stream_id).first()
    school_obj = db.query(School).filter(School.id == student.school_id).first()
    
    return {
        "id": new_child.id,
        "student_id": student.id,
        "student_name": student.name,
        "student_roll_number": student.roll_number or "N/A",
        "class_name": class_obj.name if class_obj else "Unknown",
        "stream_name": stream_obj.name if stream_obj else "",
        "school_name": school_obj.name if school_obj else "Unknown",
        "relationship": new_child.relationship,
        "is_active": new_child.is_active
    }


# ============================================================
# 🔥 GET PARENT CHILDREN
# ============================================================

@router.get("/children", response_model=List[ChildResponse])
def get_parent_children(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all children linked to the current parent"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    parent = db.query(Parent).filter(Parent.id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    children = db.query(ParentChild).filter(
        ParentChild.parent_id == parent.id,
        ParentChild.is_active == True
    ).all()
    
    result = []
    for child in children:
        student = db.query(Student).filter(Student.id == child.student_id).first()
        if not student:
            continue
        
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        stream_obj = db.query(Stream).filter(Stream.id == student.stream_id).first()
        school_obj = db.query(School).filter(School.id == student.school_id).first()
        
        result.append({
            "id": child.id,
            "student_id": student.id,
            "student_name": student.name,
            "student_roll_number": student.roll_number or "N/A",
            "class_name": class_obj.name if class_obj else "Unknown",
            "stream_name": stream_obj.name if stream_obj else "",
            "school_name": school_obj.name if school_obj else "Unknown",
            "school_id": student.school_id,
            "relationship": child.relationship,
            "is_active": child.is_active
        })
    
    return result


# ============================================================
# 🔥 DELETE CHILD LINK
# ============================================================

@router.delete("/children/{child_id}")
def remove_child(
    child_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove a child from parent's account"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    child = db.query(ParentChild).filter(
        ParentChild.id == child_id,
        ParentChild.parent_id == current_user.id
    ).first()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child link not found")
    
    db.delete(child)
    db.commit()
    
    return {"message": "Child removed successfully"}


# ============================================================
# 🔥 GET CHILD INFORMATION
# ============================================================

@router.get("/children/{student_id}/info")
def get_child_info(
    student_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get student information for parent"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    child_link = db.query(ParentChild).filter(
        ParentChild.parent_id == current_user.id,
        ParentChild.student_id == student_id,
        ParentChild.is_active == True
    ).first()
    
    if not child_link:
        raise HTTPException(status_code=403, detail="You don't have access to this student")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
    stream_obj = db.query(Stream).filter(Stream.id == student.stream_id).first()
    school = db.query(School).filter(School.id == student.school_id).first()
    
    return {
        "id": student.id,
        "name": student.name,
        "roll_number": student.roll_number,
        "class_name": class_obj.name if class_obj else "Unknown",
        "stream_name": stream_obj.name if stream_obj else "",
        "school_name": school.name if school else "Unknown",
        "school_level": school.school_level if school else "secondary",
        "school_id": student.school_id
    }


# ============================================================
# 🔥 GET CHILD TERM RESULTS
# ============================================================

@router.get("/children/{student_id}/term-results")
def get_child_term_results(
    student_id: int,
    term: str = Query("I", description="Muhula: I or II"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get term results for a child (combined exams)"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    child_link = db.query(ParentChild).filter(
        ParentChild.parent_id == current_user.id,
        ParentChild.student_id == student_id,
        ParentChild.is_active == True
    ).first()
    
    if not child_link:
        raise HTTPException(status_code=403, detail="You don't have access to this student")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    school = db.query(School).filter(School.id == student.school_id).first()
    school_level = school.school_level if school else "secondary"
    
    term_upper = term.strip().upper()
    if term_upper in ("II", "MUHULA II", "2"):
        exam_a = "MIDTERM9"
        exam_b = "ANNUAL"
        term_display = "II"
    else:
        exam_a = "MIDTERM3"
        exam_b = "TERMINAL"
        term_display = "I"
    
    all_class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    all_class_student_ids = [s.id for s in all_class_students]
    total_students = len(all_class_student_ids)
    
    subjects = db.query(Subject).filter(Subject.school_id == student.school_id).all()
    subject_map = {s.id: s.name for s in subjects}
    
    query = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type.in_([exam_a, exam_b])
    )
    if year:
        query = query.filter(Mark.year == year)
    
    marks = query.all()
    
    subject_marks = {}
    for mark in marks:
        if mark.subject_id not in subject_marks:
            subject_marks[mark.subject_id] = {}
        subject_marks[mark.subject_id][mark.exam_type] = mark.score
    
    results = []
    all_scores = []
    
    for sub_id, sub_name in subject_map.items():
        if sub_id in subject_marks:
            a_score = subject_marks[sub_id].get(exam_a)
            b_score = subject_marks[sub_id].get(exam_b)
            
            if a_score is not None or b_score is not None:
                scores = [s for s in [a_score, b_score] if s is not None]
                jumla = sum(scores)
                wastani = round(jumla / len(scores), 2)
                grade, _ = calculate_grade(wastani, school_level)
                subject_position = calculate_term_subject_position_fast(
                    db, student_id, sub_id, exam_a, exam_b, all_class_student_ids
                )
                
                results.append({
                    "subject_id": sub_id,
                    "subject_name": sub_name,
                    "a_score": a_score,
                    "b_score": b_score,
                    "jumla": jumla,
                    "wastani": wastani,
                    "grade": grade,
                    "position": subject_position,
                    "total_students": total_students
                })
                all_scores.append(wastani)
    
    results.sort(key=lambda x: x["subject_name"])
    
    if school_level == "secondary":
        best_7_avg, points_sum, grade, division = calculate_best_7_average(all_scores)
        overall_avg = best_7_avg
    else:
        valid_subjects = len(results)
        if valid_subjects > 0:
            overall_avg = round(sum(all_scores) / valid_subjects, 2)
            grade, points = calculate_grade(overall_avg, school_level)
            points_sum = points
            division = None
        else:
            overall_avg = 0
            grade = "N/A"
            points_sum = None
            division = None
    
    overall_position = calculate_term_overall_position_fast(
        db, student_id, exam_a, exam_b, all_class_student_ids, school_level
    )
    
    teacher_remarks = get_teacher_remarks(grade, overall_avg, school_level)
    headmaster_remarks = get_headmaster_remarks(grade, overall_avg, school_level)
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
    stream_obj = db.query(Stream).filter(Stream.id == student.stream_id).first()
    
    return {
        "term": term_display,
        "year": year or datetime.now().year,
        "exam_a": exam_a,
        "exam_b": exam_b,
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "class_name": class_obj.name if class_obj else "Unknown",
            "stream_name": stream_obj.name if stream_obj else ""
        },
        "results": results,
        "overall": {
            "total_score": round(sum(all_scores), 2) if all_scores else 0,
            "average": overall_avg,
            "grade": grade,
            "points": points_sum,
            "division": division,
            "position": overall_position,
            "total_students": total_students,
            "teacher_remarks": teacher_remarks,
            "headmaster_remarks": headmaster_remarks
        },
        "exam_types": [exam_a, exam_b]
    }


# ============================================================
# 🔥 GET CHILD EXAM RESULTS - INDIVIDUAL
# ============================================================

@router.get("/children/{student_id}/exam-results")
def get_child_exam_results(
    student_id: int,
    exam_type: str = Query(..., description="Exam type: MIDTERM3, MIDTERM9, TERMINAL, ANNUAL"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get results for a specific exam type only"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    child_link = db.query(ParentChild).filter(
        ParentChild.parent_id == current_user.id,
        ParentChild.student_id == student_id,
        ParentChild.is_active == True
    ).first()
    
    if not child_link:
        raise HTTPException(status_code=403, detail="You don't have access to this student")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    school = db.query(School).filter(School.id == student.school_id).first()
    school_level = school.school_level if school else "secondary"
    
    valid_exam_types = ["MIDTERM3", "MIDTERM9", "TERMINAL", "ANNUAL"]
    if exam_type not in valid_exam_types:
        raise HTTPException(status_code=400, detail=f"Invalid exam type. Must be one of: {', '.join(valid_exam_types)}")
    
    all_class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    all_class_student_ids = [s.id for s in all_class_students]
    total_students = len(all_class_student_ids)
    
    subjects = db.query(Subject).filter(Subject.school_id == student.school_id).all()
    subject_map = {s.id: s.name for s in subjects}
    
    query = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type == exam_type
    )
    if year:
        query = query.filter(Mark.year == year)
    
    marks = query.all()
    
    results = []
    all_scores = []
    
    for mark in marks:
        sub_name = subject_map.get(mark.subject_id, "Unknown")
        grade, _ = calculate_grade(mark.score, school_level)
        subject_position = calculate_single_exam_position_fast(
            db, student_id, mark.subject_id, exam_type, all_class_student_ids
        )
        
        results.append({
            "id": mark.id,
            "subject_id": mark.subject_id,
            "subject_name": sub_name,
            "score": mark.score,
            "grade": grade,
            "position": subject_position,
            "total_students": total_students,
            "exam_type": mark.exam_type,
            "year": mark.year
        })
        all_scores.append(mark.score)
    
    results.sort(key=lambda x: x["subject_name"])
    
    if school_level == "secondary":
        best_7_avg, points_sum, grade, division = calculate_best_7_average(all_scores)
        overall_avg = best_7_avg
    else:
        valid_subjects = len(results)
        if valid_subjects > 0:
            overall_avg = round(sum(all_scores) / valid_subjects, 2)
            grade, points = calculate_grade(overall_avg, school_level)
            points_sum = points
            division = None
        else:
            overall_avg = 0
            grade = "N/A"
            points_sum = None
            division = None
    
    overall_position = calculate_single_exam_overall_position_fast(
        db, student_id, exam_type, all_class_student_ids, school_level
    )
    
    teacher_remarks = get_teacher_remarks(grade, overall_avg, school_level)
    headmaster_remarks = get_headmaster_remarks(grade, overall_avg, school_level)
    
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
    stream_obj = db.query(Stream).filter(Stream.id == student.stream_id).first()
    
    return {
        "exam_type": exam_type,
        "year": year or datetime.now().year,
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "class_name": class_obj.name if class_obj else "Unknown",
            "stream_name": stream_obj.name if stream_obj else ""
        },
        "results": results,
        "overall": {
            "total_score": round(sum(all_scores), 2) if all_scores else 0,
            "average": overall_avg,
            "grade": grade,
            "points": points_sum,
            "division": division,
            "position": overall_position,
            "total_students": total_students,
            "teacher_remarks": teacher_remarks,
            "headmaster_remarks": headmaster_remarks
        }
    }


# ============================================================
# 🔥 GET PARENT DASHBOARD
# ============================================================

@router.get("/dashboard", response_model=ParentDashboardResponse)
def get_parent_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get parent dashboard with all children and their performance"""
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    parent = db.query(Parent).filter(Parent.id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    children = db.query(ParentChild).filter(
        ParentChild.parent_id == parent.id,
        ParentChild.is_active == True
    ).all()
    
    children_data = []
    for child in children:
        student = db.query(Student).filter(Student.id == child.student_id).first()
        if not student:
            continue
        
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        stream_obj = db.query(Stream).filter(Stream.id == student.stream_id).first()
        school_obj = db.query(School).filter(School.id == student.school_id).first()
        
        children_data.append({
            "id": child.id,
            "student_id": student.id,
            "student_name": student.name,
            "student_roll_number": student.roll_number or "N/A",
            "class_name": class_obj.name if class_obj else "Unknown",
            "stream_name": stream_obj.name if stream_obj else "",
            "school_name": school_obj.name if school_obj else "Unknown",
            "relationship": child.relationship,
            "is_active": child.is_active
        })
    
    return {
        "parent": parent,
        "children": children_data,
        "total_children": len(children_data)
    }


# ============================================================
# 🔥🔥🔥 PARENT FORGOT PASSWORD 🔥🔥🔥
# ============================================================

@router.post("/forgot-password")
async def parent_forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Tuma kiungo cha kuweka upya nenosiri kwa mzazi
    """
    try:
        parent = db.query(Parent).filter(Parent.email == request.email).first()
        
        if not parent:
            logger.info(f"🔐 Password reset requested for non-existent parent email: {request.email}")
            return {
                "message": "Kama barua pepe yako imesajiliwa, utapokea kiungo cha kuweka upya nenosiri"
            }
        
        if not parent.is_active:
            logger.warning(f"⚠️ Password reset requested for inactive parent: {request.email}")
            return {
                "message": "Kama barua pepe yako imesajiliwa, utapokea kiungo cha kuweka upya nenosiri"
            }
        
        token = secrets.token_urlsafe(32)
        
        parent.reset_token = token
        parent.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        username = parent.name or parent.username or "Mzazi"
        
        reset_link = f"{settings.FRONTEND_URL}/parent/reset-password?token={token}"
        
        email_sent = email_service.send_password_reset_email(
            to_email=parent.email,
            reset_token=token,
            username=username
        )
        
        if email_sent:
            logger.info(f"✅ Password reset email sent to parent: {parent.email}")
            logger.info(f"🔗 Reset link: {reset_link}")
            return {
                "message": "Kiungo cha kuweka upya nenosiri kimetumwa kwa barua pepe yako",
                "email": parent.email
            }
        else:
            logger.error(f"❌ Failed to send password reset email to parent: {parent.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Imeshindwa kutuma barua pepe. Tafadhali jaribu tena."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Parent forgot password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hitilafu imetokea. Tafadhali jaribu tena baadaye."
        )


# ============================================================
# 🔥 PARENT RESET PASSWORD
# ============================================================

@router.post("/reset-password")
async def parent_reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Weka upya nenosiri la mzazi kwa kutumia tokeni
    """
    try:
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manenosiri hayafanani"
            )
        
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenosiri lazima iwe na herufi 6 au zaidi"
            )
        
        parent = db.query(Parent).filter(
            Parent.reset_token == request.token,
            Parent.reset_token_expires > datetime.utcnow()
        ).first()
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kiungo batili au kimeisha muda wake"
            )
        
        parent.password_hash = get_password_hash(request.new_password)
        parent.updated_at = datetime.utcnow()
        
        parent.reset_token = None
        parent.reset_token_expires = None
        
        db.commit()
        
        logger.info(f"✅ Password reset successful for parent: {parent.email}")
        
        return {
            "message": "Nenosiri limewekwa upya kikamilifu. Sasa unaweza kuingia kwa nenosiri lako jipya."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Parent reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hitilafu imetokea wakati wa kuweka upya nenosiri. Tafadhali jaribu tena."
        )


# ============================================================
# 🔥 PARENT VALIDATE RESET TOKEN
# ============================================================

@router.get("/validate-reset-token/{token}")
async def parent_validate_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Thibitisha kama tokeni ya kuweka upya nenosiri bado ni halali
    """
    parent = db.query(Parent).filter(
        Parent.reset_token == token,
        Parent.reset_token_expires > datetime.utcnow()
    ).first()
    
    if parent:
        return {
            "valid": True,
            "user_id": parent.id,
            "message": "Tokeni halali"
        }
    else:
        return {
            "valid": False,
            "message": "Kiungo batili au kimeisha muda wake"
        }