from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.student import Student
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.teacher_subject import TeacherSubject
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from app.models.subject import Subject
from pydantic import BaseModel
from app.core.security import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ================================
# Helper function - PRIMARY
# ================================
def get_role_string(role):
    """Convert role to string"""
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

def get_user_school_id(current_user) -> Optional[int]:
    """Get school_id from current user"""
    if hasattr(current_user, 'school_id') and current_user.school_id:
        return current_user.school_id
    return None

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

# ================================
# Pydantic Schemas - PRIMARY (IMESAHIHISHWA!)
# ================================

class StudentCreate(BaseModel):
    name: str
    sex: str
    father_name: str
    father_phone: str
    class_id: Optional[int] = None
    stream_id: Optional[int] = None
    roll_number: Optional[str] = None
    address: Optional[str] = None
    health_info: Optional[str] = None
    mother_name: Optional[str] = None
    mother_phone: Optional[str] = None

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    sex: Optional[str] = None
    father_name: Optional[str] = None
    father_phone: Optional[str] = None
    class_id: Optional[int] = None
    stream_id: Optional[int] = None
    roll_number: Optional[str] = None
    address: Optional[str] = None
    health_info: Optional[str] = None
    mother_name: Optional[str] = None
    mother_phone: Optional[str] = None

# 🔥🔥🔥 BADILISHA HII - ONGEZA class_name NA stream_name! 🔥🔥🔥
class StudentResponse(BaseModel):
    id: int
    name: str
    sex: str
    roll_number: Optional[str]
    school_id: int
    class_id: Optional[int]
    class_name: Optional[str] = None      # 🔥 ONGEZA HII!
    stream_id: Optional[int]
    stream_name: Optional[str] = None     # 🔥 ONGEZA HII!
    father_name: str
    father_phone: str
    mother_name: Optional[str] = None
    mother_phone: Optional[str] = None
    health_info: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ================================
# API Endpoints - PRIMARY
# ================================

router = APIRouter(prefix="/primary/students", tags=["Primary Students"])

# ============================================================
# 🔥 1. STATIC ROUTE: MY STUDENTS (KWANZA!)
# ============================================================
@router.get("/my-students")
def get_my_primary_students(
    class_id: Optional[int] = Query(None, description="Filter by class ID"),
    stream_id: Optional[int] = Query(None, description="Filter by stream ID"),
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get students for PRIMARY teachers only - WITH FILTERS!"""
    
    try:
        user_role = get_role_string(getattr(current_user, 'role', None))
        user_id = getattr(current_user, 'id', None)
        
        logger.info(f"get_my_primary_students - Role: {user_role}, ID: {user_id}")
        logger.info(f"Filters - class_id: {class_id}, stream_id: {stream_id}, subject_id: {subject_id}")
        
        # SUPERADMIN
        if isinstance(current_user, SuperAdmin):
            students = db.query(Student).all()
            result = []
            for s in students:
                school = db.query(School).filter(School.id == s.school_id).first()
                if school and school.school_level != "primary":
                    continue
                    
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
                    "subject_name": "Masomo Yote",
                    "father_name": s.father_name,
                    "father_phone": s.father_phone,
                    "health_info": s.health_info,
                    "address": s.address
                })
            return result
        
        # FOR PRIMARY TEACHERS AND STAFF
        primary_staff_roles = ["Mwalimu", "Mtaaluma", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi"]
        
        if user_role in primary_staff_roles or isinstance(current_user, Teacher):
            school_id = get_user_school_id(current_user)
            if not school_id:
                return []
            
            # Verify primary school
            verify_primary_school(school_id, db)
            
            # 🔥 GET ASSIGNMENTS - FILTER BY SUBJECT IF PROVIDED
            query = db.query(TeacherSubject).filter(
                TeacherSubject.teacher_id == user_id
            )
            
            if subject_id:
                query = query.filter(TeacherSubject.subject_id == subject_id)
            
            assignments = query.all()
            
            if not assignments:
                return []
            
            result = []
            
            for assignment in assignments:
                # 🔥 SKIP IKIWA CLASS HAIENDANI NA FILTER
                if class_id and assignment.class_id != class_id:
                    continue
                
                # 🔥 SKIP IKIWA STREAM HAIENDANI NA FILTER
                if stream_id and assignment.stream_id != stream_id:
                    continue
                
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
                    Student.stream_id == assignment.stream_id,
                    Student.school_id == school_id
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
        logger.error(f"ERROR in get_my_primary_students: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


# ============================================================
# 🔥 2. GET ALL STUDENTS - PRIMARY (IMEBORESHA!)
# ============================================================
@router.get("")
def get_primary_students(
    class_id: Optional[int] = Query(None, description="Filter by class"),
    stream_id: Optional[int] = Query(None, description="Filter by stream"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all students for PRIMARY school only - WITH class_name and stream_name!"""
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    school_id = get_user_school_id(current_user)
    
    if not school_id:
        raise HTTPException(
            status_code=400, 
            detail="No school associated with this user"
        )
    
    verify_primary_school(school_id, db)
    
    if not isinstance(current_user, SuperAdmin) and not has_primary_admin_access(user_role):
        if is_primary_teacher(user_role):
            raise HTTPException(
                status_code=403, 
                detail="Walimu wanapaswa kutumia /primary/students/my-students"
            )
        raise HTTPException(
            status_code=403, 
            detail=f"Huna ruhusa. Jukumu lako: {user_role}."
        )
    
    # 🔥🔥🔥 BADILISHA HII - JOIN CLASSES NA STREAMS! 🔥🔥🔥
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
        Student.mother_name,
        Student.mother_phone,
        Student.health_info,
        Student.address,
        Student.enrollment_date,
        SchoolClass.name.label("class_name"),  # 🔥 ONGEZA HII!
        Stream.name.label("stream_name")       # 🔥 ONGEZA HII!
    ).join(
        SchoolClass, Student.class_id == SchoolClass.id, isouter=True
    ).join(
        Stream, Student.stream_id == Stream.id, isouter=True
    ).filter(
        Student.school_id == school_id
    )
    
    if class_id:
        query = query.filter(Student.class_id == class_id)
    if stream_id:
        query = query.filter(Student.stream_id == stream_id)
    
    results = query.all()
    
    # 🔥🔥🔥 BADILISHA RETURN - JAZA CLASS_NAME NA STREAM_NAME! 🔥🔥🔥
    students = []
    for row in results:
        students.append({
            "id": row.id,
            "name": row.name,
            "sex": row.sex,
            "roll_number": row.roll_number,
            "school_id": row.school_id,
            "class_id": row.class_id,
            "class_name": row.class_name or "-",  # 🔥 IMEJAZWA!
            "stream_id": row.stream_id,
            "stream_name": row.stream_name or "-",  # 🔥 IMEJAZWA!
            "father_name": row.father_name,
            "father_phone": row.father_phone,
            "mother_name": row.mother_name,
            "mother_phone": row.mother_phone,
            "health_info": row.health_info,
            "address": row.address,
            "enrollment_date": row.enrollment_date
        })
    
    return students


# ============================================================
# 🔥 3. GET SINGLE STUDENT - PRIMARY (IMEBORESHA!)
# ============================================================
@router.get("/{student_id}")
def get_primary_student(
    student_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single PRIMARY student by ID - WITH class_name and stream_name!"""
    
    # 🔥🔥🔥 BADILISHA HII - JOIN CLASSES NA STREAMS! 🔥🔥🔥
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
    
    # 🔥🔥🔥 RUDISHA DATA KAMILI! 🔥🔥🔥
    return {
        "id": result.id,
        "name": result.name,
        "sex": result.sex,
        "roll_number": result.roll_number,
        "school_id": result.school_id,
        "class_id": result.class_id,
        "class_name": result.class_name or "-",
        "stream_id": result.stream_id,
        "stream_name": result.stream_name or "-",
        "father_name": result.father_name,
        "father_phone": result.father_phone,
        "mother_name": result.mother_name,
        "mother_phone": result.mother_phone,
        "health_info": result.health_info,
        "address": result.address,
        "enrollment_date": result.enrollment_date
    }


# ============================================================
# 🔥 4. CREATE STUDENT - PRIMARY (IMEBORESHA!)
# ============================================================
@router.post("", status_code=status.HTTP_201_CREATED)
def create_primary_student(
    student_data: StudentCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new PRIMARY student"""
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    create_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in create_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Huna ruhusa ya kuongeza wanafunzi. Jukumu lako: {user_role}"
        )
    
    school_id = get_user_school_id(current_user)
    if not school_id:
        raise HTTPException(status_code=400, detail="No school associated with this user")
    
    verify_primary_school(school_id, db)
    
    if student_data.roll_number:
        existing = db.query(Student).filter(
            Student.roll_number == student_data.roll_number,
            Student.class_id == student_data.class_id,
            Student.school_id == school_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Roll number '{student_data.roll_number}' already exists"
            )
    
    if student_data.class_id:
        school_class = db.query(SchoolClass).filter(
            SchoolClass.id == student_data.class_id,
            SchoolClass.school_id == school_id
        ).first()
        if not school_class:
            raise HTTPException(status_code=404, detail="Class not found")
    
    if student_data.stream_id:
        stream = db.query(Stream).filter(
            Stream.id == student_data.stream_id,
            Stream.school_id == school_id
        ).first()
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")
    
    new_student = Student(
        name=student_data.name,
        sex=student_data.sex,
        father_name=student_data.father_name,
        father_phone=student_data.father_phone,
        mother_name=student_data.mother_name,
        mother_phone=student_data.mother_phone,
        address=student_data.address,
        health_info=student_data.health_info,
        school_id=school_id,
        class_id=student_data.class_id,
        stream_id=student_data.stream_id,
        roll_number=student_data.roll_number,
        enrollment_date=datetime.now()
    )
    
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    
    logger.info(f"✅ Student created: {new_student.name} (ID: {new_student.id}) in school {school_id}")
    
    # 🔥 RUDISHA KWA CLASS_NAME NA STREAM_NAME
    class_name = None
    stream_name = None
    if new_student.class_id:
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == new_student.class_id).first()
        class_name = class_obj.name if class_obj else None
    if new_student.stream_id:
        stream_obj = db.query(Stream).filter(Stream.id == new_student.stream_id).first()
        stream_name = stream_obj.name if stream_obj else None
    
    return {
        "id": new_student.id,
        "name": new_student.name,
        "sex": new_student.sex,
        "roll_number": new_student.roll_number,
        "school_id": new_student.school_id,
        "class_id": new_student.class_id,
        "class_name": class_name or "-",
        "stream_id": new_student.stream_id,
        "stream_name": stream_name or "-",
        "father_name": new_student.father_name,
        "father_phone": new_student.father_phone,
        "mother_name": new_student.mother_name,
        "mother_phone": new_student.mother_phone,
        "health_info": new_student.health_info,
        "address": new_student.address,
        "enrollment_date": new_student.enrollment_date
    }


# ============================================================
# 🔥 5. UPDATE STUDENT - PRIMARY
# ============================================================
@router.put("/{student_id}")
def update_primary_student(
    student_id: int, 
    student_data: StudentUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a PRIMARY student"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    verify_primary_school(student.school_id, db)
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    update_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in update_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Huna ruhusa ya kusasisha wanafunzi. Jukumu lako: {user_role}"
        )
    
    school_id = get_user_school_id(current_user)
    if school_id and student.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update students in your own school"
        )
    
    update_data = student_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(student, key, value)
    
    db.commit()
    db.refresh(student)
    
    return {"message": "Student updated successfully", "student": student}


# ============================================================
# 🔥 6. DELETE STUDENT - PRIMARY
# ============================================================
@router.delete("/{student_id}")
def delete_primary_student(
    student_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a PRIMARY student"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    verify_primary_school(student.school_id, db)
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    delete_roles = ["Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi", "Mtaaluma"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in delete_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Huna ruhusa ya kufuta wanafunzi. Jukumu lako: {user_role}"
        )
    
    school_id = get_user_school_id(current_user)
    if school_id and student.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete students in your own school"
        )
    
    db.delete(student)
    db.commit()
    
    return {"message": "Student deleted successfully"}