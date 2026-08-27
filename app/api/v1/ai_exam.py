from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.ai_exam_service import AIExamService
from app.core.security import get_current_user

# ================================
# Pydantic Schemas
# ================================

class ExamRequest(BaseModel):
    subject: str
    topic: str
    class_level: str
    num_questions: int = 10
    exam_type: str = "Midterm"  # Midterm, Terminal, Annual, Test
    school_level: str = "secondary"  # primary, secondary, advanced

class MarkingSchemeRequest(BaseModel):
    exam_content: str

# ================================
# API Endpoints
# ================================

router = APIRouter()

_ALLOWED_AI_HTTP = frozenset({400, 401, 403, 404, 429, 502, 503})


def _raise_if_ai_failed(result: dict) -> None:
    if result.get("success"):
        return
    status = int(result.get("http_status") or 502)
    if status not in _ALLOWED_AI_HTTP:
        status = 502
    raise HTTPException(status_code=status, detail=result.get("error", "AI request failed"))


@router.post("/generate-exam")
def generate_exam(
    request: ExamRequest,
    current_user = Depends(get_current_user)  # Require authentication
):
    """
    Generate an exam and (when possible) its marking scheme in one response.

    - **subject**: Subject name (e.g., "Mathematics", "English", "Science")
    - **topic**: Specific topic (e.g., "Algebra", "Grammar", "Photosynthesis")
    - **class_level**: Class name (e.g., "Form 3", "Std 5", "Form 6")
    - **num_questions**: Number of questions (default: 10)
    - **exam_type**: Type of exam (Midterm, Terminal, Annual, Test)
    - **school_level**: primary, secondary, or advanced
    """
    
    if not request.num_questions or request.num_questions < 1:
        raise HTTPException(status_code=400, detail="Number of questions must be at least 1")
    
    if request.num_questions > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 questions allowed")
    
    result = AIExamService.generate_exam_with_marking_scheme(
        subject=request.subject,
        topic=request.topic,
        class_level=request.class_level,
        num_questions=request.num_questions,
        exam_type=request.exam_type,
        school_level=request.school_level,
    )

    _raise_if_ai_failed(result)

    return result

@router.post("/generate-marking-scheme")
def generate_marking_scheme(
    request: MarkingSchemeRequest,
    current_user = Depends(get_current_user)
):
    """
    Generate a marking scheme for an existing exam
    """
    
    if not request.exam_content or len(request.exam_content) < 50:
        raise HTTPException(status_code=400, detail="Exam content is too short or empty")
    
    result = AIExamService.generate_marking_scheme(request.exam_content)
    
    _raise_if_ai_failed(result)

    return result

@router.get("/exam-templates")
def get_exam_templates():
    """
    Get available exam templates and examples
    """
    return {
        "exam_types": ["Midterm", "Terminal", "Annual", "Test", "Quiz"],
        "school_levels": ["primary", "secondary", "advanced"],
        "example_subjects": {
            "primary": ["Mathematics", "English", "Science", "Social Studies", "Kiswahili"],
            "secondary": ["Mathematics", "English", "Biology", "Chemistry", "Physics", "History", "Geography", "Kiswahili"],
            "advanced": ["Pure Mathematics", "Physics", "Chemistry", "Biology", "History", "Geography", "Economics", "Accountancy"]
        },
        "tips": [
            "Be specific with topics for better results",
            "Specify the number of questions you want",
            "Choose appropriate school level for age-appropriate content",
            "Each generate request returns both the exam and a marking scheme when possible",
        ]
    }