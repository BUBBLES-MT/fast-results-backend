from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime  # 🔥 ONGEZA HII!
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.mark import Mark
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.school import School
from app.models.school_announcement import SchoolAnnouncement

router = APIRouter()

# ============================================================
# 🔥 PRIMARY - GET PARENT REPORTS DATA
# ============================================================

@router.get("/class/{class_id}/parent-reports-data")
def get_primary_parent_reports_data(
    class_id: int,
    term: str = Query("I", description="Term: I or II"),
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
    """Get data for PRIMARY parent reports"""
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get school
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "School Name"
    
    # 🔥 FETCH ANNOUNCEMENT
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_class.school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    # Determine exam types based on term
    if term.upper() == "II":
        exam_types = ["MIDTERM9", "ANNUAL"]
        term_display = "II"
    else:
        exam_types = ["MIDTERM3", "TERMINAL"]
        term_display = "I"
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    # Get all subjects for this school
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subject_map = {s.id: s.name for s in subjects}
    
    # Process each student
    students_data = []
    for student in students:
        # Get marks for both exam types
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type.in_(exam_types),
            Mark.year == year
        ).all()
        
        if not marks:
            continue
        
        # Build subject scores
        subject_scores = {}
        for mark in marks:
            if mark.subject_id not in subject_scores:
                subject_scores[mark.subject_id] = {}
            subject_scores[mark.subject_id][mark.exam_type] = mark.score
        
        # Build results
        results = []
        total_score = 0
        for sub_id, sub_name in subject_map.items():
            if sub_id in subject_scores:
                a_score = subject_scores[sub_id].get(exam_types[0])
                b_score = subject_scores[sub_id].get(exam_types[1])
                if a_score is not None or b_score is not None:
                    scores = [s for s in [a_score, b_score] if s is not None]
                    avg = sum(scores) / len(scores) if scores else 0
                    total_score += avg
                    results.append({
                        "subject_name": sub_name,
                        "a_score": a_score,
                        "b_score": b_score,
                        "average": round(avg, 2),
                        "grade": calculate_primary_grade(avg)
                    })
        
        # Calculate overall
        overall_avg = total_score / len(results) if results else 0
        overall_grade = calculate_primary_grade(overall_avg)
        
        students_data.append({
            "student": {
                "id": student.id,
                "name": student.name,
                "roll_number": student.roll_number,
                "class_name": school_class.name,
                "stream_name": None
            },
            "results": results,
            "overall": {
                "total_score": round(total_score, 2),
                "average": round(overall_avg, 2),
                "grade": overall_grade,
                "position": 0,
                "total_students": len([s for s in students if s.id != student.id])
            }
        })
    
    # Sort by average and assign positions
    students_data.sort(key=lambda x: x["overall"]["average"], reverse=True)
    for i, data in enumerate(students_data, 1):
        data["overall"]["position"] = i
    
    return {
        "school_name": school_name,
        "class_name": school_class.name,
        "term": term_display,
        "year": year,
        "students": students_data,
        "announcement": {
            "closing_date": announcement.closing_date.strftime("%d/%m/%Y") if announcement and announcement.closing_date else None,
            "opening_date": announcement.opening_date.strftime("%d/%m/%Y") if announcement and announcement.opening_date else None
        } if announcement else None,
        "teacher_info": {
            "name": teacher_name,
            "date": teacher_date
        },
        "headmaster_info": {
            "name": headmaster_name,
            "date": headmaster_date
        },
        "district": district_name
    }


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