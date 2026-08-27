# app/api/v1/superadmin.py

from fastapi import APIRouter, Depends, HTTPException, Query, status,Request,Header  # ← ONGEZA HII!
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import pytz
from pydantic import BaseModel, validator
from app.core.database import get_db
from app.core.security import get_current_user, create_access_token
from app.models.school import School, SchoolStatus, SubscriptionPlan
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from app.models.homepage import SidebarItem, HomepageSlide, HomepageAd
from app.models.payment_transaction import PaymentTransaction
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🔥 TIMEZONE KWA TANZANIA (UTC+3)
# ============================================================
TZ = pytz.timezone("Africa/Dar_es_Salaam")

def get_tz_now():
    """Get current time in Tanzania timezone (UTC+3)"""
    return datetime.now(TZ)

# ================================
# Pydantic Schemas
# ================================

class SchoolResponse(BaseModel):
    id: int
    name: str
    school_type: str
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    region: Optional[str]
    district: Optional[str]
    is_active: bool
    status: str
    subscription_plan: Optional[str]
    subscription_expires_at: Optional[datetime]
    is_locked_by_superadmin: bool
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ExtendSubscriptionRequest(BaseModel):
    days: int = 30
    plan: str = "monthly"
    
    @validator('days')
    def validate_days(cls, v):
        if v < 1:
            raise ValueError("Days must be at least 1")
        if v > 365:
            raise ValueError("Days cannot exceed 365")
        return v
    
    @validator('plan')
    def validate_plan(cls, v):
        valid_plans = ['monthly', 'quarterly', 'semester', 'annual']
        if v not in valid_plans:
            raise ValueError(f"Plan must be one of: {', '.join(valid_plans)}")
        return v

class LockSchoolRequest(BaseModel):
    is_locked: bool

class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str
    school_id: int
    school_name: str
    user_id: int
    user_name: str
    user_role: str

class SuperAdminStats(BaseModel):
    total_schools: int
    active_schools: int
    expired_schools: int
    locked_schools: int
    total_teachers: int
    total_students: int
    total_subscriptions: int

# ================================
# HOMEPAGE SCHEMAS
# ================================

class SidebarItemCreate(BaseModel):
    image_url: str
    title: Optional[str] = None
    caption: Optional[str] = None
    order: int = 0
    active: bool = True

class SidebarItemResponse(BaseModel):
    id: int
    image_url: str
    title: Optional[str]
    caption: Optional[str]
    order: int
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class HomepageSlideCreate(BaseModel):
    image_url: str
    caption: Optional[str] = None
    order: int = 0
    active: bool = True

class HomepageSlideResponse(BaseModel):
    id: int
    image_url: str
    caption: Optional[str]
    order: int
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class HomepageAdCreate(BaseModel):
    image_url: str
    title: Optional[str] = None
    caption: Optional[str] = None
    link: Optional[str] = None
    order: int = 0
    active: bool = True

class HomepageAdResponse(BaseModel):
    id: int
    image_url: str
    title: Optional[str]
    caption: Optional[str]
    link: Optional[str]
    order: int
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ================================
# SCHOOL CREATE
# ================================

class SchoolCreate(BaseModel):
    name: str
    school_type: str = "secondary"
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None


# ================================
# SUPERADMIN SUBSCRIPTION EXTEND
# ================================

class SuperAdminSubscriptionExtend(BaseModel):
    plan: str = "monthly"
    days: Optional[int] = None
    
    @validator('plan')
    def validate_plan(cls, v):
        valid_plans = ['monthly', 'quarterly', 'semester', 'annual']
        if v not in valid_plans:
            raise ValueError(f"Plan must be one of: {', '.join(valid_plans)}")
        return v
    
    @validator('days')
    def validate_days(cls, v):
        if v is not None and v < 1:
            raise ValueError("Days must be at least 1")
        return v












# ============================================================
# 🔥 HELPER: CHECK SUPERADMIN - VERSION 2.0 (ULTIMATE)
# ============================================================
def is_superadmin(user) -> bool:
    """
    Check if user is SuperAdmin - NJIA ZOTE ZIMEWEKWA!
    
    Args:
        user: User object from FastAPI dependency
    
    Returns:
        bool: True if user is SuperAdmin, False otherwise
    """
    
    # ============================================================
    # 🔥 STEP 1: LOG ZA KUANGALIA (KWA DEBUGGING)
    # ============================================================
    logger.info("=" * 60)
    logger.info("🔍 ========== is_superadmin CHECK ==========")
    logger.info(f"🔍 User ID: {getattr(user, 'id', 'NO_ID')}")
    logger.info(f"🔍 User Class: {user.__class__.__name__ if hasattr(user, '__class__') else 'Unknown'}")
    logger.info(f"🔍 User Module: {user.__class__.__module__ if hasattr(user, '__class__') else 'Unknown'}")
    logger.info(f"🔍 is_superadmin attr: {getattr(user, 'is_superadmin', 'NOT_FOUND')}")
    logger.info(f"🔍 role attr: {getattr(user, 'role', 'NOT_FOUND')}")
    logger.info(f"🔍 user_type attr: {getattr(user, 'user_type', 'NOT_FOUND')}")
    logger.info(f"🔍 username: {getattr(user, 'username', 'NO_USERNAME')}")
    logger.info(f"🔍 email: {getattr(user, 'email', 'NO_EMAIL')}")
    logger.info(f"🔍 name: {getattr(user, 'name', 'NO_NAME')}")
    
    # Check if user object is empty
    if not user:
        logger.warning("⚠️ User object is None or empty")
        logger.info("=" * 60)
        return False
    
    # ============================================================
    # 🔥 STEP 2: CHECK USING MULTIPLE METHODS
    # ============================================================
    is_superadmin_user = False
    reasons = []
    
    # METHOD 1: Check class name
    try:
        if hasattr(user, '__class__') and user.__class__.__name__ == 'SuperAdmin':
            is_superadmin_user = True
            reasons.append("✅ Class name is SuperAdmin")
            logger.info("   ✅ Method 1: Class name is SuperAdmin")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 1 failed: {e}")
    
    # METHOD 2: Check is_superadmin attribute
    try:
        if hasattr(user, 'is_superadmin') and user.is_superadmin:
            is_superadmin_user = True
            reasons.append("✅ is_superadmin attribute is True")
            logger.info("   ✅ Method 2: is_superadmin=True")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 2 failed: {e}")
    
    # METHOD 3: Check role attribute (string or Enum)
    try:
        if hasattr(user, 'role'):
            role = user.role
            if hasattr(role, 'value'):
                role = role.value
            role_str = str(role).lower()
            if role_str in ['superadmin', 'super_admin', 'admin']:
                is_superadmin_user = True
                reasons.append(f"✅ Role is {role}")
                logger.info(f"   ✅ Method 3: role={role}")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 3 failed: {e}")
    
    # METHOD 4: Check user_type attribute (from token)
    try:
        if hasattr(user, 'user_type'):
            user_type = user.user_type
            if hasattr(user_type, 'value'):
                user_type = user_type.value
            user_type_str = str(user_type).lower()
            if user_type_str in ['superadmin', 'super_admin', 'admin']:
                is_superadmin_user = True
                reasons.append(f"✅ User type is {user_type}")
                logger.info(f"   ✅ Method 4: user_type={user_type}")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 4 failed: {e}")
    
    # METHOD 5: Check username (fallback)
    try:
        if hasattr(user, 'username'):
            username = str(user.username).lower()
            if username in ['superadmin', 'admin', 'super_admin', 'matandala']:
                is_superadmin_user = True
                reasons.append(f"✅ Username is {username}")
                logger.info(f"   ✅ Method 5: username={username}")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 5 failed: {e}")
    
    # METHOD 6: Check ID (SuperAdmin default is 1)
    try:
        if hasattr(user, 'id') and user.id == 1:
            is_superadmin_user = True
            reasons.append("✅ User ID is 1")
            logger.info("   ✅ Method 6: ID=1")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 6 failed: {e}")
    
    # METHOD 7: Check if user exists in SuperAdmin table
    try:
        if hasattr(user, 'id') and user.id:
            from app.models.superadmin import SuperAdmin
            from app.core.database import SessionLocal
            
            db = SessionLocal()
            try:
                sa = db.query(SuperAdmin).filter(SuperAdmin.id == user.id).first()
                if sa:
                    is_superadmin_user = True
                    reasons.append(f"✅ Found in SuperAdmin table with ID {user.id}")
                    logger.info(f"   ✅ Method 7: Found in database with ID {user.id}")
            finally:
                db.close()
    except ImportError as e:
        logger.warning(f"   ⚠️ Method 7 failed (import): {e}")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 7 failed (database): {e}")
    
    # METHOD 8: Check via token payload (if available)
    try:
        if hasattr(user, 'token_data') and user.token_data:
            token_user_type = user.token_data.get('user_type')
            if token_user_type and str(token_user_type).lower() in ['superadmin', 'super_admin', 'admin']:
                is_superadmin_user = True
                reasons.append(f"✅ Token user_type is {token_user_type}")
                logger.info(f"   ✅ Method 8: token user_type={token_user_type}")
    except Exception as e:
        logger.warning(f"   ⚠️ Method 8 failed: {e}")
    
    # ============================================================
    # 🔥 STEP 3: LOG RESULTS
    # ============================================================
    logger.info("-" * 40)
    if is_superadmin_user:
        logger.info("✅ RESULT: User IS SuperAdmin")
        for reason in reasons:
            logger.info(f"   {reason}")
    else:
        logger.info("❌ RESULT: User IS NOT SuperAdmin")
        logger.info("   💡 Possible reasons:")
        logger.info("      1. User is not a SuperAdmin")
        logger.info("      2. Token is invalid or expired")
        logger.info("      3. User object is incomplete")
        logger.info("      4. Database connection issue")
    
    logger.info("=" * 60)
    
    return is_superadmin_user


# ============================================================
# 🔥 ALTERNATIVE: is_superadmin_simple() - FASTER VERSION
# ============================================================
def is_superadmin_simple(user) -> bool:
    """
    Quick check for SuperAdmin - FASTER but less thorough
    
    Args:
        user: User object from FastAPI dependency
    
    Returns:
        bool: True if user is SuperAdmin, False otherwise
    """
    if not user:
        return False
    
    # Quick checks in order of speed
    # 1. Check is_superadmin attribute
    if hasattr(user, 'is_superadmin') and user.is_superadmin:
        return True
    
    # 2. Check class name
    if hasattr(user, '__class__') and user.__class__.__name__ == 'SuperAdmin':
        return True
    
    # 3. Check ID
    if hasattr(user, 'id') and user.id == 1:
        return True
    
    # 4. Check role
    if hasattr(user, 'role'):
        role = user.role
        if hasattr(role, 'value'):
            role = role.value
        if str(role).lower() in ['superadmin', 'super_admin']:
            return True
    
    # 5. Check user_type
    if hasattr(user, 'user_type'):
        user_type = user.user_type
        if hasattr(user_type, 'value'):
            user_type = user_type.value
        if str(user_type).lower() in ['superadmin', 'super_admin']:
            return True
    
    return False


# ============================================================
# 🔥 DECORATOR FOR SUPERADMIN ROUTES
# ============================================================
from functools import wraps
from fastapi import HTTPException, status

def superadmin_required(func):
    """
    Decorator to require SuperAdmin access for route handlers
    
    Usage:
        @router.get("/admin-only")
        @superadmin_required
        def admin_route(current_user = Depends(get_current_user)):
            return {"message": "You are superadmin!"}
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get current_user from kwargs (FastAPI passes it by name)
        current_user = kwargs.get('current_user')
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if not is_superadmin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin access required"
            )
        
        return func(*args, **kwargs)
    
    return wrapper


# ============================================================
# 🔥 TEST FUNCTION (FOR DEVELOPMENT)
# ============================================================
def test_is_superadmin():
    """
    Test the is_superadmin function with mock objects
    """
    from unittest.mock import Mock
    
    # Test 1: SuperAdmin with correct class
    superadmin_mock = Mock()
    superadmin_mock.__class__.__name__ = 'SuperAdmin'
    superadmin_mock.id = 1
    superadmin_mock.username = 'matandala'
    superadmin_mock.role = 'superadmin'
    superadmin_mock.user_type = 'superadmin'
    superadmin_mock.is_superadmin = True
    
    result = is_superadmin(superadmin_mock)
    print(f"Test 1 (SuperAdmin class): {result}")  # Should be True
    
    # Test 2: Regular user
    regular_user = Mock()
    regular_user.__class__.__name__ = 'User'
    regular_user.id = 5
    regular_user.username = 'teacher1'
    regular_user.role = 'teacher'
    regular_user.user_type = 'teacher'
    regular_user.is_superadmin = False
    
    result = is_superadmin(regular_user)
    print(f"Test 2 (Regular user): {result}")  # Should be False
    
    # Test 3: User with ID 1 but not SuperAdmin
    user_id_1 = Mock()
    user_id_1.__class__.__name__ = 'User'
    user_id_1.id = 1
    user_id_1.username = 'user1'
    user_id_1.role = 'teacher'
    user_id_1.user_type = 'teacher'
    user_id_1.is_superadmin = False
    
    result = is_superadmin(user_id_1)
    print(f"Test 3 (User with ID 1): {result}")  # Should be True (ID check)
    
    # Test 4: None user
    result = is_superadmin(None)
    print(f"Test 4 (None user): {result}")  # Should be False
    
    print("\n✅ All tests complete!")




# ================================
# Router
# ================================

router = APIRouter()


# ================================
# SCHOOL MANAGEMENT ENDPOINTS
# ================================

@router.get("/schools", response_model=List[SchoolResponse])
def get_all_schools(
    school_type: Optional[str] = Query(None, description="Filter by school type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can view all schools"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized access to /schools by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    query = db.query(School)
    
    if school_type:
        query = query.filter(School.school_type == school_type)
    if status:
        query = query.filter(School.status == status)
    
    schools = query.all()
    logger.info(f"✅ Superadmin {current_user.name} fetched {len(schools)} schools")
    return schools


@router.post("/schools", response_model=SchoolResponse)
def create_school(
    school_data: SchoolCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can create a new school"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized school creation attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    existing = db.query(School).filter(School.name == school_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"School with name '{school_data.name}' already exists")
    
    valid_school_types = ["primary", "secondary", "advanced"]
    if school_data.school_type.lower() not in valid_school_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid school_type. Must be one of: {', '.join(valid_school_types)}"
        )
    
    school_type_lower = school_data.school_type.lower()
    school_type_display = school_type_lower.upper()
    
    new_school = School(
        name=school_data.name,
        school_type=school_type_display,
        school_level=school_type_lower,
        email=school_data.email,
        phone=school_data.phone,
        address=school_data.address,
        region=school_data.region,
        district=school_data.district,
        is_active=True,
        status=SchoolStatus.ACTIVE,
        is_locked_by_superadmin=False
    )
    
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    
    logger.info(
        "✅ School created by superadmin %s: id=%s name=%s type=%s region=%s district=%s",
        current_user.name,
        new_school.id,
        new_school.name,
        new_school.school_type,
        new_school.region,
        new_school.district,
    )

    return new_school


@router.get("/schools/{school_id}", response_model=SchoolResponse)
def get_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can view a specific school"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized access to school {school_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school







# ============================================================
# 🔥🔥🔥 SUPERADMIN LOCK/UNLOCK SCHOOL - PRO MAX VERSION
# ============================================================

@router.put("/schools/{school_id}/lock")
def lock_school(
    school_id: int,
    request: LockSchoolRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Lock or unlock a school with professional messaging
    
    When locking:
    - Comprehensive reason for lock
    - Clear action items for resolution
    - Professional formatting
    
    When unlocking:
    - Confirmation of restored access
    - Next steps for user
    """
    
    # ============================================================
    # 🔥 STEP 1: CHECK PERMISSIONS
    # ============================================================
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized lock attempt on school {school_id} by user {getattr(current_user, 'id', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ACCESS_DENIED",
                "message": "Access denied. Superadmin privileges required to perform this action.",
                "code": "FORBIDDEN_001"
            }
        )
    
    # ============================================================
    # 🔥 STEP 2: FIND SCHOOL
    # ============================================================
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        logger.warning(f"⚠️ School {school_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "SCHOOL_NOT_FOUND",
                "message": f"School with ID {school_id} was not found in our system.",
                "code": "NOT_FOUND_001"
            }
        )
    
    # ============================================================
    # 🔥 STEP 3: GET SCHOOL DETAILS
    # ============================================================
    admin_name = getattr(current_user, 'name', None) or getattr(current_user, 'username', 'SuperAdmin')
    now = get_tz_now()
    
    # Calculate subscription status
    days_left = 0
    days_overdue = 0
    is_expired = True
    
    if school.subscription_expires_at:
        expires = school.subscription_expires_at
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        
        if expires > now:
            days_left = (expires - now).days
            is_expired = False
        else:
            days_overdue = (now - expires).days
            is_expired = True
    
    # ============================================================
    # 🔥 STEP 4: PERFORM ACTION (LOCK OR UNLOCK)
    # ============================================================
    old_lock_status = school.is_locked_by_superadmin
    action = "locked" if request.is_locked else "unlocked"
    
    school.is_locked_by_superadmin = request.is_locked
    
    if request.is_locked:
        # 🔒 LOCK SCHOOL
        school.status = SchoolStatus.INACTIVE
        school.is_active = False
        
        # Professional lock message
        if is_expired:
            lock_reason = "subscription_expired"
            lock_details = {
                "reason": "Subscription has expired",
                "days_overdue": days_overdue,
                "expires_at": school.subscription_expires_at,
                "plan": school.subscription_plan
            }
        else:
            lock_reason = "administrative_lock"
            lock_details = {
                "reason": "Administrative action",
                "performed_by": admin_name,
                "performed_at": now.isoformat()
            }
        
        message = generate_lock_message(school.name, lock_reason, lock_details)
        
    else:
        # 🔓 UNLOCK SCHOOL
        if school.is_subscription_active():
            school.status = SchoolStatus.ACTIVE
            school.is_active = True
            status_message = "active"
        else:
            school.status = SchoolStatus.INACTIVE
            school.is_active = False
            status_message = "inactive (subscription expired)"
        
        message = generate_unlock_message(school.name, status_message)
    
    # ============================================================
    # 🔥 STEP 5: COMMIT CHANGES
    # ============================================================
    try:
        db.commit()
        db.refresh(school)
        logger.info(f"🔑 Superadmin {admin_name} {action} school: {school.name} (ID: {school.id})")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to {action} school {school_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": f"Failed to {action} school. Please try again or contact support.",
                "code": "DB_001"
            }
        )
    
    # ============================================================
    # 🔥 STEP 6: RETURN PROFESSIONAL RESPONSE
    # ============================================================
    return {
        "success": True,
        "message": message,
        "data": {
            "school_id": school.id,
            "school_name": school.name,
            "school_type": school.school_type,
            "is_locked": school.is_locked_by_superadmin,
            "is_active": school.is_active,
            "status": school.status.value,
            "subscription_plan": school.subscription_plan,
            "subscription_expires_at": school.subscription_expires_at,
            "days_left": days_left if not is_expired else 0,
            "days_overdue": days_overdue if is_expired else 0,
            "is_expired": is_expired
        },
        "action": {
            "type": action,
            "performed_by": admin_name,
            "performed_at": now.isoformat(),
            "previous_status": old_lock_status
        },
        "support": {
            "email": "support@schoolsystem.com",
            "phone": "+255 700 000 000",
            "hours": "Monday - Friday, 8:00 AM - 6:00 PM (EAT)"
        }
    }


# ============================================================
# 🔥 HELPER FUNCTIONS FOR PROFESSIONAL MESSAGES
# ============================================================

def generate_lock_message(school_name: str, reason: str, details: dict) -> str:
    """Generate professional lock message based on reason"""
    
    if reason == "subscription_expired":
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    ⚠️ ACCOUNT SUSPENDED                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Dear {school_name} Administrator,                             ║
║                                                                ║
║  Your school account has been TEMPORARILY SUSPENDED due to     ║
║  an EXPIRED SUBSCRIPTION. To restore full access to all        ║
║  features and services, please renew your subscription.        ║
║                                                                ║
║  📋 SUBSCRIPTION DETAILS:                                      ║
║  ───────────────────────────────────────────────────────────    ║
║  • Plan: {details.get('plan', 'N/A')}                         ║
║  • Expired: {details.get('days_overdue', 0)} days ago         ║
║  • Expiry Date: {details.get('expires_at', 'N/A')}            ║
║                                                                ║
║  🔹 WHAT YOU NEED TO DO:                                       ║
║  ───────────────────────────────────────────────────────────    ║
║  1️⃣ Contact your school management to process payment         ║
║  2️⃣ Choose a subscription plan that fits your needs           ║
║  3️⃣ Complete the renewal process                              ║
║  4️⃣ Contact support for assistance if needed                  ║
║                                                                ║
║  🔹 BENEFITS OF RENEWING:                                      ║
║  ───────────────────────────────────────────────────────────    ║
║  ✅ Full access to student management system                  ║
║  ✅ Teacher and staff management                              ║
║  ✅ Academic records and reports                              ║
║  ✅ Parent and student communication                          ║
║  ✅ 24/7 technical support                                    ║
║  ✅ Regular system updates and security patches               ║
║                                                                ║
║  📞 NEED HELP?                                                 ║
║  ───────────────────────────────────────────────────────────    ║
║  Email: support@schoolsystem.com                              ║
║  Phone: +255 700 000 000                                      ║
║  Hours: Monday - Friday, 8:00 AM - 6:00 PM (EAT)             ║
║                                                                ║
║  We look forward to serving you again!                        ║
║                                                                ║
╚══════════════════════════════════════════════════════════════════╝
""".strip()
    
    elif reason == "administrative_lock":
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    🔒 ACCOUNT LOCKED                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Dear {school_name} Administrator,                             ║
║                                                                ║
║  Your school account has been TEMPORARILY LOCKED by the        ║
║  system administrator for routine maintenance and review.      ║
║  This is a standard procedure to ensure system security and    ║
║  optimal performance.                                          ║
║                                                                ║
║  📋 LOCK DETAILS:                                              ║
║  ───────────────────────────────────────────────────────────    ║
║  • Reason: {details.get('reason', 'Administrative action')}   ║
║  • Performed By: {details.get('performed_by', 'System Admin')}║
║  • Performed At: {details.get('performed_at', 'N/A')}         ║
║                                                                ║
║  🔹 WHAT YOU NEED TO DO:                                       ║
║  ───────────────────────────────────────────────────────────    ║
║  1️⃣ Wait for the review to complete (usually within 24 hrs)  ║
║  2️⃣ Contact support if you have questions                     ║
║  3️⃣ You will be notified when access is restored              ║
║                                                                ║
║  📞 NEED HELP?                                                 ║
║  ───────────────────────────────────────────────────────────    ║
║  Email: support@schoolsystem.com                              ║
║  Phone: +255 700 000 000                                      ║
║                                                                ║
║  We apologize for any inconvenience and appreciate your       ║
║  patience.                                                    ║
║                                                                ║
╚══════════════════════════════════════════════════════════════════╝
""".strip()
    
    else:
        return f"""
⚠️ ACCOUNT LOCKED: {school_name}

Your school account has been temporarily locked. Please contact support for assistance.

📧 Email: support@schoolsystem.com
📞 Phone: +255 700 000 000
""".strip()


def generate_unlock_message(school_name: str, status: str) -> str:
    """Generate professional unlock message"""
    
    return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    ✅ ACCOUNT UNLOCKED                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Dear {school_name} Administrator,                             ║
║                                                                ║
║  Your school account has been successfully UNLOCKED!           ║
║  All features and services are now accessible.                 ║
║                                                                ║
║  📋 ACCOUNT STATUS:                                            ║
║  ───────────────────────────────────────────────────────────    ║
║  • Status: {status.upper()}                                   ║
║  • Access: Full access restored                               ║
║  • All features: Available                                    ║
║                                                                ║
║  🔹 WHAT YOU CAN DO NOW:                                       ║
║  ───────────────────────────────────────────────────────────    ║
║  ✅ Login to your school dashboard                            ║
║  ✅ Manage students and teachers                              ║
║  ✅ Access academic records                                   ║
║  ✅ Generate reports                                          ║
║  ✅ Communicate with parents and students                     ║
║                                                                ║
║  📞 NEED HELP?                                                 ║
║  ───────────────────────────────────────────────────────────    ║
║  Email: support@schoolsystem.com                              ║
║  Phone: +255 700 000 000                                      ║
║                                                                ║
║  Welcome back! 🎉                                              ║
║                                                                ║
╚══════════════════════════════════════════════════════════════════╝
""".strip()






@router.post("/schools/{school_id}/extend-subscription")
def extend_subscription(
    school_id: int,
    request: ExtendSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can manually extend school subscription"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized extend attempt on school {school_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    tz = school._get_tz()
    now = datetime.now(tz)
    
    # ✅ HESABU TAREHE MPYA
    if school.subscription_expires_at and school.subscription_expires_at > now:
        new_expiry = school.subscription_expires_at + timedelta(days=request.days)
    else:
        new_expiry = now + timedelta(days=request.days)
    
    school.subscription_expires_at = new_expiry
    school.subscription_plan = request.plan
    school.is_overridden = True
    
    # ✅ WEKA ACTIVE
    school.is_active = True
    if school.is_locked_by_superadmin:
        school.is_locked_by_superadmin = False
    
    school.status = SchoolStatus.ACTIVE
    
    db.commit()
    db.refresh(school)
    
    logger.info(f"🔑 Superadmin {current_user.name} extended subscription for school {school.name} (ID: {school.id}) by {request.days} days. New expiry: {new_expiry}")
    
    return {
        "message": f"Subscription extended by {request.days} days",
        "school_id": school.id,
        "school_name": school.name,
        "new_expiry_date": new_expiry,
        "plan": request.plan,
        "is_active": school.is_active,
        "status": school.status.value
    }


@router.delete("/schools/{school_id}")
def delete_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can delete a school (and all associated data)"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized delete attempt on school {school_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    school_name = school.name
    
    try:
        db.delete(school)
        db.commit()
        logger.info(f"🗑️ Superadmin {current_user.name} deleted school: {school_name} (ID: {school_id})")
        return {
            "message": f"School '{school_name}' deleted successfully",
            "school_id": school_id
        }
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete school {school_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete school: {str(e)}")




# ============================================================
# 🔥 DEBUG: TEST TOGGLE ENDPOINT (FOR TESTING)
# ============================================================

@router.get("/debug/toggle-test")
def debug_toggle_test(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 DEBUG: Test if user can access toggle endpoint
    """
    try:
        user_id = getattr(current_user, 'id', None)
        user_class = current_user.__class__.__name__
        is_sa = is_superadmin(current_user)
        
        return {
            "authenticated": True,
            "user": {
                "id": user_id,
                "class": user_class,
                "is_superadmin": is_sa,
                "username": getattr(current_user, 'username', None),
                "name": getattr(current_user, 'name', None),
                "user_type": getattr(current_user, 'user_type', None),
            },
            "can_toggle": is_sa,
            "message": "You can use toggle endpoint" if is_sa else "You need SuperAdmin privileges"
        }
    except Exception as e:
        return {
            "authenticated": False,
            "error": str(e)
        }
    

# ============================================================
# 🔥 DEBUG: TOKEN INSPECTOR
# ============================================================

@router.get("/debug/token-info")
def debug_token_info(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    🔥 DEBUG: Check token information
    """
    result = {
        "has_auth": bool(authorization),
        "auth_header": authorization,
    }
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        result["token_preview"] = token[:30] + "..." if len(token) > 30 else token
        
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            result["payload"] = payload
            
            if payload:
                user_id = payload.get("sub")
                user_type = payload.get("user_type")
                result["user_id"] = user_id
                result["user_type"] = user_type
                result["is_superadmin_in_token"] = user_type and user_type.lower() in ["superadmin", "super_admin"]
                
                # Check in database
                if user_id:
                    sa = db.query(SuperAdmin).filter(SuperAdmin.id == user_id).first()
                    if sa:
                        result["superadmin_in_db"] = True
                        result["superadmin_username"] = sa.username
                        result["superadmin_name"] = getattr(sa, 'name', None)
                    else:
                        result["superadmin_in_db"] = False
        except Exception as e:
            result["decode_error"] = str(e)
    else:
        result["error"] = "No Bearer token found"
    
    return result    




# ============================================================
# 🔥🔥🔥 SUPERADMIN GET SCHOOL STATUS 🔥🔥🔥
# ============================================================

@router.get("/schools/{school_id}/status")
def get_school_status(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Get detailed school status.
    
    Returns comprehensive information about a school including:
    - School details (name, level, type, region, district)
    - Subscription information (plan, expiry, days left/overdue)
    - Status (active, expired, locked)
    - Statistics (teachers, students)
    - Login eligibility (can_login)
    """
    


    # ============================================================
    # 1. CHECK SUPERADMIN PERMISSIONS
    # ============================================================
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized status check on school {school_id} by user {getattr(current_user, 'id', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can view this information"
        )
    
    # ============================================================
    # 2. FIND SCHOOL
    # ============================================================
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        logger.warning(f"⚠️ School {school_id} not found for status check")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"School with ID {school_id} not found"
        )
    
    # ============================================================
    # 3. CALCULATE SUBSCRIPTION STATUS
    # ============================================================
    now = get_tz_now()
    days_left = 0
    days_overdue = 0
    is_expired = True
    
    if school.subscription_expires_at:
        expires = school.subscription_expires_at
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        
        if expires > now:
            days_left = (expires - now).days
            is_expired = False
        else:
            days_overdue = (now - expires).days
            is_expired = True
    else:
        # No expiry date = expired
        is_expired = True
        days_overdue = 0
    
    # ============================================================
    # 4. GET TEACHERS AND STUDENTS STATISTICS
    # ============================================================
    from app.models.student import Student
    
    total_teachers = db.query(Teacher).filter(Teacher.school_id == school_id).count()
    total_students = db.query(Student).filter(Student.school_id == school_id).count()
    active_teachers = db.query(Teacher).filter(
        Teacher.school_id == school_id, 
        Teacher.status == "active"
    ).count()
    active_students = db.query(Student).filter(
        Student.school_id == school_id, 
        Student.status == "active"
    ).count()
    
    # ============================================================
    # 5. DETERMINE CAN_LOGIN
    # ============================================================
    can_login = school.is_active and not is_expired and not school.is_locked_by_superadmin
    
    # ============================================================
    # 6. LOG AND RETURN
    # ============================================================
    logger.info(f"📊 School {school_id} ({school.name}) status checked by {current_user.name}")
    logger.info(f"   Active: {school.is_active}, Expired: {is_expired}, Locked: {school.is_locked_by_superadmin}")
    logger.info(f"   Teachers: {total_teachers}, Students: {total_students}")
    logger.info(f"   Can login: {can_login}")
    
    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "school_level": school.school_level,
            "school_type": school.school_type,
            "region": school.region,
            "district": school.district,
            "address": school.address,
            "phone": school.phone,
            "email": school.email,
            "logo_url": school.logo_url,
            "website": school.website
        },
        "subscription": {
            "plan": school.subscription_plan,
            "expires_at": school.subscription_expires_at,
            "days_left": days_left,
            "days_overdue": days_overdue,
            "is_expired": is_expired,
            "is_active": school.is_active,
            "is_locked_by_superadmin": school.is_locked_by_superadmin,
            "status": school.status,
            "is_overridden": school.is_overridden
        },
        "statistics": {
            "total_teachers": total_teachers,
            "active_teachers": active_teachers,
            "total_students": total_students,
            "active_students": active_students
        },
        "permissions": {
            "can_login": can_login,
            "is_active": school.is_active,
            "is_expired": is_expired,
            "is_locked": school.is_locked_by_superadmin
        },
        "checked_by": current_user.name,
        "checked_at": now.isoformat()
    }


# ============================================================
# 🔥🔥🔥 SUPERADMIN EXTEND SUBSCRIPTION (MANUAL) 🔥🔥🔥
# ============================================================

@router.post("/schools/{school_id}/extend-subscription-manual")
def extend_subscription_manual(
    school_id: int,
    request: SuperAdminSubscriptionExtend,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Manually extend school subscription.
    Plans: monthly (30 days), quarterly (90 days), semester (180 days), annual (365 days)
    """
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized manual extend attempt on school {school_id} by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can manually extend subscription"
        )
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Get days from plan
    plan_days = {
        "monthly": 30,
        "quarterly": 90,
        "semester": 180,
        "annual": 365
    }
    days = request.days or plan_days.get(request.plan, 30)
    
    now = get_tz_now()
    
    if school.subscription_expires_at:
        expires = school.subscription_expires_at
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        if expires > now:
            new_expiry = expires + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
    else:
        new_expiry = now + timedelta(days=days)
    
    school.subscription_expires_at = new_expiry
    school.subscription_plan = request.plan
    school.is_active = True
    school.status = "active"
    school.is_locked_by_superadmin = False
    
    db.commit()
    db.refresh(school)
    
    logger.info(f"🔑 Superadmin {current_user.name} extended subscription for {school.name} (ID: {school.id}) by {days} days. New expiry: {new_expiry}")
    
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


# ================================
# IMPERSONATION ENDPOINTS
# ================================

@router.post("/impersonate/{school_id}", response_model=ImpersonateResponse)
def impersonate_school(
    school_id: int,
    user_id: Optional[int] = Query(None, description="Specific user ID to impersonate"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can login as any school admin or teacher"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized impersonation attempt on school {school_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if user_id:
        user = db.query(Teacher).filter(Teacher.id == user_id, Teacher.school_id == school_id).first()
    else:
        user = db.query(Teacher).filter(Teacher.school_id == school_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="No user found for this school")
    
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "user_type": "teacher",
            "school_id": school_id,
            "impersonated_by": current_user.id,
            "is_impersonated": True
        }
    )
    
    logger.info(f"🔑 Superadmin {current_user.name} impersonated {user.name} (ID: {user.id}) at school {school.name} (ID: {school.id})")
    
    return ImpersonateResponse(
        access_token=access_token,
        token_type="bearer",
        school_id=school.id,
        school_name=school.name,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role
    )


@router.post("/switch-school/{school_id}")
def switch_school_context(
    school_id: int,
    academic_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Superadmin can switch to a specific school context"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized switch attempt on school {school_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    response = {
        "message": f"Switched to school: {school.name}",
        "school_id": school.id,
        "school_name": school.name
    }
    
    if academic_id:
        academic = db.query(Teacher).filter(Teacher.id == academic_id, Teacher.school_id == school_id).first()
        if academic:
            response["academic_id"] = academic.id
            response["academic_name"] = academic.name
    
    logger.info(f"🔑 Superadmin {current_user.name} switched to school {school.name} (ID: {school.id})")
    return response


# ============================================================
# 🔥🔥🔥 STATISTICS ENDPOINT - ILIYOBORESHA KABISA!
# ============================================================

@router.get("/stats", response_model=SuperAdminStats)
def get_superadmin_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get statistics for superadmin dashboard"""
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ Unauthorized stats access by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized. Superadmin access required.")
    
    from app.models.student import Student
    
    total_schools = db.query(School).count()
    
    # ✅ ACTIVE SCHOOLS - ANGALIA SUBSCRIPTION EXPIRY!
    now = get_tz_now()
    
    active_schools = db.query(School).filter(
        School.is_locked_by_superadmin == False,
        School.subscription_expires_at.isnot(None),
        School.subscription_expires_at > now
    ).count()
    
    # ✅ EXPIRED SCHOOLS
    expired_schools = db.query(School).filter(
        School.is_locked_by_superadmin == False,
        (School.subscription_expires_at.is_(None) | (School.subscription_expires_at <= now))
    ).count()
    
    # ✅ LOCKED SCHOOLS
    locked_schools = db.query(School).filter(
        School.is_locked_by_superadmin == True
    ).count()
    
    total_teachers = db.query(Teacher).count()
    total_students = db.query(Student).count()
    total_subscriptions = db.query(PaymentTransaction).filter(
        PaymentTransaction.status == "success"
    ).count()
    
    logger.info(f"📊 Superadmin {current_user.name} fetched stats: total={total_schools}, active={active_schools}, expired={expired_schools}, locked={locked_schools}")
    
    return SuperAdminStats(
        total_schools=total_schools,
        active_schools=active_schools,
        expired_schools=expired_schools,
        locked_schools=locked_schools,
        total_teachers=total_teachers,
        total_students=total_students,
        total_subscriptions=total_subscriptions
    )


# ================================
# HOMEPAGE SIDEBAR ENDPOINTS
# ================================

@router.get("/homepage/sidebar", response_model=List[SidebarItemResponse])
def get_sidebar_items(
    active_only: bool = Query(True, description="Show only active items"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get sidebar items - Public sees active, Superadmin sees all"""
    if is_superadmin(current_user):
        query = db.query(SidebarItem)
    else:
        query = db.query(SidebarItem).filter(SidebarItem.active == True)
    
    return query.order_by(SidebarItem.order).all()


@router.post("/homepage/sidebar", response_model=SidebarItemResponse)
def create_sidebar_item(
    item: SidebarItemCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create sidebar item - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    new_item = SidebarItem(
        image_url=item.image_url,
        title=item.title,
        caption=item.caption,
        order=item.order,
        active=item.active
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    logger.info(f"✅ Sidebar item created by superadmin {current_user.name}")
    return new_item


@router.put("/homepage/sidebar/{item_id}")
def update_sidebar_item(
    item_id: int,
    item: SidebarItemCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update sidebar item - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    db_item = db.query(SidebarItem).filter(SidebarItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Sidebar item not found")
    
    db_item.image_url = item.image_url
    db_item.title = item.title
    db_item.caption = item.caption
    db_item.order = item.order
    db_item.active = item.active
    
    db.commit()
    db.refresh(db_item)
    logger.info(f"✅ Sidebar item {item_id} updated by superadmin {current_user.name}")
    return {"message": "Sidebar item updated successfully"}


@router.delete("/homepage/sidebar/{item_id}")
def delete_sidebar_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete sidebar item - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    db_item = db.query(SidebarItem).filter(SidebarItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Sidebar item not found")
    
    db.delete(db_item)
    db.commit()
    logger.info(f"🗑️ Sidebar item {item_id} deleted by superadmin {current_user.name}")
    return {"message": "Sidebar item deleted successfully"}


# ================================
# HOMEPAGE SLIDES ENDPOINTS
# ================================

@router.get("/homepage/slides", response_model=List[HomepageSlideResponse])
def get_homepage_slides(
    active_only: bool = Query(True, description="Show only active slides"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get slides - Public sees active, Superadmin sees all"""
    if is_superadmin(current_user):
        query = db.query(HomepageSlide)
    else:
        query = db.query(HomepageSlide).filter(HomepageSlide.active == True)
    
    return query.order_by(HomepageSlide.order).all()


@router.post("/homepage/slides", response_model=HomepageSlideResponse)
def create_homepage_slide(
    slide: HomepageSlideCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create slide - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    new_slide = HomepageSlide(
        image_url=slide.image_url,
        caption=slide.caption,
        order=slide.order,
        active=slide.active
    )
    db.add(new_slide)
    db.commit()
    db.refresh(new_slide)
    logger.info(f"✅ Slide created by superadmin {current_user.name}")
    return new_slide


@router.put("/homepage/slides/{slide_id}")
def update_homepage_slide(
    slide_id: int,
    slide: HomepageSlideCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update slide - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    db_slide = db.query(HomepageSlide).filter(HomepageSlide.id == slide_id).first()
    if not db_slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    db_slide.image_url = slide.image_url
    db_slide.caption = slide.caption
    db_slide.order = slide.order
    db_slide.active = slide.active
    
    db.commit()
    db.refresh(db_slide)
    logger.info(f"✅ Slide {slide_id} updated by superadmin {current_user.name}")
    return {"message": "Slide updated successfully"}


@router.delete("/homepage/slides/{slide_id}")
def delete_homepage_slide(
    slide_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete slide - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    db_slide = db.query(HomepageSlide).filter(HomepageSlide.id == slide_id).first()
    if not db_slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    db.delete(db_slide)
    db.commit()
    logger.info(f"🗑️ Slide {slide_id} deleted by superadmin {current_user.name}")
    return {"message": "Slide deleted successfully"}


# ================================
# HOMEPAGE ADS ENDPOINTS
# ================================

@router.get("/homepage/ads", response_model=List[HomepageAdResponse])
def get_homepage_ads(
    active_only: bool = Query(True, description="Show only active ads"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get ads - Public sees active, Superadmin sees all"""
    if is_superadmin(current_user):
        query = db.query(HomepageAd)
    else:
        query = db.query(HomepageAd).filter(HomepageAd.active == True)
    
    return query.order_by(HomepageAd.order).all()


@router.post("/homepage/ads", response_model=HomepageAdResponse)
def create_homepage_ad(
    ad: HomepageAdCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create ad - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    new_ad = HomepageAd(
        image_url=ad.image_url,
        title=ad.title,
        caption=ad.caption,
        link=ad.link,
        order=ad.order,
        active=ad.active
    )
    db.add(new_ad)
    db.commit()
    db.refresh(new_ad)
    logger.info(f"✅ Ad created by superadmin {current_user.name}")
    return new_ad


@router.put("/homepage/ads/{ad_id}")
def update_homepage_ad(
    ad_id: int,
    ad: HomepageAdCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update ad - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    db_ad = db.query(HomepageAd).filter(HomepageAd.id == ad_id).first()
    if not db_ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    db_ad.image_url = ad.image_url
    db_ad.title = ad.title
    db_ad.caption = ad.caption
    db_ad.link = ad.link
    db_ad.order = ad.order
    db_ad.active = ad.active
    
    db.commit()
    db.refresh(db_ad)
    logger.info(f"✅ Ad {ad_id} updated by superadmin {current_user.name}")
    return {"message": "Ad updated successfully"}


@router.delete("/homepage/ads/{ad_id}")
def delete_homepage_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete ad - SUPERADMIN ONLY"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    db_ad = db.query(HomepageAd).filter(HomepageAd.id == ad_id).first()
    if not db_ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    db.delete(db_ad)
    db.commit()
    logger.info(f"🗑️ Ad {ad_id} deleted by superadmin {current_user.name}")
    return {"message": "Ad deleted successfully"}


# ================================
# GET ACADEMIC OF A SCHOOL
# ================================

@router.get("/schools/{school_id}/academic")
def get_school_academic(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get Academic user of a school"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    academic = db.query(Teacher).filter(
        Teacher.school_id == school_id,
        Teacher.role == "Academic"
    ).first()
    
    if not academic:
        raise HTTPException(status_code=404, detail="No Academic found for this school")
    
    return {
        "id": academic.id,
        "name": academic.name,
        "username": academic.username,
        "email": academic.email,
        "role": academic.role
    }


# ================================
# GET HEADMASTER/HEADMISTRESS OF A SCHOOL
# ================================

@router.get("/schools/{school_id}/head")
def get_school_head(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get Headmaster or Headmistress of a school"""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    head = db.query(Teacher).filter(
        Teacher.school_id == school_id,
        Teacher.role.in_(["Headmaster", "Headmistress"])
    ).first()
    
    if not head:
        raise HTTPException(status_code=404, detail="No Headmaster/Headmistress found for this school")
    
    return {
        "id": head.id,
        "name": head.name,
        "username": head.username,
        "email": head.email,
        "role": head.role
    }





    # ============================================================
# 🔥🔥🔥 DEBUG ENDPOINT - PUBLIC VERSION (NO AUTH REQUIRED)
# ============================================================

@router.get("/debug/me")
def debug_me(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔥 DEBUG: Show token and user details (PUBLIC - no auth required)
    """
    from fastapi.security import HTTPAuthorizationCredentials
    
    # Get token from header
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    
    result = {
        "has_token": bool(token),
        "token_preview": token[:50] + "..." if token and len(token) > 50 else token,
        "auth_header": auth_header,
        "all_headers": dict(request.headers),
        "cookies": dict(request.cookies),
    }
    
    if token:
        # Decode token
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            result["token_payload"] = payload
            
            if payload:
                user_id = payload.get("sub")
                user_type = payload.get("user_type")
                result["user_id"] = user_id
                result["user_type"] = user_type
                
                # Try to get user from database
                if user_type and user_type.lower() in ["superadmin", "super_admin"]:
                    user = db.query(SuperAdmin).filter(SuperAdmin.id == user_id).first()
                    if user:
                        result["user_found"] = True
                        result["user_details"] = {
                            "id": user.id,
                            "username": user.username,
                            "name": getattr(user, 'name', None),
                            "email": getattr(user, 'email', None),
                            "is_superadmin": True
                        }
                    else:
                        result["user_found"] = False
                        result["error"] = f"SuperAdmin with ID {user_id} not found"
                
                elif user_type and user_type.lower() == "parent":
                    from app.models.parent import Parent
                    user = db.query(Parent).filter(Parent.id == user_id).first()
                    if user:
                        result["user_found"] = True
                        result["user_details"] = {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                        }
                    else:
                        result["user_found"] = False
                        result["error"] = f"Parent with ID {user_id} not found"
                
                else:
                    # Teacher
                    from app.models.teacher import Teacher
                    user = db.query(Teacher).filter(Teacher.id == user_id).first()
                    if user:
                        result["user_found"] = True
                        result["user_details"] = {
                            "id": user.id,
                            "name": user.name,
                            "username": user.username,
                            "email": user.email,
                            "role": user.role,
                            "school_id": user.school_id
                        }
                    else:
                        result["user_found"] = False
                        result["error"] = f"User with ID {user_id} not found"
        except Exception as e:
            result["decode_error"] = str(e)
    else:
        result["error"] = "No token provided"
    
    return result





# ============================================================
# 🔥 DEBUG ENDPOINT - WITH AUTH (TEST AUTHENTICATION)
# ============================================================

@router.get("/debug/auth")
def debug_auth(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔥 DEBUG: Test authentication - requires valid token
    """
    result = {
        "authenticated": True,
        "user_class": current_user.__class__.__name__,
        "user_id": getattr(current_user, 'id', None),
        "user_username": getattr(current_user, 'username', None),
        "user_name": getattr(current_user, 'name', None),
        "user_email": getattr(current_user, 'email', None),
        "user_role": getattr(current_user, 'role', None),
        "user_type": getattr(current_user, 'user_type', None),
        "is_superadmin_attr": getattr(current_user, 'is_superadmin', None),
    }
    
    # Get all attributes
    for attr in dir(current_user):
        if not attr.startswith('_'):
            try:
                value = getattr(current_user, attr)
                if not callable(value):
                    result[attr] = str(value)
            except:
                pass
    
    return result




# ============================================================
# 🔥🔥🔥 SUPERADMIN ACTIVATE/DEACTIVATE ENDPOINTS
# ============================================================

@router.put("/schools/{school_id}/activate")
@router.patch("/schools/{school_id}/activate")
@router.post("/schools/{school_id}/activate")
def activate_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Activate a school
    """
    logger.info("=" * 80)
    logger.info("🔥🔥🔥 ACTIVATE SCHOOL ENDPOINT HIT! 🔥🔥🔥")
    logger.info(f"📡 School ID: {school_id}")
    logger.info(f"📡 User: {getattr(current_user, 'username', 'Unknown')}")
    logger.info("=" * 80)
    
    # Check superadmin
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ ACCESS DENIED: User is not SuperAdmin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Superadmin privileges required."
        )
    
    # Find school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        logger.warning(f"⚠️ School {school_id} not found")
        raise HTTPException(status_code=404, detail="School not found")
    
    logger.info(f"📚 Found school: {school.name} (ID: {school.id})")
    logger.info(f"   Current status: is_active={school.is_active}, status={school.status}")
    
    # Activate
    school.is_active = True
    school.status = "active"
    school.is_locked_by_superadmin = False
    
    # Set subscription if expired
    now = get_tz_now()
    if not school.subscription_expires_at or school.subscription_expires_at < now:
        school.subscription_expires_at = now + timedelta(days=30)
        school.subscription_plan = "monthly"
        logger.info(f"   ✅ Subscription set: monthly until {school.subscription_expires_at}")
    
    db.commit()
    db.refresh(school)
    
    admin_name = getattr(current_user, 'name', None) or getattr(current_user, 'username', 'SuperAdmin')
    
    logger.info(f"✅ {admin_name} activated school: {school.name} (ID: {school.id})")
    logger.info("=" * 80)
    
    return {
        "success": True,
        "message": f"School '{school.name}' has been activated successfully",
        "school_id": school.id,
        "school_name": school.name,
        "is_active": school.is_active,
        "status": school.status,
        "subscription_plan": school.subscription_plan,
        "subscription_expires_at": school.subscription_expires_at,
        "is_locked_by_superadmin": school.is_locked_by_superadmin,
        "performed_by": admin_name
    }


@router.put("/schools/{school_id}/deactivate")
@router.patch("/schools/{school_id}/deactivate")
@router.post("/schools/{school_id}/deactivate")
def deactivate_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 SUPERADMIN ONLY: Deactivate a school
    """
    logger.info("=" * 80)
    logger.info("🔥🔥🔥 DEACTIVATE SCHOOL ENDPOINT HIT! 🔥🔥🔥")
    logger.info(f"📡 School ID: {school_id}")
    logger.info(f"📡 User: {getattr(current_user, 'username', 'Unknown')}")
    logger.info("=" * 80)
    
    # Check superadmin
    if not is_superadmin(current_user):
        logger.warning(f"⚠️ ACCESS DENIED: User is not SuperAdmin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Superadmin privileges required."
        )
    
    # Find school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        logger.warning(f"⚠️ School {school_id} not found")
        raise HTTPException(status_code=404, detail="School not found")
    
    logger.info(f"📚 Found school: {school.name} (ID: {school.id})")
    logger.info(f"   Current status: is_active={school.is_active}, status={school.status}")
    
    # Deactivate
    school.is_active = False
    school.status = "inactive"
    school.is_locked_by_superadmin = True
    
    db.commit()
    db.refresh(school)
    
    admin_name = getattr(current_user, 'name', None) or getattr(current_user, 'username', 'SuperAdmin')
    
    logger.info(f"✅ {admin_name} deactivated school: {school.name} (ID: {school.id})")
    logger.info("=" * 80)
    
    return {
        "success": True,
        "message": f"School '{school.name}' has been deactivated successfully",
        "school_id": school.id,
        "school_name": school.name,
        "is_active": school.is_active,
        "status": school.status,
        "is_locked_by_superadmin": school.is_locked_by_superadmin,
        "performed_by": admin_name
    }