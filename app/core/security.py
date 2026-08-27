# app/core/security.py

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
from app.models.school import School
from app.models.parent import Parent
from app.models.student import Student
import logging

logger = logging.getLogger(__name__)

# ================================
# Password hashing
# ================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# ================================
# JWT Token
# ================================
SECRET_KEY = "your-super-secret-key-change-this-in-production-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug("jwt decode ok sub=%s", payload.get("sub"))
        return payload
    except JWTError as e:
        logger.debug("jwt decode failed: %s", e)
        return None

# ================================
# Helper function to get role string
# ================================
def get_role_string(role):
    """Convert Enum role to string if needed"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

# ================================
# Helper to get school level from token or database
# ================================
def get_school_level_from_token(payload: dict, db: Session) -> str:
    """Extract school_level from token or get from database"""
    school_level = payload.get("school_level")
    if school_level:
        return school_level
    
    user_id = payload.get("sub")
    user_type = payload.get("user_type")
    
    if user_type and user_type.lower() != "superadmin" and user_type.lower() != "parent":
        teacher = db.query(Teacher).filter(Teacher.id == user_id).first()
        if teacher and teacher.school_id:
            school = db.query(School).filter(School.id == teacher.school_id).first()
            if school and school.school_level:
                return school.school_level
    
    return "secondary"

# ================================
# Authentication
# ================================
security = HTTPBearer()

# ============================================================
# 🔥 ALL VALID ROLES - CASE INSENSITIVE!
# ============================================================
VALID_SCHOOL_ROLES = [
    # Kiingereza
    "Teacher", "Headmaster", "Headmistress", "Second Master", "Second Mistress", 
    "Academic", "Accountant", "Registrar", "Librarian", "Matron", "Patron",
    # Kiswahili
    "Mwalimu", "Mtaaluma", "Mwalimu Mkuu", "Mwalimu Mkuu Msaidizi",
    "Katibu", "Mhasibu", "Msimamizi",
    # Parent
    "Parent"
]

def normalize_user_type(user_type: Optional[str]) -> str:
    """Normalize user type to lowercase for consistent comparison"""
    if user_type is None:
        return ""
    return str(user_type).lower().strip()

def is_valid_role(user_type: Optional[str]) -> bool:
    """Check if user_type is valid (case-insensitive)"""
    if user_type is None:
        return False
    normalized = normalize_user_type(user_type)
    return normalized in [r.lower() for r in VALID_SCHOOL_ROLES]

def is_superadmin_type(user_type: Optional[str]) -> bool:
    """Check if user_type is SuperAdmin (case-insensitive)"""
    if user_type is None:
        return False
    normalized = normalize_user_type(user_type)
    return normalized in ["superadmin", "super_admin", "admin"]

def is_parent_type(user_type: Optional[str]) -> bool:
    """Check if user_type is Parent (case-insensitive)"""
    if user_type is None:
        return False
    normalized = normalize_user_type(user_type)
    return normalized == "parent"

# ============================================================
# 🔥 GET CURRENT USER - CASE INSENSITIVE VERSION!
# ============================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user from JWT token - REQUIRES authentication"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        logger.warning("❌ Invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user_type = payload.get("user_type")
    school_level = payload.get("school_level")

    logger.debug(
        "🔍 auth payload sub=%s user_type=%s school_level=%s",
        user_id,
        user_type,
        school_level,
    )

    user = None
    
    # ============================================================
    # 🔥 NORMALIZE USER_TYPE KWANZA!
    # ============================================================
    normalized_user_type = normalize_user_type(user_type)
    
    logger.info(f"🔍 Normalized user_type: '{normalized_user_type}' (original: '{user_type}')")

    # ============================================================
    # 🔥 1. KWA SUPERADMIN - CASE INSENSITIVE!
    # ============================================================
    if is_superadmin_type(user_type):
        logger.info(f"🔍 Looking for SuperAdmin with ID: {user_id}")
        user = db.query(SuperAdmin).filter(SuperAdmin.id == user_id).first()
        if user:
            # ✅ Ongeza attribute muhimu kwa SuperAdmin
            user.is_superadmin = True
            user.user_type = "superadmin"  # Normalized
            user.school_level = None
            # ✅ Add name attribute if missing (for consistency)
            if not hasattr(user, 'name') or user.name is None:
                user.name = user.username
            # ✅ Add username if missing
            if not hasattr(user, 'username'):
                user.username = user.email or f"superadmin_{user.id}"
            logger.info(f"✅ Superadmin authenticated: {user.username} (ID: {user.id})")
            logger.info(f"   Class: {user.__class__.__name__}")
            logger.info(f"   Name: {getattr(user, 'name', 'None')}")
            logger.info(f"   is_superadmin: {getattr(user, 'is_superadmin', 'None')}")
            return user
        else:
            logger.error(f"❌ SuperAdmin with ID {user_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Superadmin not found"
            )

    # ============================================================
    # 🔥 2. KWA PARENT - CASE INSENSITIVE!
    # ============================================================
    if is_parent_type(user_type):
        logger.info(f"🔍 Looking for Parent with ID: {user_id}")
        parent = db.query(Parent).filter(Parent.id == user_id).first()
        if parent:
            user = parent
            user.user_type = "parent"  # Normalized
            # Get school level
            if parent.school_id:
                school = db.query(School).filter(School.id == parent.school_id).first()
                user.school_level = school.school_level if school else "primary"
            else:
                user.school_level = "primary"
            # Add name if missing
            if not hasattr(user, 'name') or user.name is None:
                user.name = parent.full_name or parent.name
            logger.info(f"✅ Parent authenticated: {parent.name} (ID: {parent.id})")
            return user
        else:
            logger.error(f"❌ Parent with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Parent not found"
            )

    # ============================================================
    # 🔥 3. KWA TEACHER / SCHOOL STAFF - CASE INSENSITIVE!
    # ============================================================
    elif is_valid_role(user_type):
        logger.info(f"🔍 Looking for Teacher with ID: {user_id} (Type: {user_type})")
        user = db.query(Teacher).filter(Teacher.id == user_id).first()
        if user:
            user_role = get_role_string(user.role)
            # Store both original and normalized
            user.role = user_role
            user.user_type = normalized_user_type  # Normalized for consistency
            
            # Add school level
            if school_level:
                user.school_level = school_level
            else:
                if user.school_id:
                    school = db.query(School).filter(School.id == user.school_id).first()
                    user.school_level = school.school_level if school else "secondary"
                else:
                    user.school_level = "secondary"
            
            # Add name if missing
            if not hasattr(user, 'name') or user.name is None:
                user.name = user.full_name or user.username
            
            logger.info(f"✅ Teacher authenticated: {user.name} (ID: {user.id})")
            logger.info(f"   Role: {user_role}, Type: {normalized_user_type}")
            return user
        else:
            logger.error(f"❌ Teacher with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

    else:
        logger.error(f"❌ Invalid user type: '{user_type}' (normalized: '{normalized_user_type}')")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Invalid user type: '{user_type}'. Valid types: Teacher, Headmaster, Headmistress, Second Master, Second Mistress, Academic, Accountant, Registrar, Librarian, Matron, Patron, Mwalimu, Mtaaluma, Mwalimu Mkuu, Mwalimu Mkuu Msaidizi, Katibu, Mhasibu, Msimamizi, Parent, or Superadmin"
        )

# ============================================================
# 🔥 GET CURRENT USER OPTIONAL - CASE INSENSITIVE!
# ============================================================
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user if token exists, otherwise return None."""
    if not credentials:
        logger.debug("🔓 No token provided - public access")
        return None
    
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
        
        if payload is None:
            logger.debug("🔓 Invalid token - public access")
            return None
        
        user_id = payload.get("sub")
        user_type = payload.get("user_type")
        
        if not user_id or not user_type:
            return None
        
        # Normalize user_type
        normalized_user_type = normalize_user_type(user_type)
        
        # ============================================================
        # 🔥 SUPERADMIN - CASE INSENSITIVE!
        # ============================================================
        if is_superadmin_type(user_type):
            user = db.query(SuperAdmin).filter(SuperAdmin.id == user_id).first()
            if user:
                user.is_superadmin = True
                user.user_type = "superadmin"
                user.school_level = None
                if not hasattr(user, 'name') or user.name is None:
                    user.name = user.username
                logger.debug(f"🔐 Optional auth: Superadmin found (ID: {user_id})")
                return user
        
        # ============================================================
        # 🔥 PARENT - CASE INSENSITIVE!
        # ============================================================
        if is_parent_type(user_type):
            parent = db.query(Parent).filter(Parent.id == user_id).first()
            if parent:
                user = parent
                user.user_type = "parent"
                if parent.school_id:
                    school = db.query(School).filter(School.id == parent.school_id).first()
                    user.school_level = school.school_level if school else "primary"
                else:
                    user.school_level = "primary"
                if not hasattr(user, 'name') or user.name is None:
                    user.name = parent.full_name or parent.name
                logger.debug(f"🔐 Optional auth: Parent found (ID: {user_id})")
                return user
        
        # ============================================================
        # 🔥 TEACHER - CASE INSENSITIVE!
        # ============================================================
        elif is_valid_role(user_type):
            user = db.query(Teacher).filter(Teacher.id == user_id).first()
            if user:
                user_role = get_role_string(user.role)
                user.role = user_role
                user.user_type = normalized_user_type
                
                if user.school_id:
                    school = db.query(School).filter(School.id == user.school_id).first()
                    user.school_level = school.school_level if school else "secondary"
                else:
                    user.school_level = "secondary"
                
                if not hasattr(user, 'name') or user.name is None:
                    user.name = user.full_name or user.username
                
                logger.debug(f"🔐 Optional auth: Teacher found (ID: {user_id})")
                return user
        
        return None
        
    except Exception as e:
        logger.debug(f"🔓 Optional auth error: {e} - public access")
        return None

# ================================
# Get current user with school
# ================================
def get_current_user_with_school(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user with school information"""
    user = get_current_user(credentials, db)
    
    if hasattr(user, 'school_id') and user.school_id:
        school = db.query(School).filter(School.id == user.school_id).first()
        if school:
            user.school_name = school.name
            user.school_level = school.school_level
            user.school_type = school.school_type
    
    return user

# ============================================================
# 🔥 GET CURRENT PARENT
# ============================================================
def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current parent from JWT token - MAALUM KWA PARENT"""
    user = get_current_user(credentials, db)
    
    if not hasattr(user, 'user_type') or user.user_type != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Parent account required."
        )
    
    parent = db.query(Parent).filter(Parent.id == user.id).first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent not found"
        )
    
    return parent

# ============================================================
# 🔥 GET CURRENT STUDENT PARENT
# ============================================================
def get_current_parent_for_student(
    student_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current parent and verify they have access to the student"""
    parent = get_current_parent(credentials, db)
    
    from app.models.parent_child import ParentChild
    child_link = db.query(ParentChild).filter(
        ParentChild.parent_id == parent.id,
        ParentChild.student_id == student_id,
        ParentChild.is_active == True
    ).first()
    
    if not child_link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this student"
        )
    
    return parent

# ============================================================
# 🔥 HELPER FUNCTIONS FOR FRONTEND
# ============================================================

def get_user_display_type(user_type: str) -> str:
    """Get display version of user type"""
    normalized = normalize_user_type(user_type)
    mapping = {
        "superadmin": "Super Admin",
        "admin": "Super Admin",
        "parent": "Mzazi",
        "teacher": "Mwalimu",
        "headmaster": "Mwalimu Mkuu",
        "headmistress": "Mwalimu Mkuu",
        "academic": "Mtaaluma",
        "accountant": "Mhasibu"
    }
    return mapping.get(normalized, user_type)

def is_superadmin_user(user) -> bool:
    """Check if user object is SuperAdmin"""
    if not user:
        return False
    
    # Check attribute
    if hasattr(user, 'is_superadmin') and user.is_superadmin:
        return True
    
    # Check class
    if hasattr(user, '__class__') and user.__class__.__name__ == 'SuperAdmin':
        return True
    
    # Check ID
    if hasattr(user, 'id') and user.id == 1:
        return True
    
    # Check user_type
    if hasattr(user, 'user_type') and is_superadmin_type(user.user_type):
        return True
    
    return False

# ============================================================
# 🔥 DEBUG FUNCTION
# ============================================================

def debug_user_info(user) -> dict:
    """Get debug info about a user object"""
    if not user:
        return {"error": "User is None"}
    
    info = {
        "class": user.__class__.__name__,
        "id": getattr(user, 'id', None),
        "username": getattr(user, 'username', None),
        "name": getattr(user, 'name', None),
        "email": getattr(user, 'email', None),
        "user_type": getattr(user, 'user_type', None),
        "role": getattr(user, 'role', None),
        "is_superadmin": getattr(user, 'is_superadmin', None),
        "school_id": getattr(user, 'school_id', None),
        "school_level": getattr(user, 'school_level', None),
        "is_superadmin_user": is_superadmin_user(user),
    }
    
    # Add all attributes
    for attr in dir(user):
        if not attr.startswith('_'):
            try:
                value = getattr(user, attr)
                if not callable(value):
                    info[attr] = value
            except:
                pass
    
    return info