# app/api/v1/auth/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import pytz
import secrets
import logging
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, get_password_hash
from app.core.email import email_service
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from app.models.school import School, SchoolStatus

logger = logging.getLogger(__name__)

# ============================================================
# 🔥 TIMEZONE KWA TANZANIA (UTC+3)
# ============================================================
TZ = pytz.timezone("Africa/Dar_es_Salaam")

def get_tz_now():
    """Get current time in Tanzania timezone (UTC+3)"""
    return datetime.now(TZ)


# ================================
# 🔥 PYDANTIC SCHEMAS
# ================================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_type: str
    name: str
    role: Optional[str] = None
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    school_level: Optional[str] = None
    redirect_url: Optional[str] = None
    status: Optional[str] = None
    subscription_active: Optional[bool] = None
    days_left: Optional[int] = None
    subscription_plan: Optional[str] = None
    expiry_date: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    username: str
    email: str
    password: str
    phone1: Optional[str] = None
    phone2: Optional[str] = None
    role: str = "Teacher"
    school_id: int

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class SubscriptionExpiredDetail(BaseModel):
    message: str
    school_id: int
    school_name: str
    expiry_date: Optional[str] = None
    days_overdue: Optional[int] = None
    redirect_to: str = "/payment"


# ================================
# Helper function to get role string
# ================================
def get_role_string(role):
    """Convert Enum role to string if needed"""
    if hasattr(role, 'value'):
        return role.value
    return str(role)

def get_redirect_url(school_level: str) -> str:
    """Get dashboard redirect URL based on school level"""
    if school_level == "primary":
        return "/primary/dashboard"
    elif school_level == "advanced":
        return "/advanced/dashboard"
    return "/secondary/dashboard"


# ============================================================
# 🔥 ROLES ZINAZORUHUSIWA KUINGIA MOJA KWA MOJA
# ============================================================
AUTO_APPROVED_ROLES = [
    "Mwalimu Mkuu",
    "Headmaster",
    "Headmistress",
    "Second Master",
    "Second Mistress"
]


# ============================================================
# API Endpoints
# ============================================================

router = APIRouter()


# ============================================================
# 🔥 🔥 🔥 LOGIN - PRO MAX VERSION 3.0 (SMART REDIRECT)
# ============================================================
@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login for teachers and superadmins.
    
    🔥 SMART LOGIC:
    - If subscription EXPIRED → Redirect to /payment
    - If SuperAdmin LOCKED → Show maintenance message (NO redirect to payment)
    """
    
    # ================================
    # Check if user is Teacher
    # ================================
    teacher = db.query(Teacher).filter(Teacher.username == login_data.username).first()
    if teacher and verify_password(login_data.password, teacher.password_hash):
        
        # 🔥 Check if teacher is pending approval
        if teacher.status == "pending":
            logger.warning(f"⚠️ Login attempt by pending teacher: {teacher.username} (ID: {teacher.id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ACCOUNT_PENDING",
                    "message": (
                        "📋 ACCOUNT PENDING APPROVAL\n\n"
                        f"Dear {teacher.name},\n\n"
                        "Your account is currently awaiting approval from the school administration.\n\n"
                        "🔹 What to do:\n"
                        "• Please wait for the school administrator to review your application\n"
                        "• You will receive a notification once your account is activated\n"
                        "• Contact the school directly if you need immediate assistance\n\n"
                        "📞 Need help? Contact your school administrator."
                    ),
                    "status": "pending",
                    "school_id": teacher.school_id
                }
            )
        
        # 🔥 Check if teacher is rejected
        if teacher.status == "rejected":
            logger.warning(f"⚠️ Login attempt by rejected teacher: {teacher.username} (ID: {teacher.id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ACCOUNT_REJECTED",
                    "message": (
                        "❌ REGISTRATION NOT APPROVED\n\n"
                        f"Dear {teacher.name},\n\n"
                        "We regret to inform you that your registration application "
                        "was not approved by the school administration.\n\n"
                        f"Reason: {teacher.rejection_reason or 'No specific reason provided'}\n\n"
                        "🔹 What to do:\n"
                        "• Contact the school directly for more information\n"
                        "• You may re-apply with correct information\n"
                        "• Speak to the school administrator for guidance\n\n"
                        "📞 Need help? Contact your school administrator."
                    ),
                    "status": "rejected",
                    "school_id": teacher.school_id
                }
            )
        
        # 🔥 Check if teacher is suspended
        if teacher.status == "suspended":
            logger.warning(f"⚠️ Login attempt by suspended teacher: {teacher.username} (ID: {teacher.id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ACCOUNT_SUSPENDED",
                    "message": (
                        "🔒 ACCOUNT SUSPENDED\n\n"
                        f"Dear {teacher.name},\n\n"
                        "Your account has been temporarily suspended.\n\n"
                        "🔹 What to do:\n"
                        "• Contact the school administrator for more information\n"
                        "• Your school administration will guide you on next steps\n"
                        "• This is a temporary measure for review\n\n"
                        "📞 Need help? Contact your school administrator."
                    ),
                    "status": "suspended",
                    "school_id": teacher.school_id
                }
            )
        
        # Check if teacher account is active
        if not teacher.active:
            logger.warning(f"⚠️ Login attempt by inactive teacher: {teacher.username} (ID: {teacher.id})")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ACCOUNT_INACTIVE",
                    "message": (
                        "⏸️ ACCOUNT INACTIVE\n\n"
                        f"Dear {teacher.name},\n\n"
                        "Your account is currently inactive.\n\n"
                        "🔹 What to do:\n"
                        "• Contact the school administrator to reactivate your account\n"
                        "• Ensure all your details are up to date\n"
                        "• The school administration will assist you\n\n"
                        "📞 Need help? Contact your school administrator."
                    )
                }
            )
        
        # Get school information
        school = db.query(School).filter(School.id == teacher.school_id).first()
        
        if school:
            # ============================================================
            # 🔥🔥🔥 SMART CHECK: EXPIRED vs LOCKED
            # ============================================================
            
            # FIRST: Check if subscription is expired
            is_expired = False
            days_overdue = 0
            expiry_date_str = None
            plan_name = "N/A"
            
            if school.subscription_expires_at:
                now = get_tz_now()
                expires = school.subscription_expires_at
                if expires.tzinfo is None:
                    expires = TZ.localize(expires)
                if expires < now:
                    is_expired = True
                    days_overdue = (now - expires).days
                    expiry_date_str = expires.isoformat()
                    plan_name = school.subscription_plan.value if school.subscription_plan else "N/A"
            
            # ============================================================
            # 🔥 CASE 1: SUBSCRIPTION EXPIRED → REDIRECT TO PAYMENT
            # ============================================================
            if is_expired:
                logger.warning(f"🔴 Login blocked for school {school.name} (ID: {school.id}) - SUBSCRIPTION EXPIRED. Days overdue: {days_overdue}")
                
                message = (
                    "⚠️ SERVICE INTERRUPTED - ACCOUNT UPDATE REQUIRED\n\n"
                    "═══════════════════════════════════════════════════════════\n"
                    f"  School: {school.name}\n"
                    "═══════════════════════════════════════════════════════════\n\n"
                    
                    "Dear School Community,\n\n"
                    "We are currently performing a scheduled system update on your "
                    "school's account. This is a standard procedure to ensure all "
                    "services remain secure, fast, and reliable.\n\n"
                    
                    "📋 UPDATE DETAILS:\n"
                    "──────────────────────────────────────────────────────────\n"
                    f"  • Status: System update in progress\n"
                    f"  • Days since update started: {days_overdue} days ago\n"
                    f"  • Previous plan: {plan_name}\n"
                    f"  • Estimated completion: 24-48 hours after confirmation\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "🔹 WHAT YOU NEED TO DO:\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  1️⃣ Contact your school management to complete the update\n"
                    "  2️⃣ The system update requires a simple confirmation\n"
                    "  3️⃣ Once confirmed, services will be restored immediately\n"
                    "  4️⃣ You will receive a notification when complete\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "🔹 BENEFITS OF THIS UPDATE:\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  ✅ Improved system performance\n"
                    "  ✅ Enhanced security features\n"
                    "  ✅ New features and improvements\n"
                    "  ✅ Faster response times\n"
                    "  ✅ Better user experience\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "📞 NEED ASSISTANCE?\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  📧 Email: support@masifastresults.com\n"
                    "  📞 Phone: +255 700 000 000\n"
                    "  🕐 Hours: Monday - Friday, 8:00 AM - 6:00 PM (EAT)\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "We apologize for any inconvenience and appreciate your patience "
                    "as we work to improve your experience. Thank you for being part "
                    "of the MASI FAST RESULTS community! 🚀"
                )
                
                # ✅ REDIRECT TO PAYMENT PAGE!
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "SUBSCRIPTION_EXPIRED",
                        "message": message,
                        "school_id": school.id,
                        "school_name": school.name,
                        "expiry_date": expiry_date_str,
                        "days_overdue": days_overdue,
                        "redirect_to": "/payment",
                        "plan": plan_name,
                        "support_email": "support@masifastresults.com",
                        "support_phone": "+255 700 000 000"
                    }
                )
            
            # ============================================================
            # 🔥 CASE 2: SUPERADMIN LOCKED → MAINTENANCE MESSAGE (NO PAYMENT)
            # ============================================================
            if school.is_locked_by_superadmin:
                logger.warning(f"🔒 Login blocked for school {school.name} (ID: {school.id}) - LOCKED BY SUPERADMIN")
                
                message = (
                    "🔒 SYSTEM MAINTENANCE IN PROGRESS\n\n"
                    "═══════════════════════════════════════════════════════════\n"
                    f"  School: {school.name}\n"
                    "═══════════════════════════════════════════════════════════\n\n"
                    
                    "Dear School Community,\n\n"
                    "We are currently performing scheduled system maintenance on "
                    "your school's account to improve security and performance.\n\n"
                    
                    "📋 MAINTENANCE DETAILS:\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  • Status: Maintenance in progress\n"
                    "  • Estimated completion: 24 hours\n"
                    "  • Action required: None - automated process\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "🔹 WHAT TO EXPECT:\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  1️⃣ Services will be restored automatically\n"
                    "  2️⃣ You will be notified when complete\n"
                    "  3️⃣ No action required from your side\n"
                    "  4️⃣ All data remains secure\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "🔹 MAINTENANCE BENEFITS:\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  ✅ Improved system performance\n"
                    "  ✅ Enhanced security\n"
                    "  ✅ Bug fixes and improvements\n"
                    "  ✅ Better user experience\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "📞 NEED ASSISTANCE?\n"
                    "──────────────────────────────────────────────────────────\n"
                    "  📧 Email: support@masifastresults.com\n"
                    "  📞 Phone: +255 700 000 000\n"
                    "  🕐 Hours: Monday - Friday, 8:00 AM - 6:00 PM (EAT)\n"
                    "──────────────────────────────────────────────────────────\n\n"
                    
                    "Thank you for your patience and understanding. "
                    "We'll be back online soon! 🚀"
                )
                
                # ✅ NO REDIRECT TO PAYMENT - JUST MAINTENANCE MESSAGE!
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "SYSTEM_MAINTENANCE",
                        "message": message,
                        "school_id": school.id,
                        "school_name": school.name,
                        "redirect_to": None,
                        "support_email": "support@masifastresults.com",
                        "support_phone": "+255 700 000 000"
                    }
                )
            
            logger.info(f"✅ Login successful: {teacher.username} -> {school.name} (ID: {school.id})")
        
        # Get role as string (handle Enum)
        role_value = get_role_string(teacher.role)
        
        # Get school level (default to 'secondary' if not set)
        school_level = school.school_level if school and school.school_level else "secondary"
        redirect_url = get_redirect_url(school_level)
        
        # ✅ Include school_id in token for frontend
        access_token = create_access_token(
            data={
                "sub": str(teacher.id), 
                "user_type": role_value,
                "school_level": school_level,
                "school_id": teacher.school_id
            }
        )
        
        # ✅ Calculate days left - WITH TIMEZONE FIX!
        now = get_tz_now()
        days_left = 0
        subscription_active = True
        expiry_date_str = None
        if school and school.subscription_expires_at:
            expires = school.subscription_expires_at
            if expires.tzinfo is None:
                expires = TZ.localize(expires)
            days_left = max(0, (expires - now).days)
            subscription_active = school.is_subscription_active()
            expiry_date_str = expires.isoformat()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=teacher.id,
            user_type=role_value,
            name=teacher.name,
            role=role_value,
            school_id=teacher.school_id,
            school_name=school.name if school else None,
            school_level=school_level,
            redirect_url=redirect_url,
            status=teacher.status,
            subscription_active=subscription_active,
            days_left=days_left,
            subscription_plan=school.subscription_plan.value if school and school.subscription_plan else None,
            expiry_date=expiry_date_str
        )
    
    # ================================
    # Check if user is Superadmin
    # ================================
    superadmin = db.query(SuperAdmin).filter(SuperAdmin.username == login_data.username).first()
    if superadmin and verify_password(login_data.password, superadmin.password_hash):
        
        # Check if superadmin account is active
        if not superadmin.is_active:
            logger.warning(f"⚠️ Login attempt by inactive superadmin: {superadmin.username} (ID: {superadmin.id})")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is deactivated. Contact system administrator."
            )
        
        # Create access token for superadmin (no subscription checks)
        access_token = create_access_token(
            data={"sub": str(superadmin.id), "user_type": "Superadmin"}
        )
        
        logger.info(f"✅ Superadmin login successful: {superadmin.username} (ID: {superadmin.id})")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=superadmin.id,
            user_type="Superadmin",
            name=superadmin.name,
            role="Superadmin",
            school_id=None,
            school_name=None,
            school_level=None,
            redirect_url="/superadmin",
            status="active",
            subscription_active=True,
            days_left=None,
            subscription_plan=None,
            expiry_date=None
        )
    
    # ================================
    # Invalid credentials
    # ================================
    logger.warning(f"⚠️ Failed login attempt for username: {login_data.username}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "INVALID_CREDENTIALS",
            "message": (
                "❌ LOGIN FAILED\n\n"
                "The username or password you entered is incorrect.\n\n"
                "🔹 What to do:\n"
                "• Check your username and password and try again\n"
                "• If you forgot your password, use the 'Forgot Password' option\n"
                "• Contact your school administrator if you need assistance\n\n"
                "📞 Need help?\n"
                "📧 Email: support@masifastresults.com\n"
                "📞 Phone: +255 700 000 000"
            )
        }
    )


# ============================================================
# 🔥 REGISTER - AUTO-APPROVED KWA WAKUU PEKEE!
# ============================================================
@router.post("/register")
def register(register_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new teacher.
    
    🔥 WATU WANAOWEKWA ACTIVE MOJA KWA MOJA:
    - Mwalimu Mkuu (Primary)
    - Headmaster (Secondary)
    - Headmistress (Secondary)
    - Second Master (Secondary)
    - Second Mistress (Secondary)
    
    🔥 WALIMU WENGINE:
    - WANAWEKWA PENDING (WANAHITAJI APPROVAL)
    """
    
    # Check if school exists
    school = db.query(School).filter(School.id == register_data.school_id).first()
    if not school:
        logger.error(f"❌ Registration failed: School ID {register_data.school_id} not found")
        raise HTTPException(status_code=404, detail="School not found")
    
    # Check if school is locked by superadmin
    if school.is_locked_by_superadmin:
        logger.warning(f"❌ Registration blocked: School {school.name} (ID: {school.id}) is locked")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "REGISTRATION_UNAVAILABLE",
                "message": (
                    "🔒 REGISTRATION TEMPORARILY UNAVAILABLE\n\n"
                    "Dear Applicant,\n\n"
                    "We are currently performing scheduled system maintenance on this "
                    "school's account. New registrations are temporarily suspended.\n\n"
                    "🔹 What to do:\n"
                    "• Please try again later\n"
                    "• The school management has been notified\n"
                    "• Services will be restored shortly\n\n"
                    "📞 Need help? Contact your school administrator."
                )
            }
        )
    
    # Check if subscription expired
    if not school.is_subscription_active():
        now = get_tz_now()
        days_overdue = 0
        if school.subscription_expires_at:
            expires = school.subscription_expires_at
            if expires.tzinfo is None:
                expires = TZ.localize(expires)
            days_overdue = max(0, (now - expires).days)
        
        logger.warning(f"❌ Registration blocked: School {school.name} (ID: {school.id}) subscription expired. Days overdue: {days_overdue}")
        
        raise HTTPException(
            status_code=402,
            detail={
                "error": "REGISTRATION_UNAVAILABLE",
                "message": (
                    "⚠️ REGISTRATION TEMPORARILY UNAVAILABLE\n\n"
                    "Dear Applicant,\n\n"
                    "We are currently performing system maintenance on this "
                    "school's account. New registrations are temporarily suspended.\n\n"
                    "🔹 What to do:\n"
                    "• Please try again later\n"
                    "• The school management has been notified\n"
                    "• Services will be restored shortly\n\n"
                    "📞 Need help? Contact your school administrator."
                ),
                "school_id": school.id,
                "school_name": school.name,
                "days_overdue": days_overdue
            }
        )
    
    # Check if username exists
    existing = db.query(Teacher).filter(Teacher.username == register_data.username).first()
    if existing:
        logger.warning(f"❌ Registration failed: Username '{register_data.username}' already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email exists
    existing_email = db.query(Teacher).filter(Teacher.email == register_data.email).first()
    if existing_email:
        logger.warning(f"❌ Registration failed: Email '{register_data.email}' already exists")
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # 🔥 Check if teacher already active in another school
    existing_active = db.query(Teacher).filter(
        Teacher.email == register_data.email,
        Teacher.status == "active"
    ).first()
    
    if existing_active:
        logger.warning(f"❌ Registration failed: Teacher with email '{register_data.email}' already active in another school")
        raise HTTPException(
            status_code=400,
            detail="Teacher with this email is already active in another school."
        )
    
    # 🔥 ANGAHA KAMA MWALIMU NI MKUU WA SHULE (AUTO-APPROVED)
    is_auto_approved = register_data.role in AUTO_APPROVED_ROLES
    
    # 🔥 UNDA MWALIMU
    new_teacher = Teacher(
        name=register_data.name,
        username=register_data.username,
        email=register_data.email,
        phone1=register_data.phone1,
        phone2=register_data.phone2,
        role=register_data.role,
        school_id=register_data.school_id,
        status="active" if is_auto_approved else "pending",
        active=True if is_auto_approved else False,
        approved_by=None,
        approved_at=get_tz_now() if is_auto_approved else None,
        rejection_reason=None
    )
    new_teacher.set_password(register_data.password)
    
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    
    # 🔥 UJUMBE KULINGANA NA AINA YA MWALIMU
    if is_auto_approved:
        message = (
            "✅ REGISTRATION SUCCESSFUL!\n\n"
            f"Dear {register_data.name},\n\n"
            "Your registration has been completed successfully. "
            f"You are now registered as {register_data.role}.\n\n"
            "🔹 What to do next:\n"
            "• Login using your username and password\n"
            "• Complete your profile information\n"
            "• Start managing your school\n\n"
            "📞 Need help? Contact support@masifastresults.com"
        )
        status_text = "active"
        logger.info(f"👑 {register_data.role} registered (auto-approved): {new_teacher.name} (ID: {new_teacher.id}) - School: {school.name}")
    else:
        message = (
            "✅ REGISTRATION SUCCESSFUL - PENDING APPROVAL\n\n"
            f"Dear {register_data.name},\n\n"
            "Your registration has been completed successfully and is now "
            "awaiting approval from the school administration.\n\n"
            "🔹 What to do next:\n"
            "• Wait for the school administrator to review your application\n"
            "• You will receive a notification once approved\n"
            "• Contact the school directly if you need assistance\n\n"
            "📞 Need help? Contact your school administrator."
        )
        status_text = "pending"
        logger.info(f"📝 New teacher registered (pending): {new_teacher.name} (ID: {new_teacher.id}) - School: {school.name}")
    
    return {
        "message": message,
        "teacher_id": new_teacher.id,
        "status": status_text,
        "school_id": school.id,
        "school_name": school.name,
        "school_level": school.school_level,
        "role": register_data.role
    }


# ============================================================
# 🔥🔥🔥 FORGOT PASSWORD - REDIS IMETENGWA! 🔥🔥🔥
# ============================================================

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Send password reset email to user
    
    🔥 REDIS IMETENGWA KABISA! HAKUNA HUSIANO NA REDIS!
    Token inahifadhiwa kwenye DATABASE (Teacher/User model)
    """
    try:
        # 🔥 Find user by email (Teacher or SuperAdmin)
        user = db.query(Teacher).filter(Teacher.email == request.email).first()
        is_superadmin = False
        
        if not user:
            user = db.query(SuperAdmin).filter(SuperAdmin.email == request.email).first()
            if user:
                is_superadmin = True
        
        if not user:
            # Don't reveal if user exists or not (security)
            logger.info(f"🔐 Password reset requested for non-existent email: {request.email}")
            return {
                "message": "If your email is registered, you will receive a password reset link"
            }
        
        # 🔥 Check if user is active
        if hasattr(user, 'status') and user.status != "active":
            logger.warning(f"⚠️ Password reset requested for inactive user: {request.email}")
            return {
                "message": "If your email is registered, you will receive a password reset link"
            }
        
        # 🔥 Generate reset token
        token = secrets.token_urlsafe(32)
        
        # 🔥🔥🔥 HAPA NDIO TOKEN INAHIFADHIWA KWENYE DATABASE (SI REDIS!) 🔥🔥🔥
        user.reset_token = token
        user.reset_token_expires = get_tz_now() + timedelta(hours=1)
        db.commit()
        
        # 🔥 Get username
        username = user.name or user.username or "User"
        
        # 🔥 Send email
        email_sent = email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=token,
            username=username
        )
        
        if email_sent:
            logger.info(f"✅ Password reset email sent to {user.email}")
            return {
                "message": "Password reset link has been sent to your email",
                "email": user.email
            }
        else:
            logger.error(f"❌ Failed to send password reset email to {user.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email. Please try again later."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Forgot password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred. Please try again later."
        )


# ============================================================
# 🔥🔥🔥 RESET PASSWORD - REDIS IMETENGWA! 🔥🔥🔥
# ============================================================

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using token from email
    
    🔥 REDIS IMETENGWA KABISA! Token inathibitishwa kutoka DATABASE!
    """
    try:
        # 🔥 Validate passwords match
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # 🔥 Validate password strength
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters"
            )
        
        # 🔥🔥🔥 HAPA TOKEN INATHIBITISHWA KUTOKA DATABASE (SI REDIS!) 🔥🔥🔥
        # Find user by token
        user = db.query(Teacher).filter(
            Teacher.reset_token == request.token,
            Teacher.reset_token_expires > get_tz_now()
        ).first()
        
        if not user:
            user = db.query(SuperAdmin).filter(
                SuperAdmin.reset_token == request.token,
                SuperAdmin.reset_token_expires > get_tz_now()
            ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # 🔥 Update password
        user.password_hash = get_password_hash(request.new_password)
        user.updated_at = get_tz_now()
        
        # 🔥 Clear reset token (one-time use)
        user.reset_token = None
        user.reset_token_expires = None
        
        db.commit()
        
        logger.info(f"✅ Password reset successful for user: {user.email}")
        
        return {
            "message": "Password reset successful. You can now login with your new password."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred. Please try again later."
        )


# ============================================================
# 🔥🔥🔥 VALIDATE RESET TOKEN - REDIS IMETENGWA! 🔥🔥🔥
# ============================================================

@router.get("/validate-reset-token/{token}")
async def validate_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate if a reset token is still valid (for frontend)
    
    🔥 REDIS IMETENGWA KABISA! Token inathibitishwa kutoka DATABASE!
    """
    # 🔥 Angalia kwenye database
    user = db.query(Teacher).filter(
        Teacher.reset_token == token,
        Teacher.reset_token_expires > get_tz_now()
    ).first()
    
    if not user:
        user = db.query(SuperAdmin).filter(
            SuperAdmin.reset_token == token,
            SuperAdmin.reset_token_expires > get_tz_now()
        ).first()
    
    if user:
        return {"valid": True, "user_id": user.id}
    else:
        return {"valid": False, "message": "Invalid or expired token"}


# ============================================================
# 🔥 GET ME - ILIYOBORESHA
# ============================================================
@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    """Get current logged in user info"""
    
    # Check if user is superadmin or teacher
    if hasattr(current_user, 'is_superadmin') and current_user.is_superadmin:
        user_type = "Superadmin"
        role = "Superadmin"
        school_level = None
        school_id = None
    else:
        user_type = get_role_string(current_user.role) if hasattr(current_user, 'role') else "Teacher"
        role = user_type
        school_id = getattr(current_user, 'school_id', None)
        # Get school level
        if school_id:
            from app.core.database import SessionLocal
            db = SessionLocal()
            school = db.query(School).filter(School.id == school_id).first()
            school_level = school.school_level if school else "secondary"
            db.close()
        else:
            school_level = "secondary"
    
    response = {
        "id": current_user.id,
        "name": current_user.name,
        "username": current_user.username,
        "email": current_user.email,
        "user_type": user_type,
        "role": role,
        "school_level": school_level,
        "status": getattr(current_user, 'status', 'active')
    }
    
    # Add school_id for teachers
    if school_id:
        response["school_id"] = school_id
    
    return response


# ============================================================
# 🔥 CHECK SUBSCRIPTION - ILIYOBORESHA
# ============================================================
@router.get("/check-subscription/{school_id}")  
def check_subscription_status(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Check subscription status for a school (for superadmin)"""
    
    # Only superadmin can check subscription status
    if not (hasattr(current_user, 'is_superadmin') and current_user.is_superadmin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    is_active = school.is_subscription_active()
    status_text, days_left = school.subscription_status()
    
    # Calculate days overdue - WITH TIMEZONE!
    now = get_tz_now()
    days_overdue = 0
    expiry_date_str = None
    if school.subscription_expires_at:
        expires = school.subscription_expires_at
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        days_overdue = max(0, (now - expires).days)
        expiry_date_str = expires.isoformat()
    
    return {
        "school_id": school.id,
        "school_name": school.name,
        "subscription_active": is_active,
        "subscription_status": status_text,
        "days_left": days_left,
        "days_overdue": days_overdue,
        "expiry_date": expiry_date_str,
        "is_locked": school.is_locked_by_superadmin,
        "plan": school.subscription_plan.value if school.subscription_plan else None,
        "school_level": school.school_level.value if school.school_level else None,
        "school_type": school.school_type.value if school.school_type else None,
        "can_login": school.can_login()
    }


# ============================================================
# 🔥 EXTEND SUBSCRIPTION - ILIYOBORESHA
# ============================================================
class ExtendSubscriptionRequest(BaseModel):
    days: int = 30
    plan: str = "monthly"

@router.post("/extend-subscription/{school_id}")
def extend_subscription(
    school_id: int,
    request: ExtendSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Extend subscription for a school (superadmin only)"""
    
    # Only superadmin can extend subscription
    if not (hasattr(current_user, 'is_superadmin') and current_user.is_superadmin):
        logger.warning(f"⚠️ Unauthorized attempt to extend subscription for school {school_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Calculate new expiry date - WITH TIMEZONE!
    now = get_tz_now()
    
    if school.subscription_expires_at:
        expires = school.subscription_expires_at
        if expires.tzinfo is None:
            expires = TZ.localize(expires)
        if expires > now:
            new_expiry = expires + timedelta(days=request.days)
        else:
            new_expiry = now + timedelta(days=request.days)
    else:
        new_expiry = now + timedelta(days=request.days)
    
    school.subscription_expires_at = new_expiry
    school.subscription_plan = request.plan
    school.is_active = True
    school.is_locked_by_superadmin = False
    
    # Update status
    if school.status == SchoolStatus.EXPIRED or school.status == SchoolStatus.INACTIVE:
        school.status = SchoolStatus.ACTIVE
    
    db.commit()
    db.refresh(school)
    
    logger.info(f"🔑 Subscription extended for school {school.name} (ID: {school.id}) by {request.days} days. New expiry: {new_expiry}")
    
    return {
        "message": f"Subscription extended by {request.days} days",
        "school_id": school.id,
        "school_name": school.name,
        "plan": request.plan,
        "days_added": request.days,
        "new_expiry_date": new_expiry.isoformat(),
        "is_active": school.is_active,
        "status": school.status.value
    }