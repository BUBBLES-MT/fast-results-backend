# app/api/v1/primary/students/import.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.student import Student
from app.api.v1.students.import_helper import (
    parse_excel_students,
    import_students_to_db,
    create_import_template,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/primary/students", tags=["Students - Primary"])


@router.post("/import-excel")
async def import_students_excel_primary(
    school_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    ✅ Import wanafunzi wa PRIMARY kutoka Excel
    
    Format ya Excel:
    | Jina Kamili | Jinsia (M/F) | Tarehe ya Kuzaliwa | Darasa | Mkondo | Namba ya Usajili |
    """
    # Kagua file
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "File lazima iwe Excel (.xlsx au .xls)")
    
    contents = await file.read()
    
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "File ni kubwa sana (max 10MB)")
    
    # Chambua Excel
    students_data = parse_excel_students(contents)
    
    # Ingiza kwenye database
    result = import_students_to_db(
        students_data=students_data,
        school_id=school_id,
        db=db,
        SchoolClass=SchoolClass,
        Stream=Stream,
        Student=Student,
        school_level="primary",
    )
    
    return {
        "success": True,
        "level": "primary",
        **result,
    }


@router.get("/import-template")
async def download_import_template_primary(
    current_user = Depends(get_current_user),
):
    """
    ✅ Pakua template ya Excel (PRIMARY)
    """
    buffer = create_import_template(level="primary")
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=student_import_template_primary.xlsx"
        }
    )