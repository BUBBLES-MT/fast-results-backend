from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.responses import StreamingResponse
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.mark import Mark
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.school_class import SchoolClass
from app.models.school import School
from app.models.superadmin import SuperAdmin
from app.models.teacher_subject import TeacherSubject
from app.models.stream import Stream
from pydantic import BaseModel
from sqlalchemy import extract, or_
import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

# ================================
# 🔥 HELPER FUNCTIONS - PRIMARY GRADING
# ================================

def get_role_string(role):
    """Convert Enum role to string if needed"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

def has_primary_admin_access(user_role: str) -> bool:
    """Check if role has PRIMARY admin access"""
    admin_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    return user_role in admin_roles

def is_primary_teacher(user_role: str) -> bool:
    """Check if role is a PRIMARY teacher"""
    return user_role == "Mwalimu"

def verify_primary_school(school_id: int, db: Session) -> School:
    """Verify school exists and is primary"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    if school.school_level != "primary":
        raise HTTPException(
            status_code=400, 
            detail="This is not a primary school. Please use secondary endpoint."
        )
    return school

# 🔥 PRIMARY GRADING (0-50)
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

def get_primary_grade_color(grade: str) -> str:
    """Get color for PRIMARY grade"""
    colors = {
        "A": "bg-emerald-100 text-emerald-800",
        "B": "bg-blue-100 text-blue-800",
        "C": "bg-yellow-100 text-yellow-800",
        "D": "bg-orange-100 text-orange-800",
        "E": "bg-red-100 text-red-800"
    }
    return colors.get(grade, "bg-gray-100 text-gray-800")

def get_primary_grade_description(grade: str) -> str:
    """Get description for PRIMARY grade"""
    descriptions = {
        "A": "Bora Sana",
        "B": "Nzuri",
        "C": "Wastani",
        "D": "Inaridhisha",
        "E": "Haijaridhisha"
    }
    return descriptions.get(grade, "Haijulikani")

def calculate_primary_average(marks: List[float]) -> float:
    """Calculate average for PRIMARY (masomo yote)"""
    if not marks:
        return 0
    return round(sum(marks) / len(marks), 2)

# 🔥 PRIMARY COMMENT FUNCTION
def get_primary_comment(score):
    """
    🔥 MAONI YA MWALIMU KWA MWANAFUNZI
    Kulingana na alama 0-50 (PRIMARY SCHOOL)
    """
    if score is None:
        return "HAKUNA ALAMA"
    elif score >= 41:
        return "BORA SANA! ENDELEA KUSOMA KWA BIDII."
    elif score >= 31:
        return "VIZURI! UNA UWEZO MKUBWA."
    elif score >= 21:
        return "UMEJITAHIDI. ENDELEA KUBORESHA."
    elif score >= 11:
        return "ONGEZA BIDII. UNAFAA KUSOMA ZAIDI."
    else:
        return "UMEFELI. TAFUTA MSAADA WA HARAKA."

# 🔥 PRIMARY REMARKS - KAMILI!
def get_primary_remarks(grade: str, average: float) -> str:
    """Generate remarks for PRIMARY student"""
    if grade == "A":
        return f"✅ BORA SANA! Mwanafunzi amefanya vizuri sana kwa wastani wa {average:.1f}%. Endelea kusoma kwa bidii na umakini. Hongera sana!"
    elif grade == "B":
        return f"✅ VIZURI! Mwanafunzi amefanya vizuri kwa wastani wa {average:.1f}%. Ana uwezo mkubwa na anaweza kufanya vizuri zaidi. Endelea kujitahidi!"
    elif grade == "C":
        return f"📚 WASTANI WA KURIDHISHA! Mwanafunzi amepata wastani wa {average:.1f}%. Anahitaji kuongeza juhudi na kufanya marudio makini. Tunaamini anaweza!"
    elif grade == "D":
        return f"⚠️ INAHITAJI MABORESHO! Mwanafunzi amepata wastani wa {average:.1f}%. Anahitaji msaada zaidi na ufuatiliaji wa karibu kutoka kwa wazazi na walimu."
    else:
        return f"❌ INAHITAJI USAIDIZI WA HARAKA! Mwanafunzi amepata wastani wa {average:.1f}%. Tunatoa wito kwa wazazi kushirikiana na shule ili kumsaidia kuboresha."


def get_primary_teacher_remarks(grade: str, average: float) -> str:
    """Generate teacher remarks for PRIMARY school - KISWAHILI"""
    if grade == "A":
        return f"✅ BORA SANA! Mwanafunzi amefanya vizuri sana kwa wastani wa {average:.1f}%. Endelea kusoma kwa bidii na umakini. Hongera sana!"
    elif grade == "B":
        return f"✅ VIZURI! Mwanafunzi amefanya vizuri kwa wastani wa {average:.1f}%. Ana uwezo mkubwa na anaweza kufanya vizuri zaidi. Endelea kujitahidi!"
    elif grade == "C":
        return f"📚 WASTANI WA KURIDHISHA! Mwanafunzi amepata wastani wa {average:.1f}%. Anahitaji kuongeza juhudi na kufanya marudio makini. Tunaamini anaweza!"
    elif grade == "D":
        return f"⚠️ INAHITAJI MABORESHO! Mwanafunzi amepata wastani wa {average:.1f}%. Anahitaji msaada zaidi na ufuatiliaji wa karibu kutoka kwa wazazi na walimu."
    else:
        return f"❌ INAHITAJI USAIDIZI WA HARAKA! Mwanafunzi amepata wastani wa {average:.1f}%. Tunatoa wito kwa wazazi kushirikiana na shule ili kumsaidia kuboresha."


def get_primary_headmaster_remarks(grade: str, average: float) -> str:
    """Generate headmaster remarks for PRIMARY school - KISWAHILI"""
    if grade == "A":
        return f"🏆 HONGERA SANA! Mwanafunzi ameonyesha kipaji cha hali ya juu kwa wastani wa {average:.1f}%. Tunajivunia kuwepo kwake shuleni. Mungu ambariki!"
    elif grade == "B":
        return f"🌟 HONGERA! Mwanafunzi ameonyesha uwezo mzuri kwa wastani wa {average:.1f}%. Tunamshauri kuendelea kusoma kwa bidii ili kufikia lengo lake."
    elif grade == "C":
        return f"📖 WASTANI MWEMA! Mwanafunzi amepata wastani wa {average:.1f}%. Tunawashauri wazazi kumhamasisha na kumuangalia kwa karibu ili aboreshe."
    elif grade == "D":
        return f"🔄 TUNASHAURI MABORESHO! Mwanafunzi amepata wastani wa {average:.1f}%. Tunashauri ushirikiano mkubwa kati ya shule na wazazi ili kumsaidia kuboresha."
    else:
        return f"🚨 TUNATOA WITO! Mwanafunzi amepata wastani wa {average:.1f}%. Tunawasihi wazazi kushirikiana kikamilifu na shule ili kumwokoa mtoto wao."


# ================================
# Pydantic Schemas
# ================================

class MarkCreate(BaseModel):
    student_id: int
    subject_id: int
    score: float
    exam_type: str
    teacher_id: Optional[int] = None
    school_id: Optional[int] = None

class MarkResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    student_roll_number: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None
    score: float
    grade: str
    exam_type: str
    teacher_id: int
    teacher_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MarkUpdate(BaseModel):
    score: float
    exam_type: Optional[str] = None

class GradeResponse(BaseModel):
    student_id: int
    student_name: str
    student_roll_number: Optional[str] = None
    subject_id: int
    subject_name: str
    score: float
    grade: str

class StudentResultResponse(BaseModel):
    student_id: int
    student_name: str
    student_roll_number: Optional[str] = None
    exam_type: str
    subjects: List[GradeResponse]
    total_score: float
    average: float
    overall_grade: str
    position: int
    total_students: int
    remarks: str


# ================================
# API Endpoints
# ================================

router = APIRouter(prefix="/primary/marks", tags=["Primary Marks"])

# ============================================================
# 🔥 1. ROUTES ZA STATIC - HAZINA PARAMETER ZA PATH
# ============================================================

@router.get("/my-students")
def get_my_primary_students_marks(
    year: Optional[int] = Query(None, description="Year to filter"),
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get marks for PRIMARY students based on user role"""
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    school_id = getattr(current_user, 'school_id', None)
    
    if not school_id:
        raise HTTPException(status_code=400, detail="School ID required")
    
    verify_primary_school(school_id, db)
    
    def apply_year_filter(query, year):
        if year:
            return query.filter(extract('year', Mark.created_at) == year)
        return query
    
    if isinstance(current_user, SuperAdmin):
        query = db.query(Mark)
        query = apply_year_filter(query, year)
        marks = query.all()
        return {
            "marks": [{
                "id": m.id,
                "student_id": m.student_id,
                "subject_id": m.subject_id,
                "score": m.score,
                "exam_type": m.exam_type,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in marks]
        }
    
    admin_roles = ["Mtaaluma", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi"]
    
    if user_role in admin_roles:
        if school_id:
            query = db.query(
                Mark.id,
                Mark.student_id,
                Mark.subject_id,
                Mark.score,
                Mark.exam_type,
                Mark.teacher_id,
                Mark.created_at,
                Student.name.label("student_name"),
                Student.roll_number.label("roll_number"),
                Student.class_id,
                SchoolClass.name.label("class_name"),
                Student.stream_id,
                Stream.name.label("stream_name"),
                Subject.name.label("subject_name"),
                Teacher.name.label("teacher_name")
            ).join(
                Student, Mark.student_id == Student.id
            ).join(
                Subject, Mark.subject_id == Subject.id
            ).join(
                Teacher, Mark.teacher_id == Teacher.id
            ).join(
                SchoolClass, Student.class_id == SchoolClass.id
            ).join(
                Stream, Student.stream_id == Stream.id
            ).filter(
                Student.school_id == school_id
            )
            
            if teacher_id:
                query = query.filter(Mark.teacher_id == teacher_id)
            
            query = apply_year_filter(query, year)
            result = query.all()
            
            marks = []
            for row in result:
                marks.append({
                    "id": row.id,
                    "student_id": row.student_id,
                    "student_name": row.student_name,
                    "roll_number": row.roll_number or "",
                    "subject_id": row.subject_id,
                    "subject_name": row.subject_name,
                    "class_id": row.class_id,
                    "class_name": row.class_name,
                    "stream_id": row.stream_id,
                    "stream_name": row.stream_name,
                    "exam_type": row.exam_type,
                    "score": row.score,
                    "teacher_id": row.teacher_id,
                    "teacher_name": row.teacher_name,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })
            return {"marks": marks}
    
    if user_role == "Mwalimu" or user_role == "Teacher":
        assignments = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == current_user.id
        ).all()
        
        if not assignments:
            return {"marks": [], "message": "No classes assigned"}
        
        class_stream_conditions = []
        subject_ids = []
        
        for assignment in assignments:
            class_stream_conditions.append(
                (Student.class_id == assignment.class_id) & 
                (Student.stream_id == assignment.stream_id)
            )
            subject_ids.append(assignment.subject_id)
        
        query = db.query(
            Mark.id,
            Mark.student_id,
            Mark.subject_id,
            Mark.score,
            Mark.exam_type,
            Mark.teacher_id,
            Mark.created_at,
            Student.name.label("student_name"),
            Student.roll_number.label("roll_number"),
            Student.class_id,
            SchoolClass.name.label("class_name"),
            Student.stream_id,
            Stream.name.label("stream_name"),
            Subject.name.label("subject_name")
        ).join(
            Student, Mark.student_id == Student.id
        ).join(
            Subject, Mark.subject_id == Subject.id
        ).join(
            SchoolClass, Student.class_id == SchoolClass.id
        ).join(
            Stream, Student.stream_id == Stream.id
        ).filter(
            or_(*class_stream_conditions),
            Mark.subject_id.in_(subject_ids),
            Mark.teacher_id == current_user.id
        )
        
        query = apply_year_filter(query, year)
        result = query.all()
        
        marks = []
        for row in result:
            marks.append({
                "id": row.id,
                "student_id": row.student_id,
                "student_name": row.student_name,
                "roll_number": row.roll_number or "",
                "subject_id": row.subject_id,
                "subject_name": row.subject_name,
                "class_id": row.class_id,
                "class_name": row.class_name,
                "stream_id": row.stream_id,
                "stream_name": row.stream_name,
                "exam_type": row.exam_type,
                "score": row.score,
                "teacher_id": row.teacher_id,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {"marks": marks}
    
    return {"marks": [], "error": "Unauthorized role"}


@router.get("/available-years")
def get_primary_available_years(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get list of years that have PRIMARY marks data"""
    from sqlalchemy import distinct
    
    school_id = getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="School ID required")
    
    verify_primary_school(school_id, db)
    
    years = db.query(distinct(extract('year', Mark.created_at))).join(
        Student, Mark.student_id == Student.id
    ).filter(
        Student.school_id == school_id
    ).order_by(
        extract('year', Mark.created_at).desc()
    ).all()
    
    year_list = [int(y[0]) for y in years if y[0] is not None]
    
    if not year_list:
        from datetime import datetime
        year_list = [datetime.now().year]
    
    return {"years": year_list}


@router.get("/exam-types")
def get_primary_exam_types(
    school_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all available PRIMARY exam types"""
    
    target_school_id = school_id
    if not target_school_id:
        if hasattr(current_user, 'school_id'):
            target_school_id = current_user.school_id
        else:
            raise HTTPException(status_code=400, detail="School ID required")
    
    verify_primary_school(target_school_id, db)
    
    query = db.query(Mark.exam_type).distinct().join(
        Student, Mark.student_id == Student.id
    ).filter(
        Student.school_id == target_school_id
    )
    
    exam_types = [et[0] for et in query.order_by(Mark.exam_type).all()]
    
    if not exam_types:
        exam_types = ["MIDTERM3", "MIDTERM9", "TERMINAL", "ANNUAL"]
    
    return {"exam_types": exam_types}


@router.get("/check")
def check_primary_marks(
    student_id: Optional[int] = Query(None),
    subject_id: int = Query(..., description="Subject ID"),
    exam_type: str = Query(..., description="Exam type"),
    class_id: int = Query(..., description="Class ID"),
    school_id: int = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Check if marks exist for students in a class"""
    
    verify_primary_school(school_id, db)
    
    query = db.query(Mark.student_id).filter(
        Mark.subject_id == subject_id,
        Mark.exam_type == exam_type
    ).join(
        Student, Mark.student_id == Student.id
    ).filter(
        Student.school_id == school_id
    )
    
    if class_id and class_id > 0:
        query = query.filter(Student.class_id == class_id)
    
    if student_id:
        query = query.filter(Mark.student_id == student_id)
    
    marks = query.all()
    
    return [{"student_id": m[0]} for m in marks]


# ============================================================
# 🔥🔥🔥 EXPORT EXCEL - TABLES ZOTE KAMA TEMPLATE!
# ============================================================

@router.get("/class/{class_id}/export-excel")
def export_primary_class_excel(
    class_id: int,
    exam_type: str = Query(..., description="Exam type"),
    region: Optional[str] = Query(None, description="District/Region name"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export Excel with all 5 tables for PRIMARY school"""
    from app.models.school_class import SchoolClass
    from app.models.school import School
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.mark import Mark
    from datetime import datetime
    from io import BytesIO
    import pandas as pd
    from fastapi.responses import StreamingResponse
    
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    verify_primary_school(school_class.school_id, db)
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SHULE YA MSINGI"
    
    final_region = region
    if not final_region and school:
        final_region = getattr(school, 'region', None)
        if not final_region:
            final_region = getattr(school, 'district', None)
    if not final_region:
        final_region = "_________________________"
    
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    subject_order = ["KISWAHILI", "ENGLISH", "HISABATI", "SAYANSI", "H/TANZANIA", "JIOGRAFIA", "S/MICH"]
    
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subject_dict = {s.name: s for s in subjects}
    sorted_subjects = []
    for name in subject_order:
        if name in subject_dict:
            sorted_subjects.append(subject_dict[name])
    for s in subjects:
        if s.name not in subject_order:
            sorted_subjects.append(s)
    
    subject_names = [s.name for s in sorted_subjects]
    num_subjects = len(subject_names)
    
    marks = db.query(Mark).join(Student).filter(
        Student.class_id == class_id,
        Mark.exam_type == exam_type
    ).all()
    
    marks_map = {}
    for m in marks:
        marks_map[(m.student_id, m.subject_id)] = m.score
    
    def calculate_primary_grade(score):
        if score is None or score == "":
            return "ABS"
        elif score >= 41:
            return "A"
        elif score >= 31:
            return "B"
        elif score >= 21:
            return "C"
        elif score >= 11:
            return "D"
        else:
            return "E"
    
    def get_primary_comment(score):
        if score >= 41:
            return "VIZURI SANA"
        elif score >= 31:
            return "VIZURI"
        elif score >= 21:
            return "UMEJITAHIDI"
        elif score >= 11:
            return "ONGEZA BIDII"
        else:
            return "UMEFELI"
    
    results = []
    grade_summary = {
        "A": {"M": 0, "F": 0},
        "B": {"M": 0, "F": 0},
        "C": {"M": 0, "F": 0},
        "D": {"M": 0, "F": 0},
        "E": {"M": 0, "F": 0},
        "ABS": {"M": 0, "F": 0}
    }
    reg_summary = {"M": 0, "F": 0}
    exam_takers = {"M": 0, "F": 0}
    subject_data = {}
    
    for sub in sorted_subjects:
        subject_data[sub.name] = {
            'grades': {
                'A': {'M': 0, 'F': 0},
                'B': {'M': 0, 'F': 0},
                'C': {'M': 0, 'F': 0},
                'D': {'M': 0, 'F': 0},
                'E': {'M': 0, 'F': 0},
                'ABS': {'M': 0, 'F': 0}
            },
            'total_score': 0,
            'count': 0,
            'scores': []
        }
    
    for student in students:
        reg_summary[student.sex] += 1
        student_marks = [m for m in marks if m.student_id == student.id]
        has_exam = len(student_marks) > 0
        
        if has_exam:
            exam_takers[student.sex] += 1
        
        subject_scores = []
        subject_grades = []
        total = 0
        valid_subjects = 0
        
        for sub in sorted_subjects:
            score = marks_map.get((student.id, sub.id))
            
            if score is not None:
                grade = calculate_primary_grade(score)
                subject_scores.append(score)
                subject_grades.append(grade)
                total += score
                valid_subjects += 1
                subject_data[sub.name]['grades'][grade][student.sex] += 1
                subject_data[sub.name]['total_score'] += score
                subject_data[sub.name]['count'] += 1
                subject_data[sub.name]['scores'].append(score)
            else:
                subject_scores.append("")
                subject_grades.append("")
                subject_data[sub.name]['grades']['ABS'][student.sex] += 1
        
        if valid_subjects > 0:
            avg = round(total / valid_subjects, 2)
        else:
            avg = 0
        
        grade = calculate_primary_grade(avg)
        
        if has_exam:
            grade_summary[grade][student.sex] += 1
        else:
            grade_summary["ABS"][student.sex] += 1
        
        results.append({
            "exam_no": student.roll_number or f"P-{student.id:04d}",
            "name": student.name,
            "sex": student.sex,
            "subjects": subject_scores,
            "subject_grades": subject_grades,
            "total": total,
            "average": avg,
            "grade": grade,
            "comment": get_primary_comment(avg)
        })
    
    results.sort(key=lambda x: x["average"], reverse=True)
    for i, r in enumerate(results, 1):
        r["position"] = i
    
    subject_avg_list = []
    for sub_name, data in subject_data.items():
        avg = round(data['total_score'] / data['count'], 2) if data['count'] > 0 else 0
        subject_avg_list.append((sub_name, avg))
    
    subject_avg_list.sort(key=lambda x: x[1], reverse=True)
    subject_position_map = {sub: idx + 1 for idx, (sub, _) in enumerate(subject_avg_list)}
    
    total_pass = sum(grade_summary[g]["M"] + grade_summary[g]["F"] for g in ["A","B","C"])
    total_fail = sum(grade_summary[g]["M"] + grade_summary[g]["F"] for g in ["D","E"])
    total_students = total_pass + total_fail
    
    pass_pct = round((total_pass / total_students) * 100, 2) if total_students > 0 else 0
    fail_pct = round((total_fail / total_students) * 100, 2) if total_students > 0 else 0
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet(f"{school_class.name} Results")
        
        header_format = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", "font_size": 16})
        header_format_big = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", "font_size": 18})
        title_format = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", "font_size": 12, "bg_color": "#DCE6F1"})
        bold_center = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter", "bg_color": "#DCE6F1"})
        data_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9})
        data_format_left = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 9})
        grade_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9, 'bold': True})
        merge_format = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", "bg_color": "#DCE6F1", "border": 1})
        
        SMALL_TABLE_START = 6
        USAJILI_START = 13
        SUBJECT_TABLE_START = 4
        RESULTS_TABLE_START = 3
        INFO_START = 16
        
        exam_date = datetime.now().strftime('%B %Y')
        exam_type_parts = exam_type.lower().split('_')
        exam_type_title = ' '.join(word.capitalize() for word in exam_type_parts)
        
        header_total_cols = 3 + 3 + (num_subjects * 2) + 5
        
        worksheet.merge_range(0, RESULTS_TABLE_START, 0, RESULTS_TABLE_START + header_total_cols - 1,
                             f"HALMASHAURI YA WILAYA YA {final_region.upper()}", header_format_big)
        worksheet.merge_range(1, RESULTS_TABLE_START, 1, RESULTS_TABLE_START + header_total_cols - 1,
                             f"MATOKEO YA MTIHANI WA {exam_type_title} - {exam_date}", header_format)
        worksheet.merge_range(2, RESULTS_TABLE_START, 2, RESULTS_TABLE_START + header_total_cols - 1,
                             f"{school_name.upper()} - {school_class.name.upper()}", header_format)
        
        current_row = 4
        
        div_start = SMALL_TABLE_START
        worksheet.merge_range(current_row, div_start, current_row, div_start + 7, "TATHIMINI YA UFAULU", title_format)
        
        div_headers = ["JINSI", "A", "B", "C", "D", "E", "ABS", "JUMLA"]
        for c, col in enumerate(div_headers):
            worksheet.write(current_row + 1, div_start + c, col, bold_center)
        
        total_m = sum(grade_summary[g]["M"] for g in ["A","B","C","D","E","ABS"])
        total_f = sum(grade_summary[g]["F"] for g in ["A","B","C","D","E","ABS"])
        
        div_data = [
            ["WAV"] + [grade_summary[g]["M"] for g in ["A","B","C","D","E","ABS"]] + [total_m],
            ["WAS"] + [grade_summary[g]["F"] for g in ["A","B","C","D","E","ABS"]] + [total_f],
            ["JUMLA"] + [grade_summary[g]["M"] + grade_summary[g]["F"] for g in ["A","B","C","D","E","ABS"]] + [total_m + total_f]
        ]
        
        for r in range(len(div_data)):
            for c in range(len(div_headers)):
                worksheet.write(current_row + 2 + r, div_start + c, div_data[r][c], bold_center)
        
        current_row += 6
        
        reg_start = USAJILI_START
        worksheet.merge_range(current_row, reg_start, current_row, reg_start + 3, "USAJILI", title_format)
        reg_headers = ["JINSI", "WAV", "WAS", "JML"]
        for c, col in enumerate(reg_headers):
            worksheet.write(current_row + 1, reg_start + c, col, bold_center)
        
        reg_data = [
            ["WALIOSAJIRIWA", reg_summary["M"], reg_summary["F"], reg_summary["M"] + reg_summary["F"]],
            ["WALIOFANYA", exam_takers["M"], exam_takers["F"], exam_takers["M"] + exam_takers["F"]],
            ["WASIOFANYA", reg_summary["M"] - exam_takers["M"], reg_summary["F"] - exam_takers["F"],
             (reg_summary["M"] + reg_summary["F"]) - (exam_takers["M"] + exam_takers["F"])]
        ]
        
        for r in range(len(reg_data)):
            for c in range(len(reg_headers)):
                worksheet.write(current_row + 2 + r, reg_start + c, reg_data[r][c], bold_center)
        
        current_row += 6
        
        sub_start = SUBJECT_TABLE_START
        worksheet.merge_range(current_row, sub_start, current_row, sub_start + 22, "TATHIMINI YA MADARAJA YA KILA SOMO", title_format)
        
        sub_headers_row1 = ["SOMO", "A", "", "", "B", "", "", "C", "", "", "D", "", "", "E", "", "", "ABS", "", "", "WASTANI", "NAFASI", "WALIOFAULU", "%"]
        for c, col in enumerate(sub_headers_row1):
            worksheet.write(current_row + 1, sub_start + c, col, bold_center)
        
        sub_headers_row2 = ["", "WAV", "WAS", "JML", "WAV", "WAS", "JML", "WAV", "WAS", "JML",
                           "WAV", "WAS", "JML", "WAV", "WAS", "JML", "WAV", "WAS", "JML",
                           "WASTANI", "NAFASI", "WALIOFAULU", "%"]
        for c, col in enumerate(sub_headers_row2):
            worksheet.write(current_row + 2, sub_start + c, col, bold_center)
        
        for idx, sub_name in enumerate(subject_names):
            data = subject_data[sub_name]
            grades = data['grades']
            
            total_a = grades['A']['M'] + grades['A']['F']
            total_b = grades['B']['M'] + grades['B']['F']
            total_c = grades['C']['M'] + grades['C']['F']
            total_d = grades['D']['M'] + grades['D']['F']
            total_e = grades['E']['M'] + grades['E']['F']
            total_abs = grades['ABS']['M'] + grades['ABS']['F']
            
            passed = total_a + total_b + total_c
            failed = total_d + total_e
            
            avg = subject_avg_list[idx][1] if idx < len(subject_avg_list) else 0
            position = subject_position_map.get(sub_name, 0)
            pass_pct = round((passed / (passed + failed)) * 100, 2) if (passed + failed) > 0 else 0
            
            row_data = [
                sub_name,
                grades['A']['M'], grades['A']['F'], total_a,
                grades['B']['M'], grades['B']['F'], total_b,
                grades['C']['M'], grades['C']['F'], total_c,
                grades['D']['M'], grades['D']['F'], total_d,
                grades['E']['M'], grades['E']['F'], total_e,
                grades['ABS']['M'], grades['ABS']['F'], total_abs,
                avg, position, passed, pass_pct
            ]
            
            for c, val in enumerate(row_data):
                worksheet.write(current_row + 3 + idx, sub_start + c, val, data_format)
        
        current_row += len(subject_names) + 4
        
        info_row = 2
        avg_scores = [r["average"] for r in results if r["average"] > 0]
        school_avg = round(sum(avg_scores) / len(avg_scores), 2) if avg_scores else 0
        school_grade = calculate_primary_grade(school_avg)
        
        worksheet.write(info_row, INFO_START, "WASTANI WA SHULE:", bold_center)
        worksheet.write(info_row, INFO_START + 1, school_avg, bold_center)
        worksheet.write(info_row, INFO_START + 2, f"DARAJA: {school_grade}", bold_center)
        
        pf_row = info_row + 3
        worksheet.merge_range(pf_row, INFO_START, pf_row, INFO_START + 2, "PASS/FAIL", title_format)
        pf_headers = ["", "PASS", "FAIL"]
        for c, col in enumerate(pf_headers):
            worksheet.write(pf_row + 1, INFO_START + c, col, bold_center)
        
        pf_data = [
            ["JUMLA", total_pass, total_fail],
            ["%", pass_pct, fail_pct]
        ]
        
        for r in range(len(pf_data)):
            for c in range(3):
                worksheet.write(pf_row + 2 + r, INFO_START + c, pf_data[r][c], bold_center)
        
        res_start = RESULTS_TABLE_START
        res_total_cols = 3 + (num_subjects * 2) + 5
        current_row += 2
        
        worksheet.merge_range(current_row, res_start, current_row, res_start + res_total_cols - 1, "MATOKEO YA WANAFUNZI", title_format)
        
        table_headers_row1 = ["", "", ""]
        for sub in subject_names:
            table_headers_row1.append(sub)
            table_headers_row1.append("")
        table_headers_row1 += ["", "", "", "", ""]
        
        table_headers_row2 = ["S/N", "JINA LA MWANAFUNZI", "JINSI"]
        for _ in subject_names:
            table_headers_row2.append("ALAMA")
            table_headers_row2.append("DARAJA")
        table_headers_row2 += ["JUMLA", "WASTANI", "DARAJA", "NAFASI", "MAONI"]
        
        col_idx = res_start
        for c in range(3):
            worksheet.write(current_row + 1, col_idx, table_headers_row1[c], bold_center)
            col_idx += 1
        
        for sub in subject_names:
            worksheet.merge_range(current_row + 1, col_idx, current_row + 1, col_idx + 1, sub, merge_format)
            col_idx += 2
        
        for c in range(3, 3 + 5):
            worksheet.write(current_row + 1, col_idx, table_headers_row1[3 + (num_subjects * 2) + c - 3], bold_center)
            col_idx += 1
        
        for c, col in enumerate(table_headers_row2):
            worksheet.write(current_row + 2, res_start + c, col, bold_center)
        
        for r, s in enumerate(results):
            row_data = [r + 1, s['name'], s['sex']]
            
            for i in range(len(subject_names)):
                score = s['subjects'][i] if i < len(s['subjects']) else ""
                grade = s['subject_grades'][i] if i < len(s['subject_grades']) else ""
                row_data.append(score)
                row_data.append(grade)
            
            row_data.extend([s['total'], s['average'], s['grade'], s['position'], s['comment']])
            
            for c, val in enumerate(row_data):
                if c == 1:
                    worksheet.write(current_row + 3 + r, res_start + c, val, data_format_left)
                else:
                    if c > 2 and ((c - 2) % 2 == 1):
                        worksheet.write(current_row + 3 + r, res_start + c, val, grade_format)
                    else:
                        worksheet.write(current_row + 3 + r, res_start + c, val, data_format)
        
        col_widths = {
            res_start + 0: 6,
            res_start + 1: 30,
            res_start + 2: 6,
        }
        for i in range(num_subjects):
            col_widths[res_start + 3 + (i * 2)] = 10
            col_widths[res_start + 4 + (i * 2)] = 8
        col_widths[res_start + 3 + (num_subjects * 2)] = 10
        col_widths[res_start + 4 + (num_subjects * 2)] = 10
        col_widths[res_start + 5 + (num_subjects * 2)] = 8
        col_widths[res_start + 6 + (num_subjects * 2)] = 8
        col_widths[res_start + 7 + (num_subjects * 2)] = 15
        
        for col, width in col_widths.items():
            worksheet.set_column(col, col, width)
    
    output.seek(0)
    
    filename = f"Matokeo_{school_class.name}_{exam_type}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================
# 🔥 2. ROUTES ZA DYNAMIC - ZINA PARAMETER ZA PATH
# ============================================================

@router.get("/", response_model=List[MarkResponse])
def get_primary_marks(
    student_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    teacher_id: Optional[int] = Query(None),
    exam_type: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None),
    school_id: Optional[int] = Query(None),
    limit: Optional[int] = Query(500, description="Limit results for performance"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all marks for PRIMARY school only"""
    
    target_school_id = school_id
    if not target_school_id:
        if hasattr(current_user, 'school_id'):
            target_school_id = current_user.school_id
        else:
            raise HTTPException(status_code=400, detail="School ID required")
    
    verify_primary_school(target_school_id, db)
    
    query = db.query(
        Mark.id,
        Mark.student_id,
        Mark.subject_id,
        Mark.score,
        Mark.exam_type,
        Mark.teacher_id,
        Mark.created_at,
        Student.name.label("student_name"),
        Student.roll_number.label("student_roll_number"),
        Subject.name.label("subject_name"),
        Teacher.name.label("teacher_name")
    ).join(
        Student, Mark.student_id == Student.id
    ).join(
        Subject, Mark.subject_id == Subject.id
    ).join(
        Teacher, Mark.teacher_id == Teacher.id
    ).filter(
        Student.school_id == target_school_id
    )
    
    if student_id:
        query = query.filter(Mark.student_id == student_id)
    if subject_id:
        query = query.filter(Mark.subject_id == subject_id)
    if teacher_id:
        query = query.filter(Mark.teacher_id == teacher_id)
    if exam_type:
        query = query.filter(Mark.exam_type == exam_type)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    
    query = query.order_by(Mark.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    marks = query.all()
    
    result = []
    for mark in marks:
        grade = calculate_primary_grade(mark.score)
        result.append(MarkResponse(
            id=mark.id,
            student_id=mark.student_id,
            student_name=mark.student_name,
            student_roll_number=mark.student_roll_number,
            subject_id=mark.subject_id,
            subject_name=mark.subject_name,
            score=mark.score,
            grade=grade,
            exam_type=mark.exam_type,
            teacher_id=mark.teacher_id,
            teacher_name=mark.teacher_name,
            created_at=mark.created_at
        ))
    
    return result


@router.post("", response_model=MarkResponse)
def create_primary_mark(
    mark_data: MarkCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new PRIMARY mark (0-50 scale)"""
    
    logger.info(f"=== CREATE PRIMARY MARK ===")
    logger.info(f"Student ID: {mark_data.student_id}")
    logger.info(f"Subject ID: {mark_data.subject_id}")
    logger.info(f"Teacher ID: {mark_data.teacher_id}")
    logger.info(f"Score: {mark_data.score}")
    logger.info(f"Exam Type: {mark_data.exam_type}")
    
    if not isinstance(current_user, Teacher):
        raise HTTPException(
            status_code=403,
            detail="Only teachers can create marks"
        )
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    if user_role != "Mwalimu" and not has_primary_admin_access(user_role):
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized. Your role: {user_role}. Allowed: Mwalimu, Mtaaluma, Mwalimu Mkuu"
        )
    
    school_id = mark_data.school_id or getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="School ID required")
    
    verify_primary_school(school_id, db)
    
    student = db.query(Student).filter(
        Student.id == mark_data.student_id,
        Student.school_id == school_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found in this school")
    
    subject = db.query(Subject).filter(
        Subject.id == mark_data.subject_id,
        Subject.school_id == school_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found in this school")
    
    teacher_id = mark_data.teacher_id if mark_data.teacher_id else current_user.id
    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id,
        Teacher.school_id == school_id
    ).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found in this school")
    
    existing = db.query(Mark).filter(
        Mark.student_id == mark_data.student_id,
        Mark.subject_id == mark_data.subject_id,
        Mark.exam_type == mark_data.exam_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Mark already exists for student '{student.name}' in subject '{subject.name}' for exam '{mark_data.exam_type}'"
        )
    
    if mark_data.score < 0 or mark_data.score > 50:
        raise HTTPException(
            status_code=400,
            detail="Score must be between 0 and 50 for primary school"
        )
    
    new_mark = Mark(
        student_id=mark_data.student_id,
        subject_id=mark_data.subject_id,
        teacher_id=teacher_id,
        score=mark_data.score,
        exam_type=mark_data.exam_type
    )
    
    db.add(new_mark)
    db.commit()
    db.refresh(new_mark)
    
    logger.info(f"✅ Primary mark created successfully with ID: {new_mark.id}")
    
    grade = calculate_primary_grade(mark_data.score)
    
    return MarkResponse(
        id=new_mark.id,
        student_id=new_mark.student_id,
        student_name=student.name,
        student_roll_number=student.roll_number,
        subject_id=new_mark.subject_id,
        subject_name=subject.name,
        score=new_mark.score,
        grade=grade,
        exam_type=new_mark.exam_type,
        teacher_id=new_mark.teacher_id,
        teacher_name=teacher.name,
        created_at=new_mark.created_at
    )


@router.get("/{mark_id}", response_model=MarkResponse)
def get_primary_mark(
    mark_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single PRIMARY mark by ID"""
    mark = db.query(Mark).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")
    
    student = db.query(Student).filter(Student.id == mark.student_id).first()
    if student:
        verify_primary_school(student.school_id, db)
    
    student_obj = db.query(Student).filter(Student.id == mark.student_id).first()
    subject_obj = db.query(Subject).filter(Subject.id == mark.subject_id).first()
    teacher_obj = db.query(Teacher).filter(Teacher.id == mark.teacher_id).first()
    
    grade = calculate_primary_grade(mark.score)
    
    return MarkResponse(
        id=mark.id,
        student_id=mark.student_id,
        student_name=student_obj.name if student_obj else None,
        student_roll_number=student_obj.roll_number if student_obj else None,
        subject_id=mark.subject_id,
        subject_name=subject_obj.name if subject_obj else None,
        score=mark.score,
        grade=grade,
        exam_type=mark.exam_type,
        teacher_id=mark.teacher_id,
        teacher_name=teacher_obj.name if teacher_obj else None,
        created_at=mark.created_at
    )


@router.put("/{mark_id}")
def update_primary_mark(
    mark_id: int,
    mark_data: MarkUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a PRIMARY mark (0-50 scale)"""
    mark = db.query(Mark).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")
    
    student = db.query(Student).filter(Student.id == mark.student_id).first()
    if student:
        verify_primary_school(student.school_id, db)
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if mark.teacher_id != current_user.id:
        if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to edit this mark"
            )
    
    if mark_data.score < 0 or mark_data.score > 50:
        raise HTTPException(
            status_code=400,
            detail="Score must be between 0 and 50 for primary school"
        )
    
    mark.score = mark_data.score
    if mark_data.exam_type:
        mark.exam_type = mark_data.exam_type
    
    db.commit()
    db.refresh(mark)
    
    return {
        "message": "Mark updated successfully",
        "mark_id": mark.id,
        "score": mark.score,
        "grade": calculate_primary_grade(mark.score)
    }


@router.delete("/{mark_id}")
def delete_primary_mark(
    mark_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY mark"""
    mark = db.query(Mark).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")
    
    student = db.query(Student).filter(Student.id == mark.student_id).first()
    if student:
        verify_primary_school(student.school_id, db)
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if mark.teacher_id != current_user.id:
        if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to delete this mark"
            )
    
    db.delete(mark)
    db.commit()
    
    return {"message": "Mark deleted successfully"}


# ============================================================
# 🔥 PARENT REPORTS DATA - CLASS
# ============================================================

@router.get("/class/{class_id}/parent-reports-data")
def get_primary_parent_reports_data(
    class_id: int,
    term: str = Query("I", description="Muhula: I or II"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None),
    opening_date: Optional[str] = Query(None),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Return JSON data for ALL students in a PRIMARY class for PDF generation"""
    
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    verify_primary_school(school_class.school_id, db)
    
    term_upper = term.strip().upper()
    if term_upper in ("II", "MUHULA II", "2"):
        exam_a = "MIDTERM9"
        exam_b = "ANNUAL"
        term_display = "II"
    else:
        exam_a = "MIDTERM3"
        exam_b = "TERMINAL"
        term_display = "I"
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SHULE YA MSINGI"
    
    final_district_name = district_name
    if not final_district_name and school:
        final_district_name = getattr(school, 'district', None)
    if not final_district_name:
        final_district_name = "_________________________"
    
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subjects_list = [(s.id, s.name) for s in subjects]
    
    marks = db.query(Mark).join(Student).filter(
        Student.class_id == class_id,
        Mark.exam_type.in_([exam_a, exam_b])
    ).all()
    
    marks_map = {}
    for m in marks:
        marks_map[(m.student_id, m.subject_id, m.exam_type)] = m.score
    
    student_subject_avg = {}
    for student in students:
        student_subject_avg[student.id] = {}
        for sub_id, sub_name in subjects_list:
            a_score = marks_map.get((student.id, sub_id, exam_a))
            b_score = marks_map.get((student.id, sub_id, exam_b))
            
            scores = [s for s in [a_score, b_score] if s is not None]
            avg = round(sum(scores) / len(scores), 2) if scores else None
            grade = calculate_primary_grade(avg) if avg else ""
            
            student_subject_avg[student.id][sub_id] = {
                "avg": avg,
                "a_score": a_score,
                "b_score": b_score,
                "grade": grade
            }
    
    subject_positions = {}
    for sub_id, sub_name in subjects_list:
        scores = []
        for student in students:
            info = student_subject_avg[student.id].get(sub_id)
            avg = info.get("avg") if info else None
            if avg is not None:
                scores.append((student.id, avg))
        scores.sort(key=lambda x: x[1], reverse=True)
        for idx, (sid, _) in enumerate(scores, start=1):
            if sub_id not in subject_positions:
                subject_positions[sub_id] = {}
            subject_positions[sub_id][sid] = idx
    
    summary_map = {}
    for student in students:
        avgs = []
        for sub_id, _ in subjects_list:
            info = student_subject_avg[student.id].get(sub_id)
            if info and info.get("avg") is not None:
                avgs.append(info["avg"])
        
        if avgs:
            overall_avg = round(sum(avgs) / len(avgs), 2)
            grade = calculate_primary_grade(overall_avg)
        else:
            overall_avg = 0
            grade = "E"
        
        summary_map[student.id] = {"overall_avg": overall_avg, "grade": grade}
    
    sorted_students = sorted(students, key=lambda s: summary_map.get(s.id, {}).get("overall_avg", 0), reverse=True)
    positions = {s.id: idx + 1 for idx, s in enumerate(sorted_students)}
    total_students = len(students)
    
    students_data = []
    for student in sorted_students:
        subjects_data = []
        for sub_id, sub_name in subjects_list:
            info = student_subject_avg[student.id].get(sub_id, {})
            if info.get("a_score") is not None or info.get("b_score") is not None:
                jumla = ""
                if info.get("a_score") is not None and info.get("b_score") is not None:
                    jumla = f"{info['a_score'] + info['b_score']:.1f}"
                elif info.get("a_score") is not None:
                    jumla = f"{info['a_score']:.1f}"
                elif info.get("b_score") is not None:
                    jumla = f"{info['b_score']:.1f}"
                
                avg_val = f"{info['avg']:.1f}" if info.get('avg') else ""
                grade_val = info.get('grade', '')
                subj_position = subject_positions.get(sub_id, {}).get(student.id, "")
                
                subjects_data.append({
                    "name": sub_name,
                    "a_score": info.get("a_score"),
                    "b_score": info.get("b_score"),
                    "jumla": jumla,
                    "avg": avg_val,
                    "final_grade": grade_val,
                    "position": subj_position
                })
        
        summ = summary_map.get(student.id, {})
        overall_avg = summ.get("overall_avg", 0)
        grade = summ.get("grade", "E")
        position = positions.get(student.id, len(sorted_students))
        
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        darasa = class_obj.name if class_obj else "Darasa la 1"
        
        teacher_remarks = get_primary_teacher_remarks(grade, overall_avg)
        headmaster_remarks = get_primary_headmaster_remarks(grade, overall_avg)
        
        students_data.append({
            "id": student.id,
            "name": student.name,
            "kidato": darasa,
            "term": term_display,
            "year": year,
            "subjects": subjects_data,
            "division": grade,
            "points": 0,
            "average": overall_avg,
            "position": position,
            "total_students": total_students,
            "teacher_remarks": teacher_remarks,
            "headmaster_remarks": headmaster_remarks,
            "teacher_name": teacher_name or "________________________",
            "headmaster_name": headmaster_name or "________________________",
            "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
            "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
            "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
            "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
            "school_name": school_name,
            "district_name": final_district_name
        })
    
    return {
        "class_name": school_class.name,
        "school_name": school_name,
        "term": term_display,
        "year": year,
        "students": students_data,
        "total_students": total_students,
        "district_name": final_district_name,
        "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
        "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
        "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
        "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
        "teacher_name": teacher_name or "________________________",
        "headmaster_name": headmaster_name or "________________________"
    }


# ============================================================
# 🔥🔥🔥 ROUTE 1: SUMMARY-VIEW (ON-SCREEN)
# ============================================================

@router.get("/class/{class_id}/summary-view")
def get_primary_class_summary_view(
    class_id: int,
    exam_type: str = Query(..., description="Exam type: MIDTERM3, MIDTERM9, TERMINAL, ANNUAL"),
    region: Optional[str] = Query(None, description="District/Region name - can be provided by user"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """PRIMARY CLASS SUMMARY VIEW - No division, no points, all subjects"""
    from app.models.school import School
    from app.models.school_class import SchoolClass
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.mark import Mark
    from datetime import datetime
    
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    verify_primary_school(school_class.school_id, db)
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SHULE YA MSINGI"
    
    final_region = region
    if not final_region and school:
        final_region = getattr(school, 'region', None)
        if not final_region:
            final_region = getattr(school, 'district', None)
    if not final_region:
        final_region = "_________________________"
    
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        return {
            "school_name": school_name,
            "region": final_region,
            "class_name": school_class.name,
            "exam_type": exam_type,
            "year": datetime.now().year,
            "division_summary": {
                "A": {"M": 0, "F": 0}, "B": {"M": 0, "F": 0},
                "C": {"M": 0, "F": 0}, "D": {"M": 0, "F": 0},
                "E": {"M": 0, "F": 0}
            },
            "registration_summary": {"male_reg": 0, "female_reg": 0, "total_reg": 0},
            "results": [],
            "subject_names": [],
            "subject_grade_summary": []
        }
    
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subject_names = [s.name for s in subjects]
    
    marks = db.query(Mark).join(Student).filter(
        Student.class_id == class_id,
        Mark.exam_type == exam_type
    ).all()
    
    marks_map = {}
    for m in marks:
        marks_map[(m.student_id, m.subject_id)] = m.score
    
    results = []
    grade_summary = {"A": {"M": 0, "F": 0}, "B": {"M": 0, "F": 0},
                     "C": {"M": 0, "F": 0}, "D": {"M": 0, "F": 0},
                     "E": {"M": 0, "F": 0}}
    reg_summary = {"M": 0, "F": 0}
    
    subject_grade_counts = {sub.name: {'A': {'M': 0, 'F': 0}, 'B': {'M': 0, 'F': 0},
                                       'C': {'M': 0, 'F': 0}, 'D': {'M': 0, 'F': 0},
                                       'E': {'M': 0, 'F': 0}} for sub in subjects}
    
    for student in students:
        student_marks = [m for m in marks if m.student_id == student.id]
        
        if student_marks:
            reg_summary[student.sex] += 1
        
        subject_scores = []
        total = 0
        valid_subjects = 0
        
        for idx, sub in enumerate(subjects):
            score = marks_map.get((student.id, sub.id))
            if score is not None:
                subject_scores.append(score)
                total += score
                valid_subjects += 1
                g = calculate_primary_grade(score)
                subject_grade_counts[sub.name][g][student.sex] += 1
            else:
                subject_scores.append("")
        
        if valid_subjects > 0:
            avg = round(total / valid_subjects, 2)
        else:
            avg = 0
        
        grade = calculate_primary_grade(avg)
        
        if grade in grade_summary and student_marks:
            grade_summary[grade][student.sex] += 1
        
        exam_no = student.roll_number or f"P-{student.id:04d}"
        
        results.append({
            "student_id": student.id,
            "exam_no": exam_no,
            "name": student.name,
            "sex": student.sex,
            "subjects": subject_scores,
            "total": total,
            "average": avg,
            "grade": grade,
            "division": "N/A",
            "points": 0
        })
    
    results.sort(key=lambda x: x["average"], reverse=True)
    for i, result in enumerate(results, 1):
        result["position"] = i
    
    subject_grade_summary = []
    for sub in subjects:
        subject_grade_summary.append({
            "subject": sub.name,
            "grades": {
                "A": subject_grade_counts[sub.name]['A']['M'] + subject_grade_counts[sub.name]['A']['F'],
                "B": subject_grade_counts[sub.name]['B']['M'] + subject_grade_counts[sub.name]['B']['F'],
                "C": subject_grade_counts[sub.name]['C']['M'] + subject_grade_counts[sub.name]['C']['F'],
                "D": subject_grade_counts[sub.name]['D']['M'] + subject_grade_counts[sub.name]['D']['F'],
                "E": subject_grade_counts[sub.name]['E']['M'] + subject_grade_counts[sub.name]['E']['F']
            }
        })
    
    return {
        "school_name": school_name,
        "region": final_region,
        "class_name": school_class.name,
        "exam_type": exam_type,
        "year": datetime.now().year,
        "division_summary": {
            "A": grade_summary["A"],
            "B": grade_summary["B"],
            "C": grade_summary["C"],
            "D": grade_summary["D"],
            "E": grade_summary["E"],
            "total_male": sum(d["M"] for d in grade_summary.values()),
            "total_female": sum(d["F"] for d in grade_summary.values()),
            "total_students": sum(d["M"] + d["F"] for d in grade_summary.values())
        },
        "registration_summary": {
            "male_reg": reg_summary["M"],
            "female_reg": reg_summary["F"],
            "total_reg": reg_summary["M"] + reg_summary["F"]
        },
        "results": results,
        "subject_names": subject_names,
        "subject_grade_summary": subject_grade_summary
    }


















# ============================================================
# 🔥 PARENT REPORT DATA - MWANAFUNZI MM OJA! (VERSION MPYA KABISA!)
# ============================================================

@router.get("/student/{student_id}/parent-report-data")
def get_primary_student_parent_report_data(
    student_id: int,
    term: str = Query("I", description="Muhula: I or II"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None),
    opening_date: Optional[str] = Query(None),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 RETURN JSON DATA FOR A SINGLE PRIMARY STUDENT FOR PDF GENERATION.
    HII NI KWA MWANAFUNZI MM OJA!
    """
    from app.models.school import School
    from app.models.school_class import SchoolClass
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.mark import Mark
    from app.models.stream import Stream
    from datetime import datetime
    
    # ============================================================
    # 🔥 1. GET STUDENT
    # ============================================================
    result = db.query(
        Student.id,
        Student.name,
        Student.sex,
        Student.roll_number,
        Student.school_id,
        Student.class_id,
        Student.stream_id,
        Student.father_name,
        Student.father_phone,
        Student.mother_name,
        Student.mother_phone,
        Student.health_info,
        Student.address,
        Student.enrollment_date,
        SchoolClass.name.label("class_name"),
        Stream.name.label("stream_name")
    ).join(
        SchoolClass, Student.class_id == SchoolClass.id, isouter=True
    ).join(
        Stream, Student.stream_id == Stream.id, isouter=True
    ).filter(
        Student.id == student_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Student not found")
    
    verify_primary_school(result.school_id, db)
    
    # ============================================================
    # 🔥 2. GET SCHOOL INFO
    # ============================================================
    school = db.query(School).filter(School.id == result.school_id).first()
    school_name = school.name if school else "SHULE YA MSINGI"
    
    class_name = result.class_name or "Darasa"
    stream_name = result.stream_name or ""
    
    final_district_name = district_name
    if not final_district_name and school:
        final_district_name = getattr(school, 'district', None)
    if not final_district_name:
        final_district_name = "_________________________"
    
    # ============================================================
    # 🔥 3. DETERMINE EXAM TYPES
    # ============================================================
    term_upper = term.strip().upper()
    if term_upper in ("II", "MUHULA II", "2"):
        exam_a = "MIDTERM9"
        exam_b = "ANNUAL"
        term_display = "II"
    else:
        exam_a = "MIDTERM3"
        exam_b = "TERMINAL"
        term_display = "I"
    
    # ============================================================
    # 🔥 4. GET SUBJECTS
    # ============================================================
    subjects = db.query(Subject).filter(Subject.school_id == result.school_id).all()
    
    subject_order = ["KISWAHILI", "ENGLISH", "HISABATI", "SAYANSI", "JAMII", "URAIA", "SANAAMICHEZO"]
    sorted_subjects = []
    for name in subject_order:
        for s in subjects:
            if s.name.upper() == name.upper() and s not in sorted_subjects:
                sorted_subjects.append(s)
    for s in subjects:
        if s not in sorted_subjects:
            sorted_subjects.append(s)
    
    # ============================================================
    # 🔥 5. GET MARKS FOR THIS STUDENT
    # ============================================================
    marks = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type.in_([exam_a, exam_b])
    ).all()
    
    marks_map = {}
    for m in marks:
        marks_map[(m.subject_id, m.exam_type)] = m.score
    
    # ============================================================
    # 🔥 6. GET ALL STUDENTS IN SAME CLASS
    # ============================================================
    all_students = db.query(Student).filter(
        Student.class_id == result.class_id
    ).all()
    
    # ============================================================
    # 🔥🔥🔥 7. CALCULATE SUBJECT POSITIONS 🔥🔥🔥
    # ============================================================
    subject_positions = {}
    
    for sub in sorted_subjects:
        # Get all students' averages for this subject
        subject_scores = []
        for other in all_students:
            other_marks = db.query(Mark).filter(
                Mark.student_id == other.id,
                Mark.subject_id == sub.id,
                Mark.exam_type.in_([exam_a, exam_b])
            ).all()
            
            if other_marks:
                other_scores = [m.score for m in other_marks]
                other_avg = round(sum(other_scores) / len(other_scores), 2)
                subject_scores.append((other.id, other_avg))
        
        # Get current student's score for this subject
        current_a = marks_map.get((sub.id, exam_a))
        current_b = marks_map.get((sub.id, exam_b))
        current_scores = [s for s in [current_a, current_b] if s is not None]
        current_avg = round(sum(current_scores) / len(current_scores), 2) if current_scores else None
        
        if current_avg is not None:
            pos = 1
            for _, other_avg in subject_scores:
                if other_avg > current_avg:
                    pos += 1
            subject_positions[sub.id] = pos
        else:
            subject_positions[sub.id] = "-"
    
    # ============================================================
    # 🔥 8. BUILD SUBJECT DATA
    # ============================================================
    subjects_data = []
    total_score = 0
    valid_subjects = 0
    
    for sub in sorted_subjects:
        a_score = marks_map.get((sub.id, exam_a))
        b_score = marks_map.get((sub.id, exam_b))
        
        scores = [s for s in [a_score, b_score] if s is not None]
        avg = round(sum(scores) / len(scores), 2) if scores else None
        
        jumla = ""
        if a_score is not None and b_score is not None:
            jumla = f"{a_score + b_score:.1f}"
        elif a_score is not None:
            jumla = f"{a_score:.1f}"
        elif b_score is not None:
            jumla = f"{b_score:.1f}"
        
        grade = calculate_primary_grade(avg) if avg is not None else ""
        comment = get_primary_comment(avg) if avg is not None else ""
        
        position = subject_positions.get(sub.id, "-")
        
        subjects_data.append({
            "name": sub.name,
            "a_score": a_score,
            "b_score": b_score,
            "jumla": jumla,
            "avg": f"{avg:.1f}" if avg is not None else "",
            "final_grade": grade,
            "position": position,
            "comment": comment
        })
        
        if avg is not None:
            total_score += avg
            valid_subjects += 1
    
    # ============================================================
    # 🔥 9. CALCULATE OVERALL POSITION (SAHIHI!)
    # ============================================================
    overall_avg = round(total_score / valid_subjects, 2) if valid_subjects > 0 else 0
    overall_grade = calculate_primary_grade(overall_avg)
    
    # 🔥🔥🔥 HESABU NAFASI KWA KULINGANISHA NA WANAFUNZI WOTE! 🔥🔥🔥
    overall_position = 1
    
    for other in all_students:
        if other.id == student_id:
            continue
        
        # 🔥 PATA MARKS ZA MWANAFUNZI MWINGINE
        other_total = 0
        other_valid = 0
        
        for sub in sorted_subjects:
            other_marks = db.query(Mark).filter(
                Mark.student_id == other.id,
                Mark.subject_id == sub.id,
                Mark.exam_type.in_([exam_a, exam_b])
            ).all()
            
            if other_marks:
                other_scores = [m.score for m in other_marks]
                other_avg = round(sum(other_scores) / len(other_scores), 2)
                other_total += other_avg
                other_valid += 1
        
        if other_valid > 0:
            other_overall_avg = round(other_total / other_valid, 2)
            if other_overall_avg > overall_avg:
                overall_position += 1
    
    total_students = len(all_students)
    
    # ============================================================
    # 🔥 10. GENERATE REMARKS
    # ============================================================
    teacher_remarks = get_primary_teacher_remarks(overall_grade, overall_avg)
    headmaster_remarks = get_primary_headmaster_remarks(overall_grade, overall_avg)
    
    # ============================================================
    # 🔥 11. RETURN DATA
    # ============================================================
    return {
        "class_name": class_name,
        "school_name": school_name,
        "term": term_display,
        "year": year,
        "students": [
            {
                "id": result.id,
                "name": result.name,
                "kidato": class_name,
                "term": term_display,
                "year": year,
                "subjects": subjects_data,
                "division": overall_grade,
                "points": 0,
                "average": overall_avg,
                "position": overall_position,  # ✅ NAFASI SAHIHI!
                "total_students": total_students,
                "teacher_remarks": teacher_remarks,
                "headmaster_remarks": headmaster_remarks,
                "teacher_name": teacher_name or "________________________",
                "headmaster_name": headmaster_name or "________________________",
                "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
                "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
                "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
                "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
                "school_name": school_name,
                "district_name": final_district_name
            }
        ],
        "total_students": total_students,
        "district_name": final_district_name,
        "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
        "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
        "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
        "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
        "teacher_name": teacher_name or "________________________",
        "headmaster_name": headmaster_name or "________________________"
    }