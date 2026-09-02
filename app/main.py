# app/main.py

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
from app.api.v1.primary import ai_exam as primary_ai_exam

# 🔥 PARENTS API
from app.api.v1 import parents as parents_router

# 🔥 SCHOOL ANNOUNCEMENTS API
from app.api.v1 import school_announcements as school_announcements_router

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

# ============================================================
# ✅ REDIS - TRY CONNECT BUT CONTINUE WITHOUT IT
# ============================================================
redis_client = None
REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"

if REDIS_URL and REDIS_ENABLED:
    try:
        import redis
        redis_client = redis.Redis.from_url(
            REDIS_URL,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        redis_client = None
else:
    logger.info("ℹ️ Redis is disabled, running without Redis")

# ============================================================
# 🔥 FASTAPI APP INSTANCE
# ============================================================
app = FastAPI(
    title="MASI FAST RESULTS API",
    description="Multi-tenant system for Primary and Secondary Schools",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ============================================================
# 🔥🔥🔥 CORS MIDDLEWARE 🔥🔥🔥
# ============================================================

# 🔥 Domain zote zinazoruhusiwa
ALLOWED_ORIGINS_DEFAULT = (
    "http://localhost:3000,"
    "http://localhost:8000,"
    "https://bubblesmanage.com,"
    "https://fast-results-frontend.vercel.app,"
    "https://fast-results-backend-ewis.onrender.com"
)

ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", ALLOWED_ORIGINS_DEFAULT)

# 🔥 Split and clean
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

logger.info(f"🔧 CORS Allowed Origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-User-Type",
        "X-School-Id",
    ],
    expose_headers=[
        "Content-Length",
        "X-Total-Count",
        "X-Rate-Limit-Remaining",
    ],
    max_age=3600,
)

# ============================================================
# 🔥 STATIC FILES (Uploads)
# ============================================================
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

# 🔥 Primary Past Papers
primary_past_papers_dir = Path("uploads/primary/past_papers")
primary_past_papers_dir.mkdir(parents=True, exist_ok=True)

# 🔥 Secondary Past Papers
past_papers_dir = Path("uploads/past_papers")
past_papers_dir.mkdir(parents=True, exist_ok=True)

# 🔥 Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

logger.info("📁 Upload directories created successfully")

# ============================================================
# 🔥 HELPER - GET REDIS (SAFE)
# ============================================================
def get_redis():
    """Return redis client or None if not available"""
    return redis_client

# ============================================================
# 🔥 REGISTER API ROUTERS
# ============================================================

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

# ------ PARENTS ROUTER ------
app.include_router(parents_router.router, prefix="/api/v1", tags=["Parents"])

# ------ SCHOOL ANNOUNCEMENTS ROUTER ------
app.include_router(school_announcements_router.router, prefix="/api/v1", tags=["School Announcements"])

# ------ SECONDARY ROUTERS ------
app.include_router(secondary_dashboard.router, prefix="/api/v1/secondary", tags=["Secondary Dashboard"])

# ------ PRIMARY ROUTERS ------
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
app.include_router(primary_ai_exam.router, prefix="/api/v1", tags=["Primary AI Exam"])

logger.info("✅ All routers registered successfully")

# ============================================================
# 🔥 ROOT & HEALTH ENDPOINTS
# ============================================================

@app.get("/", summary="Root endpoint")
def root():
    return {
        "message": "MASI FAST RESULTS",
        "status": "running",
        "version": "3.0.0",
        "docs": "/docs",
        "health": "/health",
        "redis": "connected" if redis_client else "disabled"
    }

@app.get("/health", summary="Health check endpoint")
def health():
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "redis": "connected" if redis_client else "disabled"
    }

# ============================================================
# 🔥 TEACHER STUDENTS ENDPOINT
# ============================================================

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

# ============================================================
# 🔥 API LIST ENDPOINT (Debugging)
# ============================================================

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
    return {
        "total_routes": len(routes),
        "routes": routes
    }

# ============================================================
# 🔥 ERROR HANDLERS
# ============================================================

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if os.getenv("DEBUG", "False").lower() == "true" else "Something went wrong",
            "path": request.url.path
        }
    )

# ============================================================
# 🔥 STARTUP EVENT
# ============================================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 MASI FAST RESULTS starting up...")
    logger.info(f"📡 Environment: {os.getenv('APP_ENVIRONMENT', 'development')}")
    logger.info(f"🔧 CORS Origins: {ALLOWED_ORIGINS}")
    logger.info(f"🗄️  Database: {'Connected' if os.getenv('DATABASE_URL') else 'Not configured'}")
    logger.info(f"📦 Redis: {'Connected' if redis_client else 'Disabled'}")
    logger.info("✅ API ready to serve requests!")

# ============================================================
# 🔥 SHUTDOWN EVENT
# ============================================================

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 MASI FAST RESULTS API shutting down...")

logger.info("✅ app.main.py loaded successfully")