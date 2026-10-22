from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.student import Student
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from pydantic import BaseModel
from app.core.security import get_current_user
import logging

# ✅ IMPORT HELPER MPYA
from app.api.v1.students.import_helper import (
    parse_excel_students,
    import_students_to_db,
    create_import_template,
)

logger = logging.getLogger(__name__)

# ================================
# Pydantic Schemas
# ================================

class StudentCreate(BaseModel):
    name: str
    sex: str
    father_name: str
    father_phone: str
    school_id: int
    class_id: Optional[int] = None
    stream_id: Optional[int] = None
    roll_number: Optional[str] = None
    address: Optional[str] = None
    health_info: Optional[str] = None

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    sex: Optional[str] = None
    father_name: Optional[str] = None
    father_phone: Optional[str] = None
    school_id: Optional[int] = None
    class_id: Optional[int] = None
    stream_id: Optional[int] = None
    roll_number: Optional[str] = None
    address: Optional[str] = None
    health_info: Optional[str] = None

class StudentResponse(BaseModel):
    id: int
    name: str
    sex: str
    roll_number: Optional[str]
    school_id: int
    class_id: Optional[int]
    stream_id: Optional[int]
    father_name: str
    father_phone: str
    health_info: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        from_attributes = True

router = APIRouter()

# ============================================================
# HELPER FUNCTION - IMPROVED (Case-insensitive)
# ============================================================
def _get_user_role(user) -> str:
    """Get user role with proper normalization (case-insensitive)"""
    role = None
    
    if hasattr(user, 'role'):
        role = user.role
    elif hasattr(user, 'user_type'):
        role = user.user_type
    elif hasattr(user, 'user_role'):
        role = user.user_role
    
    if role is not None:
        if hasattr(role, 'value'):
            role_str = role.value
        else:
            role_str = str(role)
        
        role_upper = role_str.upper()
        
        if role_upper == "TEACHER":
            return "Teacher"
        elif role_upper == "ACADEMIC":
            return "Academic"
        elif role_upper == "HEADMASTER":
            return "Headmaster"
        elif role_upper == "HEADMISTRESS":
            return "Headmistress"
        elif role_upper == "SECOND MASTER":
            return "Second Master"
        elif role_upper == "SECOND MISTRESS":
            return "Second Mistress"
        elif role_upper == "ACCOUNTANT":
            return "Accountant"
        elif role_upper == "MWALIMU":
            return "Mwalimu"
        elif role_upper == "MTAALUMA":
            return "Mtaaluma"
        elif role_upper == "MWALIMU MKUU":
            return "Mwalimu Mkuu"
        elif role_upper == "MWALIMU MKUU MSAIDIZI":
            return "Mwalimu Mkuu Msaidizi"
        else:
            return role_str
    
    class_name = type(user).__name__
    if class_name == "Teacher":
        return "Teacher"
    elif class_name == "SuperAdmin":
        return "Superadmin"
    
    return "Unknown"


# ============================================================
# ✅ ENDPOINT 0: IMPORT TEMPLATE (LAZIMA IWE KWANZA!)
# ============================================================
@router.get("/students/import-template")
async def download_import_template_secondary(
    current_user = Depends(get_current_user),
):
    """
    ✅ Pakua template ya Excel (SECONDARY)
    """
    buffer = create_import_template(level="secondary")
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=student_import_template_secondary.xlsx"
        }
    )


# ============================================================
# ✅ ENDPOINT 0.5: IMPORT EXCEL (LAZIMA IWE KWANZA!)
# ============================================================
@router.post("/students/import-excel")
async def import_students_excel_secondary(
    school_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    ✅ Import wanafunzi wa SECONDARY kutoka Excel
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "File lazima iwe Excel (.xlsx au .xls)")
    
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "File ni kubwa sana (max 10MB)")
    
    students_data = parse_excel_students(contents)
    
    result = import_students_to_db(
        students_data=students_data,
        school_id=school_id,
        db=db,
        SchoolClass=SchoolClass,
        Stream=Stream,
        Student=Student,
        level="secondary",
    )
    
    return {"success": True, "level": "secondary", **result}


# ============================================================
# ENDPOINT 1: MY STUDENTS (MUST BE FIRST - before {student_id})
# ============================================================
@router.get("/students/my-students")
def get_my_students(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.teacher import Teacher
    from app.models.teacher_subject import TeacherSubject
    from app.models.superadmin import SuperAdmin
    from app.models.student import Student
    from app.models.school_class import SchoolClass
    from app.models.stream import Stream
    from app.models.subject import Subject
    
    try:
        user_role = _get_user_role(current_user)
        user_id = getattr(current_user, 'id', None)
        
        logger.info(f"=== get_my_students called ===")
        logger.info(f"User role: {user_role}")
        logger.info(f"User ID: {user_id}")
        
        if isinstance(current_user, SuperAdmin):
            students = db.query(Student).all()
            result = []
            for s in students:
                class_obj = db.query(SchoolClass).filter(SchoolClass.id == s.class_id).first()
                class_name = class_obj.name if class_obj else f"Class {s.class_id}"
                stream_obj = db.query(Stream).filter(Stream.id == s.stream_id).first()
                stream_name = stream_obj.name if stream_obj else ""
                display_class = f"{class_name} {stream_name}".strip()
                result.append({
                    "id": s.id,
                    "name": s.name,
                    "sex": s.sex,
                    "roll_number": s.roll_number,
                    "school_id": s.school_id,
                    "class_id": s.class_id,
                    "class_name": display_class,
                    "stream_id": s.stream_id,
                    "stream_name": stream_name,
                    "subject_id": 0,
                    "subject_name": "All Subjects",
                    "father_name": s.father_name,
                    "father_phone": s.father_phone,
                    "health_info": s.health_info,
                    "address": s.address
                })
            return result
        
        staff_roles = ["Teacher", "Academic", "Headmaster", "Headmistress", "Second Master", "Second Mistress", 
                       "Mwalimu", "Mtaaluma", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi"]
        
        if user_role in staff_roles or isinstance(current_user, Teacher):
            assignments = db.query(TeacherSubject).filter(
                TeacherSubject.teacher_id == user_id
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
        
        return []
        
    except Exception as e:
        logger.error(f"ERROR in get_my_students: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


# ============================================================
# ENDPOINT 2: GET SINGLE STUDENT
# ============================================================
@router.get("/students/{student_id}")
def get_student(
    student_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.school_class import SchoolClass
    from app.models.stream import Stream
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    class_name = None
    if student.class_id:
        school_class = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        class_name = school_class.name if school_class else None
    
    stream_name = None
    if student.stream_id:
        stream = db.query(Stream).filter(Stream.id == student.stream_id).first()
        stream_name = stream.name if stream else None
    
    display_class = class_name if class_name else ""
    if stream_name:
        display_class = f"{class_name} {stream_name}" if class_name else stream_name
    
    return {
        "id": student.id,
        "name": student.name,
        "sex": student.sex,
        "roll_number": student.roll_number,
        "school_id": student.school_id,
        "class_id": student.class_id,
        "class_name": display_class,
        "stream_id": student.stream_id,
        "stream_name": stream_name,
        "father_name": student.father_name,
        "father_phone": student.father_phone,
        "address": student.address,
        "health_info": student.health_info,
        "enrollment_date": student.enrollment_date
    }


# ============================================================
# ENDPOINT 3: GET ALL STUDENTS
# ============================================================
@router.get("/students")
def get_all_students(
    school_id: Optional[int] = Query(None, description="Filter by school"),
    class_id: Optional[int] = Query(None, description="Filter by class"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.superadmin import SuperAdmin
    from app.models.school_class import SchoolClass
    from app.models.stream import Stream
    
    user_role = _get_user_role(current_user)
    
    if isinstance(current_user, SuperAdmin):
        query = db.query(
            Student.id,
            Student.name,
            Student.sex,
            Student.roll_number,
            Student.school_id,
            Student.class_id,
            Student.stream_id,
            Student.father_name,
            Student.father_phone,
            Student.address,
            Student.health_info,
            Student.enrollment_date,
            SchoolClass.name.label("class_name"),
            Stream.name.label("stream_name")
        ).join(
            SchoolClass, Student.class_id == SchoolClass.id, isouter=True
        ).join(
            Stream, Student.stream_id == Stream.id, isouter=True
        )
        if school_id:
            query = query.filter(Student.school_id == school_id)
        if class_id:
            query = query.filter(Student.class_id == class_id)
        students = query.all()
        
        return [{
            "id": s.id,
            "name": s.name,
            "sex": s.sex,
            "roll_number": s.roll_number,
            "school_id": s.school_id,
            "class_id": s.class_id,
            "class_name": s.class_name or "",
            "stream_id": s.stream_id,
            "stream_name": s.stream_name or "",
            "father_name": s.father_name,
            "father_phone": s.father_phone,
            "address": s.address,
            "health_info": s.health_info,
            "enrollment_date": s.enrollment_date
        } for s in students]
    
    admin_roles = [
        "Headmaster", "Headmistress", "Second Master", "Second Mistress", "Academic",
        "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"
    ]
    
    if user_role in admin_roles:
        if hasattr(current_user, 'school_id') and current_user.school_id:
            query = db.query(
                Student.id,
                Student.name,
                Student.sex,
                Student.roll_number,
                Student.school_id,
                Student.class_id,
                Student.stream_id,
                Student.father_name,
                Student.father_phone,
                Student.address,
                Student.health_info,
                Student.enrollment_date,
                SchoolClass.name.label("class_name"),
                Stream.name.label("stream_name")
            ).join(
                SchoolClass, Student.class_id == SchoolClass.id, isouter=True
            ).join(
                Stream, Student.stream_id == Stream.id, isouter=True
            ).filter(Student.school_id == current_user.school_id)
            
            if class_id:
                query = query.filter(Student.class_id == class_id)
            students = query.all()
            
            return [{
                "id": s.id,
                "name": s.name,
                "sex": s.sex,
                "roll_number": s.roll_number,
                "school_id": s.school_id,
                "class_id": s.class_id,
                "class_name": s.class_name or "",
                "stream_id": s.stream_id,
                "stream_name": s.stream_name or "",
                "father_name": s.father_name,
                "father_phone": s.father_phone,
                "address": s.address,
                "health_info": s.health_info,
                "enrollment_date": s.enrollment_date
            } for s in students]
    
    if user_role == "Teacher" or user_role == "Mwalimu":
        raise HTTPException(
            status_code=403, 
            detail="Teachers should use /students/my-students endpoint"
        )
    
    raise HTTPException(status_code=403, detail=f"Not authorized. Your role: {user_role}")


# ============================================================
# ENDPOINT 4: CREATE STUDENT
# ============================================================
@router.post("/students", response_model=StudentResponse)
def create_student(
    student_data: StudentCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.superadmin import SuperAdmin
    
    user_role = _get_user_role(current_user)
    
    create_roles = ["Headmaster", "Headmistress", "Academic", "Mwalimu Mkuu", "Mtaaluma"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in create_roles:
        raise HTTPException(status_code=403, detail="Not authorized to create students")
    
    school = db.query(School).filter(School.id == student_data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if student_data.roll_number:
        existing = db.query(Student).filter(
            Student.roll_number == student_data.roll_number,
            Student.class_id == student_data.class_id,
            Student.school_id == student_data.school_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Roll number '{student_data.roll_number}' already exists")
    
    new_student = Student(
        name=student_data.name,
        sex=student_data.sex,
        father_name=student_data.father_name,
        father_phone=student_data.father_phone,
        address=student_data.address,
        health_info=student_data.health_info,
        school_id=student_data.school_id,
        class_id=student_data.class_id,
        stream_id=student_data.stream_id,
        roll_number=student_data.roll_number
    )
    
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


# ============================================================
# ENDPOINT 5: UPDATE STUDENT
# ============================================================
@router.put("/students/{student_id}")
def update_student(
    student_id: int, 
    student_data: StudentUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.superadmin import SuperAdmin
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    user_role = _get_user_role(current_user)
    
    update_roles = ["Headmaster", "Headmistress", "Academic", "Mwalimu Mkuu", "Mtaaluma"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in update_roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = student_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(student, key, value)
    
    db.commit()
    db.refresh(student)
    return {"message": "Student updated successfully", "student": student}


# ============================================================
# ENDPOINT 6: DELETE STUDENT
# ============================================================
@router.delete("/students/{student_id}")
def delete_student(
    student_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.superadmin import SuperAdmin
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    user_role = _get_user_role(current_user)
    
    delete_roles = ["Headmaster", "Headmistress", "Academic", "Mwalimu Mkuu", "Mtaaluma"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in delete_roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}