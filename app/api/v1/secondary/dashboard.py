from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.school_class import SchoolClass
from app.models.subject import Subject
from pydantic import BaseModel
from typing import List

router = APIRouter()

class DashboardStatsResponse(BaseModel):
    total_students: int
    total_teachers: int
    total_classes: int
    total_subjects: int
    new_students_this_week: int
    new_teachers_this_week: int
    upcoming_exams_count: int
    recent_activities: List[str]

@router.get("/dashboard-stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get real dashboard statistics for secondary school"""
    
    # Get user's school_id
    school_id = None
    if hasattr(current_user, 'school_id'):
        school_id = current_user.school_id
    
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # Get counts
    total_students = db.query(Student).filter(Student.school_id == school_id).count()
    total_teachers = db.query(Teacher).filter(Teacher.school_id == school_id).count()
    total_classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).count()
    total_subjects = db.query(Subject).filter(Subject.school_id == school_id).count()
    
    # 🔥 FIXED: Use enrollment_date instead of created_at
    new_students_this_week = db.query(Student).filter(
        and_(
            Student.school_id == school_id,
            func.date(Student.enrollment_date) >= start_of_week
        )
    ).count()
    
    # 🔥 For teachers - if teacher has created_at or similar field
    # If Teacher model doesn't have created_at, set to 0
    new_teachers_this_week = 0  # TODO: Add created_at to Teacher model
    
    upcoming_exams_count = 0  # TODO: Add Exam model
    
    # Build activities
    recent_activities = []
    if new_students_this_week > 0:
        recent_activities.append(f"🎉 {new_students_this_week} new student(s) joined this week")
    if new_teachers_this_week > 0:
        recent_activities.append(f"👨‍🏫 {new_teachers_this_week} new teacher(s) added")
    if upcoming_exams_count > 0:
        recent_activities.append(f"📋 {upcoming_exams_count} upcoming exam(s) scheduled")
    if not recent_activities and total_students > 0:
        recent_activities.append(f"📊 Total students: {total_students}, Teachers: {total_teachers}")
    elif not recent_activities:
        recent_activities.append("📊 No new activities this week")
    
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