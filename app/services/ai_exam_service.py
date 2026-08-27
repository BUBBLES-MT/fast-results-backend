import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from openai import OpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)

load_dotenv()

# Initialize OpenAI client (new version)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _nested_openai_code(body: object) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    err = body.get("error")
    if isinstance(err, dict):
        return err.get("code") or err.get("type")
    return body.get("code")


class AIExamService:
    """Service for generating exams using AI"""
    
    @staticmethod
    def generate_exam(
        subject: str,
        topic: str,
        class_level: str,
        num_questions: int = 10,
        exam_type: str = "Midterm",
        school_level: str = "secondary"
    ) -> Dict[str, Any]:
        """
        Generate an exam using AI based on parameters
        """
        
        # Check if OpenAI is configured
        if not OPENAI_API_KEY or not client:
            return {
                "success": False,
                "error": "OpenAI API key not configured. Please add OPENAI_API_KEY to .env file"
            }
        
        # Build prompt based on school level
        level_prompts = {
            "primary": f"Generate a {exam_type} exam for Primary School {class_level} in Tanzania. Use Kiswahili language for all questions and instructions.",
            "secondary": f"Generate a {exam_type} exam for Secondary School {class_level} in Tanzania. Use English language for all questions and instructions.",
            "advanced": f"Generate an {exam_type} exam for Advanced Level {class_level} in Tanzania. Use English language for all questions and instructions."
        }
        
        # 🔥 KWA PRIMARY - TUMIA KISWAHILI
        language_instruction = "Kiswahili" if school_level == "primary" else "English"
        
        prompt = f"""
        {level_prompts.get(school_level, level_prompts['secondary'])}
        
        Subject: {subject}
        Topic: {topic}
        Number of questions: {num_questions}
        Language: {language_instruction}
        
        Please generate:
        1. Exam title
        2. Instructions for students (in {language_instruction})
        3. {num_questions} questions with clear numbering
        4. Mark allocation for each question (in {language_instruction})
        5. Total marks calculation (in {language_instruction})
        
        Format the exam professionally with clear sections.
        """
        
        try:
            # New OpenAI API v1.0+ syntax (inatumika kwa 3.x)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are an expert exam setter for schools in Tanzania. Create age-appropriate, curriculum-aligned exams in {language_instruction}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            exam_content = response.choices[0].message.content
            
            return {
                "success": True,
                "exam_content": exam_content,
                "subject": subject,
                "topic": topic,
                "class_level": class_level,
                "exam_type": exam_type,
                "school_level": school_level,
                "num_questions": num_questions,
                "language": language_instruction
            }

        except AuthenticationError:
            return {
                "success": False,
                "http_status": 503,
                "error": "OpenAI API key is invalid or revoked. Check OPENAI_API_KEY in backend .env.",
            }
        except RateLimitError as e:
            ocode = getattr(e, "code", None) or _nested_openai_code(e.body)
            if ocode == "insufficient_quota":
                msg = (
                    "OpenAI: no quota / billing not active. Add credits or a payment method at "
                    "https://platform.openai.com/account/billing — then try again."
                )
            else:
                msg = "OpenAI rate limit reached. Wait a moment and try again."
            return {"success": False, "http_status": 429, "error": msg, "openai_code": ocode}
        except (APIConnectionError, APITimeoutError) as e:
            return {
                "success": False,
                "http_status": 503,
                "error": f"Cannot reach OpenAI: {str(e)}",
            }
        except APIStatusError as e:
            status = getattr(e, "status_code", 502) or 502
            if status == 429:
                ocode = getattr(e, "code", None) or _nested_openai_code(e.body)
                if ocode == "insufficient_quota":
                    msg = (
                        "OpenAI: no quota / billing not active. Add credits at "
                        "https://platform.openai.com/account/billing"
                    )
                else:
                    msg = "OpenAI rate limit — try again shortly."
                return {"success": False, "http_status": 429, "error": msg, "openai_code": ocode}
            return {
                "success": False,
                "http_status": 502,
                "error": f"OpenAI API error ({status}): {getattr(e, 'message', str(e))}",
            }
        except Exception as e:
            return {
                "success": False,
                "http_status": 502,
                "error": f"OpenAI API error: {str(e)}",
            }

    @staticmethod
    def generate_exam_with_marking_scheme(
        subject: str,
        topic: str,
        class_level: str,
        num_questions: int = 10,
        exam_type: str = "Midterm",
        school_level: str = "secondary",
    ) -> Dict[str, Any]:
        """
        Generate exam then marking scheme in one flow (same OpenAI calls as separate endpoints).
        If marking fails after exam succeeds, exam is still returned with marking_scheme_error set.
        """
        exam_res = AIExamService.generate_exam(
            subject=subject,
            topic=topic,
            class_level=class_level,
            num_questions=num_questions,
            exam_type=exam_type,
            school_level=school_level,
        )
        if not exam_res.get("success"):
            return exam_res

        exam_content = (exam_res.get("exam_content") or "").strip()
        merged: Dict[str, Any] = dict(exam_res)

        if len(exam_content) < 50:
            merged["marking_scheme"] = None
            merged["marking_scheme_note"] = (
                "Mtihani ulivyotolewa ni mfupi mno kwa marking scheme ya kiotomatiki. "
                "Jaribu tena au tumia kitufe cha kuunda marking scheme peke yake."
            )
            return merged

        ms_res = AIExamService.generate_marking_scheme(exam_content, school_level)
        if ms_res.get("success"):
            merged["marking_scheme"] = ms_res.get("marking_scheme")
        else:
            merged["marking_scheme"] = None
            merged["marking_scheme_error"] = ms_res.get("error", "Marking scheme generation failed")
            merged["marking_scheme_http_status"] = ms_res.get("http_status")

        return merged

    @staticmethod
    def generate_marking_scheme(exam_content: str, school_level: str = "secondary") -> Dict[str, Any]:
        """
        Generate a marking scheme for an existing exam
        """
        
        # Check if OpenAI is configured
        if not OPENAI_API_KEY or not client:
            return {
                "success": False,
                "http_status": 503,
                "error": "OpenAI API key not configured",
            }

        # 🔥 KWA PRIMARY - TUMIA KISWAHILI
        language = "Kiswahili" if school_level == "primary" else "English"

        prompt = f"""
        Based on this exam, create a detailed marking scheme in {language}:
        
        {exam_content}
        
        Please provide:
        1. Mark allocation for each question (in {language})
        2. Expected answers or key points (in {language})
        3. Total marks breakdown (in {language})
        4. Grading guidelines (A, B, C, D, F based on marks) (in {language})
        """
        
        try:
            # New OpenAI API v1.0+ syntax
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are an expert examiner. Create clear, fair marking schemes in {language}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500
            )
            
            return {
                "success": True,
                "marking_scheme": response.choices[0].message.content
            }

        except AuthenticationError:
            return {
                "success": False,
                "http_status": 503,
                "error": "OpenAI API key is invalid or revoked. Check OPENAI_API_KEY in backend .env.",
            }
        except RateLimitError as e:
            ocode = getattr(e, "code", None) or _nested_openai_code(e.body)
            if ocode == "insufficient_quota":
                msg = (
                    "OpenAI: no quota / billing not active. Add credits at "
                    "https://platform.openai.com/account/billing — then try again."
                )
            else:
                msg = "OpenAI rate limit reached. Wait a moment and try again."
            return {"success": False, "http_status": 429, "error": msg, "openai_code": ocode}
        except (APIConnectionError, APITimeoutError) as e:
            return {
                "success": False,
                "http_status": 503,
                "error": f"Cannot reach OpenAI: {str(e)}",
            }
        except APIStatusError as e:
            status = getattr(e, "status_code", 502) or 502
            if status == 429:
                ocode = getattr(e, "code", None) or _nested_openai_code(e.body)
                if ocode == "insufficient_quota":
                    msg = (
                        "OpenAI: no quota / billing not active. Add credits at "
                        "https://platform.openai.com/account/billing"
                    )
                else:
                    msg = "OpenAI rate limit — try again shortly."
                return {"success": False, "http_status": 429, "error": msg, "openai_code": ocode}
            return {
                "success": False,
                "http_status": 502,
                "error": f"OpenAI API error ({status}): {getattr(e, 'message', str(e))}",
            }
        except Exception as e:
            return {
                "success": False,
                "http_status": 502,
                "error": f"OpenAI API error: {str(e)}",
            }