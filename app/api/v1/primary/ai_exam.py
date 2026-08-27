from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.teacher import Teacher
from app.models.superadmin import SuperAdmin
import openai
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/primary/ai-exam", tags=["Primary AI Exam"])

# ============================================================
# 🔥 Pydantic Schemas
# ============================================================

class GenerateExamRequest(BaseModel):
    subject: str
    topic: str
    class_level: str
    num_questions: int = 10
    exam_type: str = "MIDTERM3"
    school_level: str = "primary"

class GenerateExamResponse(BaseModel):
    success: bool
    exam_content: Optional[str] = None
    marking_scheme: Optional[str] = None
    error: Optional[str] = None

# ============================================================
# 🔥 HELPER FUNCTIONS
# ============================================================

def get_role_string(role):
    """Convert role to string"""
    if role is None:
        return None
    if hasattr(role, 'value'):
        return role.value
    return str(role)

def has_primary_access(user_role: str) -> bool:
    """Check if role has PRIMARY access"""
    allowed_roles = [
        "Mwalimu Mkuu",
        "Mwalimu Mkuu Msaidizi",
        "Mtaaluma",
        "Mwalimu",
        "Teacher"
    ]
    return user_role in allowed_roles

# ============================================================
# 🔥 GENERATE EXAM - PRIMARY
# ============================================================

@router.post("/generate-exam", response_model=GenerateExamResponse)
def generate_primary_exam(
    request: GenerateExamRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 GENERATE EXAM + MARKING SCHEME - PRIMARY SCHOOL
    RUHUSU: Mwalimu, Mtaaluma, Mwalimu Mkuu, Mwalimu Mkuu Msaidizi
    """
    
    # ============================================================
    # 🔥 PERMISSION CHECK
    # ============================================================
    user_role = get_role_string(getattr(current_user, 'role', None))
    
    if not has_primary_access(user_role) and not isinstance(current_user, SuperAdmin):
        raise HTTPException(
            status_code=403,
            detail=f"Huna ruhusa. Jukumu lako: {user_role}. Inaruhusiwa: Mwalimu, Mtaaluma, Mwalimu Mkuu, Mwalimu Mkuu Msaidizi"
        )
    
    # ============================================================
    # 🔥 VALIDATE INPUT
    # ============================================================
    if not request.subject:
        raise HTTPException(status_code=400, detail="Tafadhali chagua somo")
    
    if not request.topic:
        raise HTTPException(status_code=400, detail="Tafadhali ingiza mada")
    
    if not request.class_level:
        raise HTTPException(status_code=400, detail="Tafadhali chagua darasa")
    
    if request.num_questions < 1 or request.num_questions > 50:
        raise HTTPException(status_code=400, detail="Idadi ya maswali inapaswa kuwa kati ya 1 na 50")
    
    # ============================================================
    # 🔥 GET EXAM TYPES (KISWAHILI)
    # ============================================================
    exam_type_map = {
        "MIDTERM3": "Robo Muhula",
        "MIDTERM9": "Robo Muhula ya Pili",
        "TERMINAL": "Muhula wa Kwanza",
        "ANNUAL": "Muhula wa Pili"
    }
    
    exam_type_kiswahili = exam_type_map.get(request.exam_type, request.exam_type)
    
    # ============================================================
    # 🔥 BUILD PROMPT FOR AI
    # ============================================================
    prompt = f"""
    Unda mtihani wa {request.subject} kwa wanafunzi wa Darasa la {request.class_level} (Shule ya Msingi).
    
    Mada: {request.topic}
    Aina ya Mtihani: {exam_type_kiswahili}
    Idadi ya Maswali: {request.num_questions}
    
    TAFADHALI FUATA MUUNDO HUU:
    
    1. Kichwa cha Mtihani: "{exam_type_kiswahili} - {request.subject} - Darasa la {request.class_level}"
    2. Maagizo kwa wanafunzi
    3. Maswali {request.num_questions} (alama 0-50 kwa PRIMARY)
    4. Mwisho: "Hongera! Umemaliza mtihani wako."
    
    NOTE: Hii ni SHULE YA MSINGI, alama ni 0-50, daraja ni A-E.
    
    BAADA YA MTIHANI, TAFADHALI ANDA MWONGOZO WA ALAMA.
    """
    
    # ============================================================
    # 🔥 CALL OPENAI API
    # ============================================================
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            return GenerateExamResponse(
                success=False,
                error="OpenAI API key haijapatikana. Tafadhali wasiliana na msimamizi."
            )
        
        openai_client = openai.OpenAI(api_key=openai_api_key)
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Wewe ni mwalimu mwenye uzoefu wa shule ya msingi. Unda mitihani na mwongozo wa alama kwa Kiswahili."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        # ============================================================
        # 🔥 SPLIT CONTENT INTO EXAM AND MARKING SCHEME
        # ============================================================
        exam_content = ""
        marking_scheme = ""
        
        if "MWONGOZO WA ALAMA" in content.upper():
            parts = content.split("MWONGOZO WA ALAMA")
            exam_content = parts[0].strip()
            marking_scheme = "MWONGOZO WA ALAMA" + parts[1].strip()
        elif "MARKING SCHEME" in content.upper():
            parts = content.split("MARKING SCHEME")
            exam_content = parts[0].strip()
            marking_scheme = "MARKING SCHEME" + parts[1].strip()
        else:
            # Ikiwa hakuna marking scheme, tumia yote kama mtihani
            exam_content = content
            marking_scheme = "Mwongozo wa alama haukupatikana. Tafadhali jaribu tena."
        
        return GenerateExamResponse(
            success=True,
            exam_content=exam_content,
            marking_scheme=marking_scheme
        )
        
    except openai.OpenAIError as e:
        logger.error(f"OpenAI error: {str(e)}")
        return GenerateExamResponse(
            success=False,
            error=f"Tatizo la OpenAI: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return GenerateExamResponse(
            success=False,
            error=f"Tatizo la mfumo: {str(e)}"
        )