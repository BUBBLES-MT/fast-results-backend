# ============================================================
# 🔥 MODELS ZOTE ZA MFUMO
# ============================================================

# 🔥 CORE MODELS
from app.models.school import School
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.subject import Subject
from app.models.superadmin import SuperAdmin

# 🔥 ACADEMIC MODELS
from app.models.mark import Mark
from app.models.student_report import StudentReport
from app.models.teacher_subject import TeacherSubject
from app.models.association_tables import teacher_classes

# 🔥 PARENT MODELS (MPYA!)
from app.models.parent import Parent
from app.models.parent_child import ParentChild

# 🔥 PAYMENT & SUBSCRIPTION
from app.models.payment_transaction import PaymentTransaction

# 🔥 HOMEPAGE & CONTENT
from app.models.homepage import SidebarItem, HomepageSlide, HomepageAd
from app.models.generated_report import GeneratedReport

# 🔥 NOTIFICATIONS
from app.models.notification import Notification


# ============================================================
# 🔥 EXPORT ALL MODELS
# ============================================================

__all__ = [
    # Core
    "School",
    "Student",
    "Teacher",
    "SchoolClass",
    "Stream",
    "Subject",
    "SuperAdmin",
    
    # Academic
    "Mark",
    "StudentReport",
    "TeacherSubject",
    "teacher_classes",
    
    # Parent (MPYA!)
    "Parent",
    "ParentChild",
    
    # Payment
    "PaymentTransaction",
    
    # Homepage & Content
    "SidebarItem",
    "HomepageSlide",
    "HomepageAd",
    "GeneratedReport",
    
    # Notifications
    "Notification",
]