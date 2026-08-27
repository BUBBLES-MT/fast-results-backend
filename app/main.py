from app.api.v1.auth import auth
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.v1 import students, teachers, schools, ai_exam, superadmin, classes, subjects
from app.api.v1 import past_papers, marks, reports, streams, academic, promote
from app.api.v1.secondary import dashboard as secondary_dashboard
from app.api.v1.primary import dashboard as primary_dashboard

# 🔥 PRIMARY API IMPORTS
from app.api.v1.primary.reports import top_students as primary_top_students
from app.api.v1.primary.academic import unassigned_slots as primary_unassigned_slots
from app.api.v1.primary import classes as primary_classes
from app.api.v1.primary import streams as primary_streams
from app.api.v1.primary import students as primary_students
from app.api.v1.primary import teachers as primary_teachers
from app.api.v1.primary import subjects as primary_subjects
from app.api.v1.primary import promote as primary_promote
from app.api.v1.primary import marks as primary_marks
from app.api.v1.primary import past_papers as primary_past_papers

# 🔥🔥🔥 ONGEZA HII - PRIMARY AI EXAM! 🔥🔥🔥
from app.api.v1.primary import ai_exam as primary_ai_exam

# ============================================================
# 🔥 PARENTS API (MPYA!)
# ============================================================
from app.api.v1 import parents as parents_router

# ============================================================
# 🔥 SCHOOL ANNOUNCEMENTS API (MPYA!)
# ============================================================
from app.api.v1 import school_announcements as school_announcements_router

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from typing import Optional
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="School Management System",
    description="Multi-tenant system for Primary and Secondary Schools",
    version="2.0.0"
)

# =========================
# 🔹 CORS Middleware
# =========================
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.100:3000",
    "http://192.168.1.101:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 🔹 STATIC FILES (For uploads)
# =========================
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

# 🔥 PRIMARY PAST PAPERS UPLOAD DIRECTORY
primary_past_papers_dir = Path("uploads/primary/past_papers")
primary_past_papers_dir.mkdir(parents=True, exist_ok=True)

past_papers_dir = Path("uploads/past_papers")
past_papers_dir.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# =========================
# 🔹 Register API Routers
# =========================

# ------ GENERAL ROUTERS ------
app.include_router(students.router, prefix="/api/v1", tags=["Students"])
app.include_router(teachers.router, prefix="/api/v1", tags=["Teachers"])
app.include_router(schools.router, prefix="/api/v1", tags=["Schools"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(ai_exam.router, prefix="/api/v1/ai-exam", tags=["AI Exam Generator"])
app.include_router(superadmin.router, prefix="/api/v1/superadmin", tags=["SuperAdmin"])
app.include_router(classes.router, prefix="/api/v1", tags=["Classes"])  
app.include_router(subjects.router, prefix="/api/v1", tags=["Subjects"])
app.include_router(marks.router, prefix="/api/v1", tags=["Marks"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])  
app.include_router(streams.router, prefix="/api/v1", tags=["Streams"])
app.include_router(academic.router, prefix="/api/v1/academic", tags=["Academic"])
app.include_router(promote.router, prefix="/api/v1/promote", tags=["Promote"])
app.include_router(past_papers.router, prefix="/api/v1", tags=["Past Papers"])

# ============================================================
# 🔥 PARENTS ROUTER (MPYA!)
# ============================================================
app.include_router(parents_router.router, prefix="/api/v1", tags=["Parents"])

# ============================================================
# 🔥 SCHOOL ANNOUNCEMENTS ROUTER (MPYA!)
# ============================================================
app.include_router(school_announcements_router.router, prefix="/api/v1", tags=["School Announcements"])

# ------ SECONDARY ROUTERS ------
app.include_router(secondary_dashboard.router, prefix="/api/v1/secondary", tags=["Secondary Dashboard"])

# ============================================================
# 🔥 PRIMARY ROUTERS (ZOTE ZIMEONGEZWA)
# ============================================================
app.include_router(primary_dashboard.router, prefix="/api/v1", tags=["Primary Dashboard"])
app.include_router(primary_top_students.router, prefix="/api/v1", tags=["Primary Reports"])
app.include_router(primary_unassigned_slots.router, prefix="/api/v1", tags=["Primary Academic"])
app.include_router(primary_classes.router, prefix="/api/v1", tags=["Primary Classes"])
app.include_router(primary_streams.router, prefix="/api/v1", tags=["Primary Streams"])
app.include_router(primary_students.router, prefix="/api/v1", tags=["Primary Students"])
app.include_router(primary_teachers.router, prefix="/api/v1", tags=["Primary Teachers"])
app.include_router(primary_subjects.router, prefix="/api/v1", tags=["Primary Subjects"])
app.include_router(primary_promote.router, prefix="/api/v1", tags=["Primary Promote"])
app.include_router(primary_marks.router, prefix="/api/v1", tags=["Primary Marks"])
app.include_router(primary_past_papers.router, prefix="/api/v1", tags=["Primary Past Papers"])

# 🔥🔥🔥 ONGEZA HII - PRIMARY AI EXAM! 🔥🔥🔥
app.include_router(primary_ai_exam.router, prefix="/api/v1", tags=["Primary AI Exam"])

# =========================
# 🔹 Root & Health Endpoints
# =========================
@app.get("/", summary="Root endpoint")
def root():
    return {
        "message": "School Management System API",
        "status": "running",
        "version": "2.0.0"
    }

@app.get("/health", summary="Health check endpoint")
def health():
    return {"status": "healthy"}

# =========================
# 🔹 TEACHER STUDENTS ENDPOINT (Direct)
# =========================
@app.get("/api/v1/teacher-my-students")
def get_teacher_my_students(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    teacher_id: Optional[int] = Query(None)
):
    """Get students for teachers and academic staff who teach"""
    from app.models.teacher_subject import TeacherSubject
    from app.models.student import Student
    from app.models.school_class import SchoolClass
    from app.models.stream import Stream
    from app.models.subject import Subject
    
    logger.debug(
        "teacher_my_students user_id=%s role=%s teacher_id_query=%s",
        getattr(current_user, "id", None),
        getattr(current_user, "role", None),
        teacher_id,
    )

    target_teacher_id = teacher_id if teacher_id else current_user.id
    
    assignments = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == target_teacher_id
    ).all()
    
    if not assignments:
        return []
    
    result = []
    
    for assignment in assignments:
        subject = db.query(Subject).filter(Subject.id == assignment.subject_id).first()
        subject_name = subject.name if subject else f"Subject {assignment.subject_id}"
        
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == assignment.class_id).first()
        class_name = class_obj.name if class_obj else f"Class {assignment.class_id}"
        
        stream_obj = db.query(Stream).filter(Stream.id == assignment.stream_id).first()
        stream_name = stream_obj.name if stream_obj else ""
        
        if stream_name:
            display_class = f"{class_name} {stream_name}"
        else:
            display_class = class_name
        
        students = db.query(Student).filter(
            Student.class_id == assignment.class_id,
            Student.stream_id == assignment.stream_id
        ).all()
        
        for student in students:
            result.append({
                "id": student.id,
                "name": student.name,
                "sex": student.sex,
                "roll_number": student.roll_number,
                "school_id": student.school_id,
                "class_id": student.class_id,
                "class_name": display_class,
                "stream_id": student.stream_id,
                "stream_name": stream_name,
                "subject_id": assignment.subject_id,
                "subject_name": subject_name,
                "father_name": student.father_name,
                "father_phone": student.father_phone,
                "health_info": student.health_info,
                "address": student.address
            })
    
    return result

# =========================
# 🔹 API LIST ENDPOINT (Helpful for debugging)
# =========================
@app.get("/api/v1/routes", summary="List all registered routes")
def list_routes():
    """List all registered API routes - helpful for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else []
            })
    return {"routes": routes}