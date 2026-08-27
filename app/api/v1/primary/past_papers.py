from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.responses import FileResponse
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

router = APIRouter(prefix="/primary/past-papers", tags=["Primary Past Papers"])

# Create upload directory if not exists
UPLOAD_DIR = Path("uploads/primary/past_papers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}

# ================================
# 🔥 HELPER FUNCTIONS - PRIMARY ROLES
# ================================
def get_role_string(role):
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

def has_primary_admin_access(user_role: str) -> bool:
    """Check if role has PRIMARY admin access"""
    admin_roles = [
        "Mwalimu Mkuu",
        "Mwalimu Mkuu Msaidizi",
        "Mtaaluma"
    ]
    return user_role in admin_roles

def is_primary_teacher(user_role: str) -> bool:
    """Check if role is a PRIMARY teacher"""
    return user_role == "Mwalimu"

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
# API Endpoints - PRIMARY
# ================================

# 1. GET endpoints - FIRST
@router.get("/", response_model=List[PastPaperResponse])
def get_primary_past_papers(
    subject: Optional[str] = Query(None, description="Chuja kwa somo"),
    exam_type: Optional[str] = Query(None, description="Chuja kwa aina ya mtihani"),
    year: Optional[int] = Query(None, description="Chuja kwa mwaka"),
    class_level: Optional[str] = Query(None, description="Chuja kwa darasa"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all PRIMARY past papers"""
    
    # 🔥 Get user's school
    school_id = getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="Kitambulisho cha shule kinahitajika")
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
    
    query = db.query(PastPaper).filter(PastPaper.school_id == school_id)
    
    if subject:
        query = query.filter(PastPaper.subject == subject)
    if exam_type:
        query = query.filter(PastPaper.exam_type == exam_type)
    if year:
        query = query.filter(PastPaper.year == year)
    if class_level:
        query = query.filter(PastPaper.class_level == class_level)
    
    papers = query.order_by(PastPaper.year.desc(), PastPaper.created_at.desc()).all()
    
    result = []
    for paper in papers:
        result.append(PastPaperResponse(
            id=paper.id,
            title=paper.title,
            subject=paper.subject,
            exam_type=paper.exam_type,
            year=paper.year,
            class_level=paper.class_level,
            school_level="primary",
            file_url=paper.file_url,
            file_name=paper.file_name,
            file_size=paper.file_size,
            description=paper.description,
            uploaded_by=paper.uploaded_by,
            school_name=school.name if school else "Shule ya Msingi",
            downloads=paper.downloads,
            created_at=paper.created_at
        ))
    
    return result

@router.get("/subjects")
def get_primary_past_paper_subjects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all subjects that have PRIMARY past papers"""
    
    # 🔥 Get user's school
    school_id = getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="Kitambulisho cha shule kinahitajika")
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
    
    subjects = db.query(PastPaper.subject).filter(
        PastPaper.school_id == school_id
    ).distinct().all()
    return {"subjects": [s[0] for s in subjects]}

@router.get("/years")
def get_primary_past_paper_years(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all years that have PRIMARY past papers"""
    
    # 🔥 Get user's school
    school_id = getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="Kitambulisho cha shule kinahitajika")
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
    
    years = db.query(PastPaper.year).filter(
        PastPaper.school_id == school_id
    ).distinct().order_by(PastPaper.year.desc()).all()
    return {"years": [y[0] for y in years]}

@router.get("/my-subjects")
def get_my_primary_uploadable_subjects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get subjects that the current PRIMARY teacher can upload past papers for"""
    
    # 🔥 Get user's school
    school_id = getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="Kitambulisho cha shule kinahitajika")
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    is_teacher = is_primary_teacher(user_role)
    is_admin = has_primary_admin_access(user_role)
    is_superadmin = isinstance(current_user, SuperAdmin)
    
    subjects = []
    
    if is_teacher:
        # 🔥 PRIMARY Teachers: only their assigned subjects
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
    elif is_admin or is_superadmin:
        # 🔥 PRIMARY Admin/Superadmin: all subjects in their school
        all_subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
        for subj in all_subjects:
            subjects.append({
                "id": subj.id,
                "name": subj.name,
                "code": subj.code
            })
    
    return {"subjects": subjects}

# 2. POST endpoints - SECOND
@router.post("/upload")
async def upload_primary_past_paper(
    title: str = Form(...),
    subject: str = Form(...),
    exam_type: str = Form(...),
    year: int = Form(...),
    class_level: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload a PRIMARY past paper - Teachers, Mtaaluma, Mwalimu Mkuu can upload"""
    
    print("=== UPLOAD PRIMARY PAST PAPER ===")
    print(f"User ID: {current_user.id}")
    print(f"Title: {title}")
    print(f"Subject: {subject}")
    
    # 🔥 Get user's school
    school_id = getattr(current_user, 'school_id', None)
    if not school_id:
        raise HTTPException(status_code=400, detail="Kitambulisho cha shule kinahitajika")
    
    # 🔥 Verify it's a primary school
    school = db.query(School).filter(School.id == school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio shule ya msingi")
    
    school_name = school.name if school else "Shule ya Msingi"
    
    # 🔥 Check permissions - PRIMARY ONLY
    user_role = get_role_string(getattr(current_user, 'role', None))
    is_teacher = is_primary_teacher(user_role)
    is_admin = has_primary_admin_access(user_role)
    is_superadmin = isinstance(current_user, SuperAdmin)
    
    if not is_teacher and not is_admin and not is_superadmin:
        raise HTTPException(
            status_code=403, 
            detail=f"Huna ruhusa. Jukumu lako: {user_role}. Inaruhusiwa: Mwalimu, Mtaaluma, Mwalimu Mkuu"
        )
    
    # 🔥 Get uploadable subjects for this teacher
    uploadable_subjects = []
    
    if is_teacher:
        teacher_subjects = db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == current_user.id
        ).all()
        for ts in teacher_subjects:
            subj = db.query(Subject).filter(Subject.id == ts.subject_id).first()
            if subj:
                uploadable_subjects.append(subj.name)
    else:
        # Admin/Superadmin can upload any subject in their school
        all_subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
        uploadable_subjects = [s.name for s in all_subjects]
    
    print(f"Uploadable subjects: {uploadable_subjects}")
    
    # Check if subject is allowed
    if subject not in uploadable_subjects:
        raise HTTPException(
            status_code=403, 
            detail=f"Unaweza kupakia tu masomo: {', '.join(uploadable_subjects[:10])}"
        )
    
    # Validate required fields
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Jina la mtihani linahitajika")
    if not subject or not subject.strip():
        raise HTTPException(status_code=400, detail="Somo linahitajika")
    if not exam_type or not exam_type.strip():
        raise HTTPException(status_code=400, detail="Aina ya mtihani inahitajika")
    if not year or year <= 0:
        raise HTTPException(status_code=400, detail="Mwaka sahihi unahitajika")
    if not class_level or not class_level.strip():
        raise HTTPException(status_code=400, detail="Kiwango cha darasa kinahitajika")
    
    # Validate file
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Faili inahitajika")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Aina ya faili hairuhusiwi. Inaruhusiwa: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Faili kubwa sana. Ukubwa wa juu: 10MB. Faili yako: {file_size / (1024 * 1024):.2f}MB"
        )
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"primary_{timestamp}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved to: {file_path}")
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Imeshindwa kuhifadhi faili: {str(e)}")
    
    # Create database record
    try:
        new_paper = PastPaper(
            title=title.strip(),
            subject=subject.strip(),
            exam_type=exam_type.strip(),
            year=year,
            class_level=class_level.strip(),
            school_level="primary",
            file_url=f"/uploads/primary/past_papers/{safe_filename}",
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
            "message": "Mtihani uliopita umepakiwa kikamilifu",
            "paper_id": new_paper.id,
            "file_name": new_paper.file_name,
            "school_name": school_name,
            "file_size": new_paper.file_size
        }
        
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Imeshindwa kuhifadhi kwenye database: {str(e)}")

# 3. GET endpoints with path parameters - THIRD
@router.get("/{paper_id}/download")
def download_primary_past_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Download a PRIMARY past paper file"""
    
    print(f"=== DOWNLOAD PRIMARY PAST PAPER ===")
    print(f"Paper ID: {paper_id}")
    
    # Get paper from database
    paper = db.query(PastPaper).filter(PastPaper.id == paper_id).first()
    if not paper:
        print(f"Paper not found: {paper_id}")
        raise HTTPException(status_code=404, detail="Mtihani uliopita haujapatikana")
    
    # 🔥 Verify it's a primary school paper
    school = db.query(School).filter(School.id == paper.school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio mtihani wa shule ya msingi")
    
    print(f"Paper found: {paper.title}")
    print(f"File URL in DB: {paper.file_url}")
    
    # Construct file path
    file_url = paper.file_url.lstrip('/')
    file_path = Path(file_url)
    
    print(f"Looking for file at: {file_path.absolute()}")
    
    # Check if file exists
    if not file_path.exists():
        print(f"File not found at: {file_path.absolute()}")
        alt_path = Path("uploads/primary/past_papers") / Path(paper.file_url).name
        print(f"Trying alternative path: {alt_path.absolute()}")
        
        if alt_path.exists():
            file_path = alt_path
            print(f"Found file at alternative path!")
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Faili haijapatikana kwenye server"
            )
    
    # Increment download count
    paper.downloads += 1
    db.commit()
    
    print(f"Sending file: {file_path.name}")
    
    return FileResponse(
        path=file_path,
        filename=paper.file_name,
        media_type='application/octet-stream',
        headers={
            "Content-Disposition": f"attachment; filename={paper.file_name}"
        }
    )

# 4. DELETE endpoint - FOURTH
@router.delete("/{paper_id}")
def delete_primary_past_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY past paper - Only Superadmin can delete"""
    
    paper = db.query(PastPaper).filter(PastPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Mtihani uliopita haujapatikana")
    
    # 🔥 Verify it's a primary school paper
    school = db.query(School).filter(School.id == paper.school_id).first()
    if school and school.school_level != "primary":
        raise HTTPException(status_code=400, detail="Hii sio mtihani wa shule ya msingi")
    
    # Only Superadmin can delete
    if not isinstance(current_user, SuperAdmin):
        raise HTTPException(
            status_code=403, 
            detail="Msimamizi Mkuu pekee ndiye anaweza kufuta mitihani iliyopita"
        )
    
    # Delete file from disk
    file_path = Path(paper.file_url.lstrip('/'))
    if file_path.exists():
        file_path.unlink()
    
    db.delete(paper)
    db.commit()
    
    return {"message": "Mtihani uliopita umefutwa kikamilifu"}