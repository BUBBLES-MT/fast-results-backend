from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.responses import FileResponse  # 🔥 ADD THIS IMPORT
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import shutil
from pathlib import Path
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.past_paper import PastPaper
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.subject import Subject
from app.models.school import School
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel

router = APIRouter()

# Create upload directory if not exists
UPLOAD_DIR = Path("uploads/past_papers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}

# ================================
# Helper function to get role string
# ================================
def get_role_string(role):
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)


# ================================
# Pydantic Schemas
# ================================

class PastPaperResponse(BaseModel):
    id: int
    title: str
    subject: str
    exam_type: str
    year: int
    class_level: str
    school_level: str
    file_url: str
    file_name: str
    file_size: Optional[int]
    description: Optional[str]
    uploaded_by: int
    school_name: Optional[str] = None
    downloads: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ================================
# API Endpoints (ORDERED CORRECTLY)
# ================================

# 1. GET endpoints (no path parameters) - FIRST
@router.get("/past-papers", response_model=List[PastPaperResponse])
def get_past_papers(
    subject: Optional[str] = Query(None),
    exam_type: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    class_level: Optional[str] = Query(None),
    school_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all past papers - ALL users can see ALL past papers from ALL schools"""
    
    query = db.query(PastPaper)
    
    if subject:
        query = query.filter(PastPaper.subject == subject)
    if exam_type:
        query = query.filter(PastPaper.exam_type == exam_type)
    if year:
        query = query.filter(PastPaper.year == year)
    if class_level:
        query = query.filter(PastPaper.class_level == class_level)
    if school_level:
        query = query.filter(PastPaper.school_level == school_level)
    
    papers = query.order_by(PastPaper.year.desc(), PastPaper.created_at.desc()).all()
    
    result = []
    for paper in papers:
        school = db.query(School).filter(School.id == paper.school_id).first()
        result.append(PastPaperResponse(
            id=paper.id,
            title=paper.title,
            subject=paper.subject,
            exam_type=paper.exam_type,
            year=paper.year,
            class_level=paper.class_level,
            school_level=paper.school_level,
            file_url=paper.file_url,
            file_name=paper.file_name,
            file_size=paper.file_size,
            description=paper.description,
            uploaded_by=paper.uploaded_by,
            school_name=school.name if school else "Unknown School",
            downloads=paper.downloads,
            created_at=paper.created_at
        ))
    
    return result


@router.get("/past-papers/subjects")
def get_past_paper_subjects(db: Session = Depends(get_db)):
    """Get all subjects that have past papers"""
    subjects = db.query(PastPaper.subject).distinct().all()
    return {"subjects": [s[0] for s in subjects]}


@router.get("/past-papers/years")
def get_past_paper_years(db: Session = Depends(get_db)):
    """Get all years that have past papers"""
    years = db.query(PastPaper.year).distinct().order_by(PastPaper.year.desc()).all()
    return {"years": [y[0] for y in years]}


@router.get("/past-papers/my-subjects")
def get_my_uploadable_subjects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get subjects that the current user can upload past papers for"""
    
    is_teacher = isinstance(current_user, Teacher)
    is_superadmin = isinstance(current_user, SuperAdmin)
    
    user_role = getattr(current_user, 'role', None)
    user_role_value = get_role_string(user_role)
    
    admin_roles = ["Academic", "Headmaster", "Headmistress", "Second Master", "Second Mistress"]
    
    subjects = []
    
    if is_teacher:
        # Teachers: only their assigned subjects
        teacher_subjects = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == current_user.id
        ).all()
        for ts in teacher_subjects:
            subj = db.query(Subject).filter(Subject.id == ts.subject_id).first()
            if subj:
                subjects.append({
                    "id": subj.id,
                    "name": subj.name,
                    "code": subj.code
                })
    elif user_role_value in admin_roles or is_superadmin:
        # Admin/Superadmin: all subjects in their school
        school_id = getattr(current_user, 'school_id', None)
        if school_id:
            all_subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
            for subj in all_subjects:
                subjects.append({
                    "id": subj.id,
                    "name": subj.name,
                    "code": subj.code
                })
    
    return {"subjects": subjects}


# 2. POST endpoints - SECOND
@router.post("/past-papers/upload")
async def upload_past_paper(
    title: str = Form(...),
    subject: str = Form(...),
    exam_type: str = Form(...),
    year: int = Form(...),
    class_level: str = Form(...),
    school_level: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload a past paper - Teachers, Academic, Headmaster can upload their subjects"""
    
    print("=== UPLOAD PAST PAPER DEBUG ===")
    print(f"User ID: {current_user.id}")
    print(f"User type: {type(current_user)}")
    
    # Check if user is a teacher or has admin role
    is_teacher = isinstance(current_user, Teacher)
    is_superadmin = isinstance(current_user, SuperAdmin)
    
    # Get user role
    user_role = getattr(current_user, 'role', None)
    user_role_value = get_role_string(user_role)
    
    # Allowed roles for upload
    allowed_roles = ["Teacher", "Academic", "Headmaster", "Headmistress", "Second Master", "Second Mistress"]
    
    if not is_teacher and not is_superadmin and user_role_value not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail="Only teachers and academic staff can upload past papers"
        )
    
    # Get uploadable subjects using subject_id
    uploadable_subjects = []
    
    if is_teacher:
        # For regular teachers, only their assigned subjects
        teacher_subjects = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == current_user.id
        ).all()
        
        for ts in teacher_subjects:
            subj = db.query(Subject).filter(Subject.id == ts.subject_id).first()
            if subj:
                uploadable_subjects.append(subj.name)
    else:
        # For Academic, Headmaster, etc. - they can upload any subject in their school
        school_id = getattr(current_user, 'school_id', None)
        if school_id:
            all_subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
            uploadable_subjects = [s.name for s in all_subjects]
    
    print(f"Uploadable subjects: {uploadable_subjects}")
    print(f"Uploading subject: {subject}")
    
    # Check if the subject being uploaded is allowed
    if subject not in uploadable_subjects:
        raise HTTPException(
            status_code=403, 
            detail=f"You can only upload past papers for: {', '.join(uploadable_subjects[:10])}"
        )
    
    # Get school
    school_id = getattr(current_user, 'school_id', None)
    if not school_id and hasattr(current_user, 'school') and current_user.school:
        school_id = current_user.school.id
    
    school = db.query(School).filter(School.id == school_id).first()
    school_name = school.name if school else "Unknown School"
    
    print(f"School: {school_name}")
    
    # Validate required fields
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if not subject or not subject.strip():
        raise HTTPException(status_code=400, detail="Subject is required")
    if not exam_type or not exam_type.strip():
        raise HTTPException(status_code=400, detail="Exam type is required")
    if not year or year <= 0:
        raise HTTPException(status_code=400, detail="Valid year is required")
    if not class_level or not class_level.strip():
        raise HTTPException(status_code=400, detail="Class level is required")
    if not school_level or not school_level.strip():
        raise HTTPException(status_code=400, detail="School level is required")
    
    # Validate file
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File is required")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Max size: 10MB. Your file: {file_size / (1024 * 1024):.2f}MB"
        )
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved to: {file_path}")
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create database record
    try:
        new_paper = PastPaper(
            title=title.strip(),
            subject=subject.strip(),
            exam_type=exam_type.strip(),
            year=year,
            class_level=class_level.strip(),
            school_level=school_level.strip(),
            file_url=f"/uploads/past_papers/{safe_filename}",
            file_name=file.filename,
            file_size=file_size,
            description=description.strip() if description else None,
            uploaded_by=current_user.id,
            school_id=school_id
        )
        
        db.add(new_paper)
        db.commit()
        db.refresh(new_paper)
        
        print(f"Past paper saved to DB with ID: {new_paper.id}")
        
        return {
            "message": "Past paper uploaded successfully",
            "paper_id": new_paper.id,
            "file_name": new_paper.file_name,
            "school_name": school_name,
            "file_size": new_paper.file_size
        }
        
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")


# 3. GET endpoints with path parameters - THIRD
@router.get("/past-papers/{paper_id}/download")
def download_past_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Download a past paper file"""
    
    from fastapi.responses import FileResponse
    
    print(f"=== DOWNLOAD REQUEST ===")
    print(f"Paper ID: {paper_id}")
    
    # Get paper from database
    paper = db.query(PastPaper).filter(PastPaper.id == paper_id).first()
    if not paper:
        print(f"Paper not found: {paper_id}")
        raise HTTPException(status_code=404, detail="Past paper not found")
    
    print(f"Paper found: {paper.title}")
    print(f"File URL in DB: {paper.file_url}")
    
    # Construct file path
    file_url = paper.file_url.lstrip('/')
    file_path = Path(file_url)
    
    print(f"Looking for file at: {file_path.absolute()}")
    
    # Check if file exists
    if not file_path.exists():
        print(f"File not found at: {file_path.absolute()}")
        alt_path = Path("uploads/past_papers") / Path(paper.file_url).name
        print(f"Trying alternative path: {alt_path.absolute()}")
        
        if alt_path.exists():
            file_path = alt_path
            print(f"Found file at alternative path!")
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"File not found on server"
            )
    
    # Increment download count
    paper.downloads += 1
    db.commit()
    
    print(f"Sending file: {file_path.name}")
    
    # Return file
    return FileResponse(
        path=file_path,
        filename=paper.file_name,
        media_type='application/octet-stream',
        headers={
            "Content-Disposition": f"attachment; filename={paper.file_name}"
        }
    )


# 4. DELETE endpoint - FOURTH
@router.delete("/past-papers/{paper_id}")
def delete_past_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a past paper - Only Superadmin can delete"""
    
    paper = db.query(PastPaper).filter(PastPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Past paper not found")
    
    # Only Superadmin can delete
    is_superadmin = isinstance(current_user, SuperAdmin)
    
    if not is_superadmin:
        raise HTTPException(
            status_code=403, 
            detail="Only Superadmin can delete past papers"
        )
    
    # Delete file from disk
    file_path = Path(paper.file_url.lstrip('/'))
    if file_path.exists():
        file_path.unlink()
    
    db.delete(paper)
    db.commit()
    
    return {"message": "Past paper deleted successfully"}