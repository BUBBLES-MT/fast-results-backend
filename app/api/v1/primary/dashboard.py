from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.school import School
from app.models.superadmin import SuperAdmin
from typing import Optional
from pydantic import BaseModel

# 🔥 HII NDIO SAHIHI - prefix ni "/primary"
router = APIRouter(prefix="/primary", tags=["Primary Dashboard"])

class DashboardStatsResponse(BaseModel):
    total_students: int
    total_teachers: int
    total_classes: int
    total_subjects: int
    new_students_this_week: int
    new_teachers_this_week: int
    upcoming_exams_count: int
    recent_activities: list

@router.get("/dashboard-stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get real dashboard statistics for primary school"""
    
    # Get user's school_id
    school_id = None
    if hasattr(current_user, 'school_id'):
        school_id = current_user.school_id
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if school.school_level != "primary":
        raise HTTPException(status_code=400, detail="This is not a primary school")
    
    # Calculate date range for "this week"
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # Total students
    total_students = db.query(Student).filter(Student.school_id == school_id).count()
    
    # Total teachers
    total_teachers = db.query(Teacher).filter(Teacher.school_id == school_id).count()
    
    # Total classes
    from app.models.school_class import SchoolClass
    total_classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).count()
    
    # Total subjects
    from app.models.subject import Subject
    total_subjects = db.query(Subject).filter(Subject.school_id == school_id).count()
    
    # New students this week - using enrollment_date
    new_students_this_week = db.query(Student).filter(
        and_(
            Student.school_id == school_id,
            func.date(Student.enrollment_date) >= start_of_week
        )
    ).count()
    
    # New teachers this week
    new_teachers_this_week = db.query(Teacher).filter(
        and_(
            Teacher.school_id == school_id,
            func.date(Teacher.created_at) >= start_of_week
        )
    ).count()
    
    # Upcoming exams count - with try/except
    try:
        from app.models.exam import Exam
        upcoming_exams_count = db.query(Exam).filter(
            and_(
                Exam.school_id == school_id,
                Exam.exam_date >= today
            )
        ).count()
    except:
        upcoming_exams_count = 0
    
    # Build recent activities dynamically
    recent_activities = []
    
    if new_students_this_week > 0:
        recent_activities.append(f"🎉 Wanafunzi {new_students_this_week} wamejiunga wiki hii")
    
    if new_teachers_this_week > 0:
        recent_activities.append(f"👨‍🏫 Walimu {new_teachers_this_week} wameongezwa kwenye mfumo")
    
    if upcoming_exams_count > 0:
        recent_activities.append(f"📋 Mitihani {upcoming_exams_count} inakuja hivi karibuni")
    
    if not recent_activities:
        recent_activities.append("📊 Hakuna shughuli mpya wiki hii")
    
    return DashboardStatsResponse(
        total_students=total_students,
        total_teachers=total_teachers,
        total_classes=total_classes,
        total_subjects=total_subjects,
        new_students_this_week=new_students_this_week,
        new_teachers_this_week=new_teachers_this_week,
        upcoming_exams_count=upcoming_exams_count,
        recent_activities=recent_activities
    )