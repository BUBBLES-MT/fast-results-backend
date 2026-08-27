# app/api/v1/schools.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.models.school import School, SchoolStatus
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from pydantic import BaseModel, validator
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🔥 SUBSCRIPTION PLANS - MPYA!
# ============================================================
SUBSCRIPTION_PLANS = {
    "monthly": 30,
    "quarterly": 90,
    "semester": 180,
    "annual": 365
}

# ============================================================
# Pydantic Schemas
# ============================================================

class SchoolCreate(BaseModel):
    name: str
    school_type: str = "secondary"
    school_level: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    admin_email: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    
    @validator('school_type')
    def validate_school_type(cls, v):
        valid_types = ["primary", "secondary", "advanced"]
        if v not in valid_types:
            raise ValueError(f"school_type must be one of: {valid_types}")
        return v
    
    @validator('school_level')
    def validate_school_level(cls, v):
        if v is None:
            return v
        valid_levels = ["primary", "secondary", "advanced"]
        if v not in valid_levels:
            raise ValueError(f"school_level must be one of: {valid_levels}")
        return v

class SchoolResponse(BaseModel):
    id: int
    name: str
    school_type: str
    school_level: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    admin_email: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    is_active: bool
    status: str
    subscription_plan: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    is_locked_by_superadmin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    school_type: Optional[str] = None
    school_level: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    admin_email: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    is_active: Optional[bool] = None

# ============================================================
# 🔥🔥🔥 SUPERADMIN SCHOOL MANAGEMENT SCHEMAS 🔥🔥🔥
# ============================================================

class SuperAdminSchoolUpdate(BaseModel):
    """Kwa ajili ya superadmin ku-update shule"""
    is_active: Optional[bool] = None
    is_locked_by_superadmin: Optional[bool] = None
    subscription_plan: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    status: Optional[str] = None

class SuperAdminSubscriptionExtend(BaseModel):
    """Kwa ajili ya superadmin ku-extend subscription"""
    plan: str = "monthly"  # monthly, quarterly, semester, annual
    days: Optional[int] = None  # Ikiwa haijabainishwa, tumia plan

# ============================================================
# Helper Functions
# ============================================================

def format_school_response(school: School) -> dict:
    """Format school object for response"""
    return {
        "id": school.id,
        "name": school.name,
        "school_type": school.school_type,
        "school_level": school.school_level or school.school_type,
        "address": school.address,
        "phone": school.phone,
        "email": school.email,
        "admin_email": getattr(school, 'admin_email', None),
        "region": getattr(school, 'region', None),
        "district": getattr(school, 'district', None),
        "is_active": school.is_active,
        "status": school.status if hasattr(school, 'status') else "active",
        "subscription_plan": getattr(school, 'subscription_plan', None),
        "subscription_expires_at": getattr(school, 'subscription_expires_at', None),
        "is_locked_by_superadmin": getattr(school, 'is_locked_by_superadmin', False),
        "created_at": school.created_at
    }

def get_headmaster_roles(school_level: str) -> List[str]:
    """Pata roles za headmaster kulingana na school level"""
    if school_level == "primary":
        return ["Mwalimu Mkuu"]
    elif school_level == "secondary":
        return ["Headmaster", "Headmistress"]
    elif school_level == "advanced":
        return ["Headmaster", "Headmistress"]
    else:
        return ["Mwalimu Mkuu", "Headmaster", "Headmistress"]

def get_teacher_roles(school_level: str) -> List[str]:
    """Pata roles za teacher kulingana na school level"""
    if school_level == "primary":
        return ["Mwalimu", "Mtaaluma"]
    elif school_level == "secondary":
        return ["Teacher", "Academic"]
    elif school_level == "advanced":
        return ["Teacher", "Academic"]
    else:
        return ["Mwalimu", "Teacher", "Mtaaluma", "Academic"]

def get_subscription_days(plan: str) -> int:
    """Get number of days for a subscription plan"""
    return SUBSCRIPTION_PLANS.get(plan.lower(), 30)

# ============================================================
# API Endpoints
# ============================================================

router = APIRouter()

# ============================================================
# 🔥 GET ALL SCHOOLS - PUBLIC ACCESS
# ============================================================
@router.get("/schools", response_model=List[SchoolResponse])
def get_all_schools(
    school_type: Optional[str] = Query(None, description="Filter by school type: primary, secondary, advanced"),
    school_level: Optional[str] = Query(None, description="Filter by school level: primary, secondary, advanced"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by school name"),
    db: Session = Depends(get_db)
):
    """
    Get all schools - COMPLETELY PUBLIC ACCESS.
    Inatumika kwenye login page kwa ajili ya registration.
    Hakuna token required.
    """
    
    try:
        query = db.query(School)
        
        if school_type:
            query = query.filter(School.school_type == school_type)
        if school_level:
            query = query.filter(School.school_level == school_level)
        if is_active is not None:
            query = query.filter(School.is_active == is_active)
        if search:
            query = query.filter(School.name.ilike(f"%{search}%"))
        
        schools = query.order_by(School.name).all()
        result = [format_school_response(school) for school in schools]
        
        logger.info(f"✅ Returned {len(result)} schools (public access)")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error getting schools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schools: {str(e)}"
        )

# ============================================================
# 🔥 GET SINGLE SCHOOL - Requires authentication
# ============================================================
@router.get("/schools/{school_id}", response_model=SchoolResponse)
def get_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a single school by ID - Requires authentication"""
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    return format_school_response(school)

# ============================================================
# 🔥 CREATE SCHOOL - Requires authentication
# ============================================================
@router.post("/schools", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
def create_school(
    school_data: SchoolCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new school - Requires authentication"""
    
    existing = db.query(School).filter(School.name == school_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School with this name already exists"
        )
    
    school_level = school_data.school_level or school_data.school_type or "secondary"
    
    # ✅ Kwa shule mpya, weka subscription ya siku 30 (kipindi cha majaribio)
    now = datetime.now()
    trial_expiry = now + timedelta(days=30)
    
    new_school = School(
        name=school_data.name,
        school_type=school_data.school_type or "secondary",
        school_level=school_level,
        address=school_data.address,
        phone=school_data.phone,
        email=school_data.email,
        admin_email=school_data.admin_email,
        region=school_data.region,
        district=school_data.district,
        is_active=True,
        status="active",
        subscription_plan="monthly",
        subscription_expires_at=trial_expiry,
        is_locked_by_superadmin=False
    )
    
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    
    logger.info(f"✅ School created: {new_school.name} (ID: {new_school.id}) - Trial expires: {trial_expiry}")
    return format_school_response(new_school)

# ============================================================
# 🔥 UPDATE SCHOOL - Requires authentication
# ============================================================
@router.put("/schools/{school_id}")
def update_school(
    school_id: int,
    school_data: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a school - Requires authentication"""
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # Check permissions
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    is_superadmin = user_role == "superadmin" or user_role == "Superadmin"
    
    if not is_superadmin:
        if hasattr(current_user, 'school_id') and current_user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own school"
            )
    
    update_data = school_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(school, key, value)
    
    if 'school_type' in update_data and update_data['school_type']:
        if 'school_level' not in update_data or not update_data['school_level']:
            school.school_level = update_data['school_type']
    
    db.commit()
    db.refresh(school)
    
    logger.info(f"✅ School updated: {school.name} (ID: {school.id})")
    return {"message": "School updated successfully", "school": format_school_response(school)}

# ============================================================
# 🔥 DELETE SCHOOL - Requires authentication
# ============================================================
@router.delete("/schools/{school_id}")
def delete_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a school - Requires authentication"""
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # Check permissions
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    is_superadmin = user_role == "superadmin" or user_role == "Superadmin"
    
    if not is_superadmin:
        if hasattr(current_user, 'school_id') and current_user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own school"
            )
    
    db.delete(school)
    db.commit()
    
    logger.info(f"✅ School deleted: {school.name} (ID: {school.id})")
    return {"message": "School deleted successfully"}

# ============================================================
# 🔥 GET SCHOOL LEVELS - PUBLIC
# ============================================================
@router.get("/school-levels")
def get_school_levels(
    db: Session = Depends(get_db)
):
    """Get list of available school levels - PUBLIC"""
    return {"levels": ["primary", "secondary", "advanced"]}

# ============================================================
# 🔥🔥🔥 SUPERADMIN - ACTIVATE/DEACTIVATE SCHOOL 🔥🔥🔥
# ============================================================
@router.put("/superadmin/schools/{school_id}/toggle-active")
def toggle_school_active(
    school_id: int,
    is_active: bool = Query(..., description="True to activate, False to deactivate"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Activate or deactivate a school manually.
    
    Hii inaruhusu superadmin kufungua shule (activate) au kufunga (deactivate)
    hata kama subscription imeisha au haijalipwa.
    
    Inatumika wakati:
    - Mtandao wa malipo haufanyi kazi
    - Shule imelipa lakini system haijasawazisha
    - Kwa ajili ya majaribio
    - Kwa sababu nyingine za dharura
    """
    
    # ============================================================
    # 🔥 1. HAKIKISHA NI SUPERADMIN
    # ============================================================
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    
    is_superadmin = user_role == "superadmin" or user_role == "Superadmin"
    if not is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can manually toggle school status"
        )
    
    # ============================================================
    # 🔥 2. HAKIKISHA SHULE IPO
    # ============================================================
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # ============================================================
    # 🔥 3. BADILISHA STATUS
    # ============================================================
    old_status = school.is_active
    school.is_active = is_active
    
    if is_active:
        school.status = "active"
        # ✅ Ikiwa imeisha, weka subscription mpya (siku 30 za majaribio)
        if not school.subscription_expires_at or school.subscription_expires_at < datetime.now():
            school.subscription_expires_at = datetime.now() + timedelta(days=30)
            school.subscription_plan = "monthly"
        # ✅ Ondoa lock ikiwa ipo
        school.is_locked_by_superadmin = False
    else:
        school.status = "inactive"
        # ✅ Ikiwa inafungwa, weka lock
        school.is_locked_by_superadmin = True
    
    db.commit()
    db.refresh(school)
    
    action = "activated" if is_active else "deactivated"
    logger.info(f"🔑 Superadmin {current_user.name} {action} school: {school.name} (ID: {school.id})")
    
    return {
        "message": f"School '{school.name}' has been {action} successfully",
        "school_id": school.id,
        "school_name": school.name,
        "is_active": school.is_active,
        "status": school.status,
        "subscription_expires_at": school.subscription_expires_at,
        "is_locked_by_superadmin": school.is_locked_by_superadmin,
        "action": action,
        "performed_by": current_user.name
    }

# ============================================================
# 🔥🔥🔥 SUPERADMIN - EXTEND SUBSCRIPTION MANUALLY 🔥🔥🔥
# ============================================================
@router.post("/superadmin/schools/{school_id}/extend-subscription")
def extend_subscription_manual(
    school_id: int,
    request: SuperAdminSubscriptionExtend,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Manually extend school subscription.
    
    Superadmin anaweza kuongeza muda wa subscription ya shule
    bila kutumia mfumo wa malipo.
    
    Plans zilizopo:
    - monthly: siku 30
    - quarterly: siku 90
    - semester: siku 180
    - annual: siku 365
    """
    
    # ============================================================
    # 🔥 1. HAKIKISHA NI SUPERADMIN
    # ============================================================
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    
    is_superadmin = user_role == "superadmin" or user_role == "Superadmin"
    if not is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can manually extend subscription"
        )
    
    # ============================================================
    # 🔥 2. HAKIKISHA SHULE IPO
    # ============================================================
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # ============================================================
    # 🔥 3. HESABU IDADI YA SIKU
    # ============================================================
    days = request.days or get_subscription_days(request.plan)
    
    # ============================================================
    # 🔥 4. WEKA TAREHE MPYA YA MALIPO
    # ============================================================
    now = datetime.now()
    
    # Ikiwa subscription imeisha, anza kutoka sasa
    if not school.subscription_expires_at or school.subscription_expires_at < now:
        new_expiry = now + timedelta(days=days)
    else:
        # Ikiwa bado ina muda, ongeza kwenye tarehe iliyopo
        new_expiry = school.subscription_expires_at + timedelta(days=days)
    
    # ============================================================
    # 🔥 5. SASISHA SCHOOL
    # ============================================================
    school.subscription_plan = request.plan
    school.subscription_expires_at = new_expiry
    school.is_active = True
    school.status = "active"
    school.is_locked_by_superadmin = False
    
    db.commit()
    db.refresh(school)
    
    logger.info(f"🔑 Superadmin {current_user.name} extended subscription for {school.name} by {days} days. New expiry: {new_expiry}")
    
    return {
        "message": f"Subscription extended by {days} days",
        "school_id": school.id,
        "school_name": school.name,
        "plan": request.plan,
        "days_added": days,
        "new_expiry_date": new_expiry,
        "is_active": school.is_active,
        "status": school.status,
        "performed_by": current_user.name
    }

# ============================================================
# 🔥🔥🔥 SUPERADMIN - GET SCHOOL STATUS 🔥🔥🔥
# ============================================================
@router.get("/superadmin/schools/{school_id}/status")
def get_school_status(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Get detailed school status.
    """
    
    # ============================================================
    # 🔥 1. HAKIKISHA NI SUPERADMIN
    # ============================================================
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    
    is_superadmin = user_role == "superadmin" or user_role == "Superadmin"
    if not is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can view this information"
        )
    
    # ============================================================
    # 🔥 2. HAKIKISHA SHULE IPO
    # ============================================================
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # ============================================================
    # 🔥 3. HESABU SIKU ZILIZOSALIA
    # ============================================================
    now = datetime.now()
    days_left = 0
    if school.subscription_expires_at:
        days_left = max(0, (school.subscription_expires_at - now).days)
    
    is_expired = not school.subscription_expires_at or school.subscription_expires_at < now
    
    # ============================================================
    # 🔥 4. HESABU WALIMU NA WANAFUNZI
    # ============================================================
    from app.models.teacher import Teacher
    from app.models.student import Student
    
    total_teachers = db.query(Teacher).filter(Teacher.school_id == school_id).count()
    total_students = db.query(Student).filter(Student.school_id == school_id).count()
    active_teachers = db.query(Teacher).filter(Teacher.school_id == school_id, Teacher.status == "active").count()
    active_students = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
    
    # ============================================================
    # 🔥 5. RETURN RESPONSE
    # ============================================================
    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "school_level": school.school_level,
            "school_type": school.school_type,
            "region": school.region,
            "district": school.district
        },
        "subscription": {
            "plan": school.subscription_plan,
            "expires_at": school.subscription_expires_at,
            "days_left": days_left,
            "is_expired": is_expired,
            "is_active": school.is_active,
            "is_locked_by_superadmin": school.is_locked_by_superadmin,
            "status": school.status
        },
        "statistics": {
            "total_teachers": total_teachers,
            "active_teachers": active_teachers,
            "total_students": total_students,
            "active_students": active_students
        },
        "can_login": school.is_active and not is_expired and not school.is_locked_by_superadmin
    }

# ============================================================
# 🔥 GET HEADMASTER - KUTOKA TEACHERS TABLE
# ============================================================
@router.get("/schools/{school_id}/headmaster")
def get_school_headmaster(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get headmaster of a school from teachers table"""
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    school_level = school.school_level or school.school_type or "secondary"
    head_roles = get_headmaster_roles(school_level)
    
    headmaster = db.query(Teacher).filter(
        Teacher.school_id == school_id,
        Teacher.role.in_(head_roles),
        Teacher.status == "active",
        Teacher.active == True
    ).first()
    
    if headmaster:
        return {
            "id": headmaster.id,
            "name": headmaster.name,
            "email": headmaster.email,
            "role": headmaster.role,
            "phone": headmaster.phone1,
            "status": headmaster.status,
            "school_id": headmaster.school_id,
            "school_level": school_level
        }
    
    # Fallback: any active teacher
    any_teacher = db.query(Teacher).filter(
        Teacher.school_id == school_id,
        Teacher.status == "active",
        Teacher.active == True
    ).first()
    
    if any_teacher:
        return {
            "id": any_teacher.id,
            "name": any_teacher.name,
            "email": any_teacher.email,
            "role": any_teacher.role,
            "phone": any_teacher.phone1,
            "status": any_teacher.status,
            "school_id": any_teacher.school_id,
            "school_level": school_level,
            "note": "No headmaster found, returning first active teacher"
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No active teacher found for school ID {school_id}"
    )

# ============================================================
# 🔥 GET CLASS TEACHER
# ============================================================
@router.get("/classes/{class_id}/teacher")
def get_class_teacher(
    class_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get class teacher from teachers table"""
    
    from app.models.school_class import SchoolClass
    from app.models.teacher_subject import TeacherSubject
    
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found"
        )
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_level = school.school_level if school else "secondary"
    teacher_roles = get_teacher_roles(school_level)
    
    teacher_assignment = db.query(TeacherSubject).filter(
        TeacherSubject.class_id == class_id
    ).first()
    
    if teacher_assignment:
        teacher = db.query(Teacher).filter(
            Teacher.id == teacher_assignment.teacher_id,
            Teacher.school_id == school_class.school_id,
            Teacher.role.in_(teacher_roles),
            Teacher.status == "active",
            Teacher.active == True
        ).first()
        
        if teacher:
            return {
                "id": teacher.id,
                "name": teacher.name,
                "email": teacher.email,
                "role": teacher.role,
                "phone": teacher.phone1,
                "status": teacher.status,
                "school_id": teacher.school_id,
                "school_level": school_level
            }
    
    # Fallback: any active teacher
    teacher = db.query(Teacher).filter(
        Teacher.school_id == school_class.school_id,
        Teacher.status == "active",
        Teacher.active == True
    ).first()
    
    if teacher:
        return {
            "id": teacher.id,
            "name": teacher.name,
            "email": teacher.email,
            "role": teacher.role,
            "phone": teacher.phone1,
            "status": teacher.status,
            "school_id": teacher.school_id,
            "school_level": school_level,
            "note": "No assigned teacher found, returning first active teacher"
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No active teacher found for class ID {class_id}"
    )

# ============================================================
# 🔥 GET HEADMASTERS BY SCHOOL LEVEL
# ============================================================
@router.get("/headmasters")
def get_headmasters_by_school_level(
    school_level: Optional[str] = Query(None, description="Filter by school level: primary, secondary, advanced"),
    school_id: Optional[int] = Query(None, description="Filter by school ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get headmasters from teachers table"""
    
    if school_level:
        head_roles = get_headmaster_roles(school_level)
    else:
        head_roles = get_headmaster_roles("primary") + get_headmaster_roles("secondary")
    
    query = db.query(Teacher).filter(
        Teacher.role.in_(head_roles),
        Teacher.status == "active",
        Teacher.active == True
    )
    
    if school_id:
        query = query.filter(Teacher.school_id == school_id)
    
    headmasters = query.order_by(Teacher.name).all()
    
    result = []
    for hm in headmasters:
        school = db.query(School).filter(School.id == hm.school_id).first()
        result.append({
            "id": hm.id,
            "name": hm.name,
            "email": hm.email,
            "role": hm.role,
            "phone": hm.phone1,
            "status": hm.status,
            "school_id": hm.school_id,
            "school_name": school.name if school else "Unknown",
            "school_level": school.school_level if school else "Unknown"
        })
    
    return result