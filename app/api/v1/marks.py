from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.responses import StreamingResponse
from xhtml2pdf import pisa
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.mark import Mark
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.school_class import SchoolClass
from app.models.school import School
from app.models.superadmin import SuperAdmin
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.student import Student
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.stream import Stream
from app.models.superadmin import SuperAdmin
from sqlalchemy import extract, or_
from pydantic import BaseModel
import pandas as pd 
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.units import mm
from io import BytesIO




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
# Pydantic Schemas
# ================================

class MarkCreate(BaseModel):
    student_id: int
    subject_id: int
    score: float
    exam_type: str
    teacher_id: Optional[int] = None

class MarkResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    student_roll_number: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None
    score: float
    exam_type: str
    teacher_id: int
    teacher_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MarkUpdate(BaseModel):
    score: float
    exam_type: Optional[str] = None

class GradeResponse(BaseModel):
    student_id: int
    student_name: str
    student_roll_number: Optional[str] = None
    subject_id: int
    subject_name: str
    score: float
    grade: str
    points: int

class StudentResultResponse(BaseModel):
    student_id: int
    student_name: str
    student_roll_number: Optional[str] = None
    exam_type: str
    subjects: List[GradeResponse]
    total_score: float
    average: float
    overall_grade: str
    points_sum: int
    division: str
    position: int
    total_students: int
    remarks: str

# ================================
# Helper Functions (Grading Logic)
# ================================

GRADE_POINTS = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "F": 5
}

def calculate_grade(score: float) -> tuple[str, int]:
    if score >= 75:
        return "A", 1
    elif score >= 65:
        return "B", 2
    elif score >= 45:
        return "C", 3
    elif score >= 30:
        return "D", 4
    else:
        return "F", 5

def calculate_division(points_sum: int, subject_count: int) -> str:
    if subject_count < 7:
        return "N/A"
    if 7 <= points_sum <= 17:
        return "I"
    elif 18 <= points_sum <= 21:
        return "II"
    elif 22 <= points_sum <= 25:
        return "III"
    elif 26 <= points_sum <= 33:
        return "IV"
    elif 34 <= points_sum <= 35:
        return "O"
    else:
        return "N/A"

def calculate_remarks(grade: str, average: float) -> str:
    if grade == "A":
        return "Excellent! Outstanding performance. / Amefanya vizuri sana!"
    elif grade == "B":
        return "Very good! Keep up the great work. / Anafanya vizuri, endelea kuboresha"
    elif grade == "C":
        return "Good. Has potential to improve. / Kawaida, anaweza kufanya vizuri zaidi"
    elif grade == "D":
        return "Satisfactory. Needs more effort. / Anakidhi, anahitaji juhudi zaidi"
    else:
        return "Needs improvement. Requires serious attention. / Ana hitaji msaada zaidi"

router = APIRouter()



# ============================================================
# PARENT REPORT AUTO-REMARKS FUNCTIONS
# Ongeza hizi kabla ya endpoint yoyote ya parent report
# ============================================================

def get_teacher_remarks_by_division(division: str, average: float) -> str:
    """Generate teacher remarks based on division - AUTO GENERATED"""
    if division == "I":
        return ("Amefaulu vizuri sana! Ana uwezo mkubwa wa kitaaluma. "
                "Aendelee kuhifadhi na kuboresha utendaji wake. "
                "Anapendekezwa kusoma masomo ya sayansi na hisabati kwa kina zaidi.")
    elif division == "II":
        return ("Amefanya vizuri. Ana msingi mzuri wa kitaaluma. "
                "Anahitaji kuongeza juhudi katika masomo anayodhoofika "
                "ili kufikia Daraja la Kwanza katika mitihani ijayo.")
    elif division == "III":
        return ("Wastani wa kuridhisha. Anaweza kufanya vizuri zaidi kwa "
                "kuongeza muda wa kusoma na kufanya marudio ya kutosha. "
                "Anahitaji mwongozo kutoka kwa walimu na wazazi.")
    elif division == "IV":
        return ("Ana hitaji msaada zaidi kitaaluma. Anapaswa kufanya kazi "
                "kwa bidii, kuhudhuria masomo ya ziada, na kuomba ushauri "
                "kutoka kwa walimu. Wazazi wanashirikiane na shule.")
    else:
        return ("Haijaweza kufikia matarajio. Anahitaji kuwa makini zaidi "
                "na masomo yake. Anapaswa kushirikiana na wazazi na walimu "
                "kuboresha tabia na utendaji.")

def get_headmaster_remarks_by_division(division: str, average: float) -> str:
    """Generate headmaster remarks based on division - AUTO GENERATED"""
    if division == "I":
        return ("Hongera kwa utendaji bora. Mtoto ana uwezo wa kuwa kwenye "
                "ngazi za juu kitaaluma. Tunamshauri aendelee kwa kasi hiyo hiyo. "
                "Shule inajivunia utendaji wake.")
    elif division == "II":
        return ("Utendaji mzuri. Tunamshauri kuongeza bidii zaidi ili kufikia "
                "Daraja la Kwanza katika mitihani ijayo. Endelea kusoma kwa bidii.")
    elif division == "III":
        return ("Wastani wa kuridhisha. Tunamshauri kufanya marudio makini na "
                "kuhudhuria masomo yote kwa umakini. Ana uwezo wa kuongeza daraja.")
    elif division == "IV":
        return ("Haijatosheleza. Tunawashauri wazazi kufuatilia kwa karibu "
                "maendeleo ya mtoto na kushirikiana na shule. Mtoto anahitaji "
                "msaada zaidi nyumbani.")
    else:
        return ("Haijaridhisha. Tunatoa wito kwa mzazi/mlezi kushirikiana na "
                "shule kumsaidia mtoto kuboresha tabia na utendaji wake kitaaluma.")

def get_exam_pair_from_term(term: str) -> tuple:
    """Get exam types based on term (I or II)"""
    term = term.strip().upper()
    if term in ("II", "MUHULA II", "2"):
        return ("MIDTERM9", "ANNUAL")
    return ("MIDTERM3", "TERMINAL")




# ============================================================
# OPTIMIZED GET MARKS - Single JOIN query (NO N+1!)
# ============================================================
@router.get("/marks", response_model=List[MarkResponse])
def get_all_marks(
    student_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    teacher_id: Optional[int] = Query(None),
    exam_type: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None),
    school_id: Optional[int] = Query(None),
    limit: Optional[int] = Query(500, description="Limit results for performance"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all marks with optional filters - OPTIMIZED with single JOIN query"""
    
    # Single query with all joins - NO N+1 problem!
    query = db.query(
        Mark.id,
        Mark.student_id,
        Mark.subject_id,
        Mark.score,
        Mark.exam_type,
        Mark.teacher_id,
        Mark.created_at,
        Student.name.label("student_name"),
        Student.roll_number.label("student_roll_number"),
        Subject.name.label("subject_name"),
        Teacher.name.label("teacher_name")
    ).join(
        Student, Mark.student_id == Student.id
    ).join(
        Subject, Mark.subject_id == Subject.id
    ).join(
        Teacher, Mark.teacher_id == Teacher.id
    )
    
    # Apply filters
    if student_id:
        query = query.filter(Mark.student_id == student_id)
    if subject_id:
        query = query.filter(Mark.subject_id == subject_id)
    if teacher_id:
        query = query.filter(Mark.teacher_id == teacher_id)
    if exam_type:
        query = query.filter(Mark.exam_type == exam_type)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    if school_id:
        query = query.filter(Student.school_id == school_id)
    
    # 🔥 IMPORTANT: ORDER BY first, THEN limit
    query = query.order_by(Mark.created_at.desc())
    
    # Apply limit after order_by
    if limit:
        query = query.limit(limit)
    
    marks = query.all()
    
    # Convert to list of dicts directly
    result = []
    for mark in marks:
        result.append(MarkResponse(
            id=mark.id,
            student_id=mark.student_id,
            student_name=mark.student_name,
            student_roll_number=mark.student_roll_number,
            subject_id=mark.subject_id,
            subject_name=mark.subject_name,
            score=mark.score,
            exam_type=mark.exam_type,
            teacher_id=mark.teacher_id,
            teacher_name=mark.teacher_name,
            created_at=mark.created_at
        ))
    
    return result

    
@router.get("/class/{class_id}/export-excel")
def export_class_results_excel(
    class_id: int,
    exam_type: str = Query(..., description="Exam type"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export class results to Excel - Clean format with all sections"""
    from app.models.school_class import SchoolClass
    from app.models.school import School
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.mark import Mark
    from datetime import datetime
    from io import BytesIO
    import pandas as pd
    from fastapi.responses import StreamingResponse
    
    def calculate_grade(mark):
        if mark >= 75: return "A", 1
        elif mark >= 65: return "B", 2
        elif mark >= 45: return "C", 3
        elif mark >= 30: return "D", 4
        else: return "F", 5

    def calculate_division(points_sum, subject_count):
        if subject_count < 7: return "N/A"
        if 7 <= points_sum <= 17: return "I"
        elif 18 <= points_sum <= 21: return "II"
        elif 22 <= points_sum <= 25: return "III"
        elif 26 <= points_sum <= 33: return "IV"
        elif 34 <= points_sum <= 35: return "O"
        else: return "N/A"
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SECONDARY SCHOOL"
    region = getattr(school, 'region', None) if school else "SINGIDA REGION"
    if not region:
        region = "SINGIDA REGION"
    
    # Get students
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    # Subjects sorted by name
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).order_by(Subject.name).all()
    subject_names = [s.name for s in subjects]
    
    # Calculate results
    results = []
    division_summary = {"I": {"M": 0, "F": 0}, "II": {"M": 0, "F": 0}, "III": {"M": 0, "F": 0}, "IV": {"M": 0, "F": 0}, "O": {"M": 0, "F": 0}}
    reg_summary = {"M": 0, "F": 0}
    
    # For subject grade summary
    subject_grade_counts = {sub: {'A': {'M': 0, 'F': 0}, 'B': {'M': 0, 'F': 0}, 'C': {'M': 0, 'F': 0}, 'D': {'M': 0, 'F': 0}, 'F': {'M': 0, 'F': 0}} for sub in subject_names}
    
    for student in students:
        marks = db.query(Mark).filter(Mark.student_id == student.id, Mark.exam_type == exam_type).all()
        if not marks:
            continue
        
        reg_summary[student.sex] += 1
        marks_dict = {m.subject_id: m.score for m in marks}
        top_marks = sorted(marks, key=lambda m: m.score, reverse=True)[:7]
        
        total = sum(m.score for m in top_marks)
        average = round(total / len(top_marks), 2) if top_marks else 0
        grade, _ = calculate_grade(average)
        points_sum = sum(calculate_grade(m.score)[1] for m in top_marks) if top_marks else 0
        division = calculate_division(points_sum, len(top_marks))
        
        subject_scores = []
        for idx, sub in enumerate(subjects):
            score = marks_dict.get(sub.id)
            subject_scores.append(score if score is not None else "")
            if score and isinstance(score, (int, float)) and score > 0:
                g, _ = calculate_grade(score)
                subject_grade_counts[sub.name][g][student.sex] += 1
        
        results.append({
            "exam_no": student.roll_number or f"S6767-{student.id:04d}",
            "name": student.name,
            "sex": student.sex,
            "subjects": subject_scores,
            "total": total,
            "average": average,
            "grade": grade,
            "points": points_sum,
            "division": division
        })
        
        if division in division_summary:
            division_summary[division][student.sex] += 1
    
    # Sort and add position
    results.sort(key=lambda x: x["average"], reverse=True)
    for i, r in enumerate(results, 1):
        r["position"] = i
    
    # ============================================================
    # 🔥 FIX: Calculate GPA and position for subjects
    # ============================================================
    grade_points = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'F': 5}
    gpa_values = []
    for sub in subject_names:
        total_points = 0
        total_students = 0
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = subject_grade_counts[sub][grade]['M'] + subject_grade_counts[sub][grade]['F']
            total_points += count * grade_points[grade]
            total_students += count
        gpa = round(total_points / total_students, 3) if total_students > 0 else 0
        gpa_values.append((sub, gpa))
    
    # 🔥 Sort by GPA (smallest GPA = strongest subject = position 1)
    gpa_values.sort(key=lambda x: x[1])
    
    # 🔥 Create position map
    position_map = {}
    for idx, (sub, _) in enumerate(gpa_values, 1):
        position_map[sub] = idx
    
    # 🔥 Get subject names in GPA-sorted order
    sorted_subject_names = [sub for sub, _ in gpa_values]
    
    # Create Excel file
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet(f"{school_class.name} Results")
        
        # --- Header ---
        month_year = datetime.now().strftime('%B %Y')
        headers = [
            "THE UNITED REPUBLIC OF TANZANIA",
            "PRESIDENT'S OFFICE",
            "REGIONAL ADMINISTRATION AND LOCAL GOVERNMENT",
            region.upper(),
            f"{school_class.name} {exam_type} RESULTS {month_year}",
            school_name.upper()
        ]
        
        header_format = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", "font_size": 18, "font_color": "blue"})
        
        total_columns = 4 + len(subject_names) + 5
        header_start_col = 1
        
        for i, line in enumerate(headers):
            worksheet.merge_range(i, header_start_col, i, header_start_col + total_columns - 1, line, header_format)
        
        startrow = len(headers) + 2
        
        # --- Formats ---
        bold_center = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter", "bg_color": "#DCE6F1"})
        normal_center = workbook.add_format({"border": 1, "align": "center", "valign": "vcenter"})
        vertical_header_blue = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter", "bg_color": "#87CEEB", "rotation": 90})
        horizontal_header_blue = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter", "bg_color": "#87CEEB"})
        bold_center_gpa_pos = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter", "bg_color": "#FFD700"})
        
        # --- Division & Registration summary ---
        startcol_div = 5
        startcol_reg = startcol_div + len(division_summary) + 4
        
        worksheet.merge_range(startrow, startcol_div, startrow, startcol_div + len(division_summary), "Division Summary", bold_center)
        div_headers = ["Sex", "I", "II", "III", "IV", "O", "Total"]
        for c, col in enumerate(div_headers):
            worksheet.write(startrow + 1, startcol_div + c, col, bold_center)
        
        div_data = [
            ["M"] + [division_summary[d]["M"] for d in ["I","II","III","IV","O"]] + [sum(division_summary[d]["M"] for d in division_summary)],
            ["F"] + [division_summary[d]["F"] for d in ["I","II","III","IV","O"]] + [sum(division_summary[d]["F"] for d in division_summary)],
            ["Total"] + [division_summary[d]["M"] + division_summary[d]["F"] for d in ["I","II","III","IV","O"]] + [sum(division_summary[d]["M"] + division_summary[d]["F"] for d in division_summary)]
        ]
        
        for r in range(len(div_data)):
            for c in range(len(div_headers)):
                worksheet.write(startrow + 2 + r, startcol_div + c, div_data[r][c], bold_center)
        
        worksheet.merge_range(startrow, startcol_reg, startrow, startcol_reg + 2, "Registration Summary", bold_center)
        reg_headers = ["Sex", "REG", "ABS"]
        for c, col in enumerate(reg_headers):
            worksheet.write(startrow + 1, startcol_reg + c, col, bold_center)
        
        reg_data = [
            ["M", reg_summary["M"], 0],
            ["F", reg_summary["F"], 0],
            ["Total", reg_summary["M"] + reg_summary["F"], 0]
        ]
        
        for r in range(len(reg_data)):
            for c in range(len(reg_headers)):
                worksheet.write(startrow + 2 + r, startcol_reg + c, reg_data[r][c], bold_center)
        
        startrow += max(len(div_data), len(reg_data)) + 4
        
        # --- MAIN STUDENT RESULTS ---
        startcol_main = 2
        table_columns = ["POSITION", "EXAM_NO", "STUDENT_NAME", "SEX"] + subject_names + ["TOTAL", "AVERAGE", "GRADE", "POINTS", "DIVISION"]
        
        df_main = pd.DataFrame([
            [i+1, s['exam_no'], s['name'], s['sex']] +
            [s['subjects'][j] for j in range(len(subject_names))] +
            [s['total'], s['average'], s['grade'], s['points'], s['division']]
            for i, s in enumerate(results)
        ], columns=table_columns)
        
        worksheet.merge_range(startrow, startcol_main, startrow, startcol_main + len(table_columns) - 1, "Student Results", bold_center)
        
        for c, col in enumerate(table_columns):
            if col in ["POSITION", "EXAM_NO", "STUDENT_NAME", "SEX"]:
                worksheet.write(startrow + 1, startcol_main + c, col, horizontal_header_blue)
            else:
                worksheet.write(startrow + 1, startcol_main + c, col, vertical_header_blue)
        
        data_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9})
        for r in range(len(df_main)):
            worksheet.write(startrow + 2 + r, startcol_main + 0, df_main.iloc[r, 0], data_format)
            worksheet.write(startrow + 2 + r, startcol_main + 1, df_main.iloc[r, 1], data_format)
            worksheet.write(startrow + 2 + r, startcol_main + 2, df_main.iloc[r, 2], data_format)
            worksheet.write(startrow + 2 + r, startcol_main + 3, df_main.iloc[r, 3], data_format)
            for c in range(4, len(table_columns)):
                worksheet.write(startrow + 2 + r, startcol_main + c, df_main.iloc[r, c], data_format)
        
        worksheet.set_column(startcol_main + 0, startcol_main + 0, 9)
        worksheet.set_column(startcol_main + 1, startcol_main + 1, 12)
        worksheet.set_column(startcol_main + 2, startcol_main + 2, 30)
        worksheet.set_column(startcol_main + 3, startcol_main + 3, 5)
        for i in range(len(subject_names)):
            worksheet.set_column(startcol_main + 4 + i, startcol_main + 4 + i, 6)
        worksheet.set_column(startcol_main + 4 + len(subject_names), startcol_main + 4 + len(subject_names), 8)
        worksheet.set_column(startcol_main + 5 + len(subject_names), startcol_main + 5 + len(subject_names), 9)
        worksheet.set_column(startcol_main + 6 + len(subject_names), startcol_main + 6 + len(subject_names), 7)
        worksheet.set_column(startcol_main + 7 + len(subject_names), startcol_main + 7 + len(subject_names), 8)
        worksheet.set_column(startcol_main + 8 + len(subject_names), startcol_main + 8 + len(subject_names), 9)
        
        startrow += len(df_main) + 4
        
        # ============================================================
        # 🔥 FIX: SUBJECT GRADE SUMMARY - Using GPA-sorted order
        # ============================================================
        startcol_sub = 5
        
        # Build data rows in GPA-sorted order
        df_sub_data = []
        for g in ['A', 'B', 'C', 'D', 'F']:
            # Male row
            male_row = [g, 'M'] + [subject_grade_counts[sub][g]['M'] for sub in sorted_subject_names]
            df_sub_data.append(male_row)
            
            # Female row
            female_row = ['', 'F'] + [subject_grade_counts[sub][g]['F'] for sub in sorted_subject_names]
            df_sub_data.append(female_row)
            
            # Total row
            total_row = ['', 'Total'] + [subject_grade_counts[sub][g]['M'] + subject_grade_counts[sub][g]['F'] for sub in sorted_subject_names]
            df_sub_data.append(total_row)
        
        # GPA row (already sorted)
        gpa_row_data = ["GPA", ""] + [gpa for _, gpa in gpa_values]
        df_sub_data.append(gpa_row_data)
        
        # POSITION row (already sorted)
        pos_row_data = ["POSITION", ""] + [position_map[sub] for sub in sorted_subject_names]
        df_sub_data.append(pos_row_data)
        
        # Create DataFrame with GPA-sorted columns
        df_sub_columns = ["Grade", "Sex"] + sorted_subject_names
        df_sub = pd.DataFrame(df_sub_data, columns=df_sub_columns)
        
        worksheet.merge_range(startrow, startcol_sub, startrow, startcol_sub + len(df_sub.columns) - 1, "Subject Grade Summary", bold_center)
        
        # Write headers
        for c, col in enumerate(df_sub.columns):
            if col in ["Grade", "Sex"]:
                worksheet.write(startrow + 1, startcol_sub + c, col, horizontal_header_blue)
            else:
                worksheet.write(startrow + 1, startcol_sub + c, col, vertical_header_blue)
        
        # Write data
        for r in range(len(df_sub)):
            for c in range(len(df_sub.columns)):
                if r >= len(df_sub) - 2:  # GPA and POSITION rows
                    worksheet.write(startrow + 2 + r, startcol_sub + c, df_sub.iloc[r, c], bold_center_gpa_pos)
                else:
                    worksheet.write(startrow + 2 + r, startcol_sub + c, df_sub.iloc[r, c], normal_center)
        
        # Set column widths
        worksheet.set_column(startcol_sub + 0, startcol_sub + 0, 12)
        worksheet.set_column(startcol_sub + 1, startcol_sub + 1, 6)
    
    output.seek(0)
    
    filename = f"class_{class_id}_results_{exam_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )






@router.get("/class/{class_id}/summary-view")
def get_class_summary_view(
    class_id: int,
    exam_type: str = Query(..., description="Exam type"),
    region: Optional[str] = Query(None, description="District/Region name - can be provided by user"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get class summary for on-screen viewing (HTML table format)
    
    Args:
        class_id: ID of the class
        exam_type: Type of exam (MIDTERM3, TERMINAL, ANNUAL, etc.)
        region: Optional region name - if not provided, tries to get from school or uses default
    """
    from app.models.school import School
    from app.models.school_class import SchoolClass
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.mark import Mark
    from datetime import datetime
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get school info
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SECONDARY SCHOOL"
    
    # 🔥 FIXED: Use region from parameter, then from school, then default
    final_region = region
    if not final_region and school:
        # Try to get region from school database field (if exists)
        final_region = getattr(school, 'region', None)
    if not final_region:
        final_region = "SINGIDA REGION"
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    # Subject list
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subject_names = [s.name for s in subjects]
    
    # Calculate results
    results = []
    division_summary = {
        "I": {"M": 0, "F": 0}, 
        "II": {"M": 0, "F": 0}, 
        "III": {"M": 0, "F": 0}, 
        "IV": {"M": 0, "F": 0}, 
        "O": {"M": 0, "F": 0}
    }
    reg_summary = {"M": 0, "F": 0}
    
    for student in students:
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type == exam_type
        ).all()
        
        if marks:
            reg_summary[student.sex] += 1
        
        marks_dict = {m.subject_id: m.score for m in marks}
        top_marks = sorted(marks, key=lambda m: m.score, reverse=True)[:7] if marks else []
        
        total = sum(m.score for m in top_marks) if top_marks else 0
        average = round(total / len(top_marks), 2) if top_marks else 0
        grade, _ = calculate_grade(average)
        points_sum = sum(calculate_grade(m.score)[1] for m in top_marks) if top_marks else 0
        division = calculate_division(points_sum, len(top_marks)) if top_marks else "N/A"
        
        subject_scores = []
        for sub in subjects:
            score = marks_dict.get(sub.id)
            subject_scores.append(score if score is not None else "")
        
        results.append({
            "student_id": student.id,
            "exam_no": student.roll_number or f"S6767-{student.id:04d}",
            "name": student.name,
            "sex": student.sex,
            "subjects": subject_scores,
            "total": total,
            "average": average,
            "grade": grade,
            "points": points_sum,
            "division": division
        })
        
        if division in division_summary and marks:
            division_summary[division][student.sex] += 1
    
    # Sort and add position
    results.sort(key=lambda x: x["average"], reverse=True)
    for i, result in enumerate(results, 1):
        result["position"] = i
    
    # Subject grade summary
    subject_grade_summary = []
    for idx, sub in enumerate(subjects):
        grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for result in results:
            score = result["subjects"][idx]
            if score and isinstance(score, (int, float)):
                grade, _ = calculate_grade(score)
                if grade in grades:
                    grades[grade] += 1
        subject_grade_summary.append({
            "subject": sub.name,
            "grades": grades
        })
     
    return {
        "school_name": school_name,
        "region": final_region,
        "class_name": school_class.name,
        "exam_type": exam_type,
        "year": datetime.now().year,
        "division_summary": {
            "I": division_summary["I"],
            "II": division_summary["II"],
            "III": division_summary["III"],
            "IV": division_summary["IV"],
            "O": division_summary["O"],
            "total_male": sum(d["M"] for d in division_summary.values()),
            "total_female": sum(d["F"] for d in division_summary.values()),
            "total_students": sum(d["M"] + d["F"] for d in division_summary.values())
        },
        "registration_summary": {
            "male_reg": reg_summary["M"],
            "female_reg": reg_summary["F"],
            "total_reg": reg_summary["M"] + reg_summary["F"]
        },
        "results": results,
        "subject_names": subject_names,
        "subject_grade_summary": subject_grade_summary
    }



@router.get("/class/{class_id}/parent-reports-pdf")
def generate_class_parent_reports_data(
    class_id: int,
    term: str = Query("I", description="Muhula: I or II"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None),
    opening_date: Optional[str] = Query(None),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Return JSON data for ALL students in a class for PDF generation"""
    
    # Auto-determine exam types based on term
    term_upper = term.strip().upper()
    if term_upper in ("II", "MUHULA II", "2"):
        exam_a = "MIDTERM9"
        exam_b = "ANNUAL"
        term_display = "II"
    else:
        exam_a = "MIDTERM3"
        exam_b = "TERMINAL"
        term_display = "I"
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SECONDARY SCHOOL"
    
    # Get district name
    final_district_name = district_name
    if not final_district_name and school:
        final_district_name = getattr(school, 'district', None)
    if not final_district_name:
        final_district_name = "_________________________"
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    # Get subjects
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subjects_list = [(s.id, s.name) for s in subjects]
    
    # Get all marks for this class
    marks = db.query(Mark).join(Student).filter(
        Student.class_id == class_id,
        Mark.exam_type.in_([exam_a, exam_b])
    ).all()
    
    # Build marks map
    marks_map = {}
    for m in marks:
        marks_map[(m.student_id, m.subject_id, m.exam_type)] = m.score
    
    # Build student subject averages
    student_subject_avg = {}
    for student in students:
        student_subject_avg[student.id] = {}
        for sub_id, sub_name in subjects_list:
            a_score = marks_map.get((student.id, sub_id, exam_a))
            b_score = marks_map.get((student.id, sub_id, exam_b))
            
            scores = [s for s in [a_score, b_score] if s is not None]
            avg = round(sum(scores) / len(scores), 2) if scores else None
            grade = calculate_grade(avg)[0] if avg else ""
            
            student_subject_avg[student.id][sub_id] = {
                "avg": avg, "a_score": a_score, "b_score": b_score, "grade": grade
            }
    
    # Calculate subject positions for all students
    subject_positions = {}
    for sub_id, sub_name in subjects_list:
        scores = []
        for student in students:
            info = student_subject_avg[student.id].get(sub_id)
            avg = info.get("avg") if info else None
            if avg is not None:
                scores.append((student.id, avg))
        scores.sort(key=lambda x: x[1], reverse=True)
        for idx, (sid, _) in enumerate(scores, start=1):
            if sub_id not in subject_positions:
                subject_positions[sub_id] = {}
            subject_positions[sub_id][sid] = idx
    
    # Calculate overall summary for each student
    summary_map = {}
    for student in students:
        avgs = []
        for sub_id, _ in subjects_list:
            info = student_subject_avg[student.id].get(sub_id)
            if info and info.get("avg") is not None:
                avgs.append(info["avg"])
        
        avgs.sort(reverse=True)
        best7 = avgs[:7]
        
        if best7:
            overall_avg = round(sum(best7) / len(best7), 2)
            points_sum = sum(calculate_grade(x)[1] for x in best7)
        else:
            overall_avg = 0
            points_sum = 0
        
        division = calculate_division(points_sum, len(best7))
        summary_map[student.id] = {"overall_avg": overall_avg, "points": points_sum, "division": division}
    
    # Calculate positions
    sorted_students = sorted(students, key=lambda s: summary_map.get(s.id, {}).get("overall_avg", 0), reverse=True)
    positions = {s.id: idx + 1 for idx, s in enumerate(sorted_students)}
    total_students = len(students)
    
    # Prepare data for each student
    students_data = []
    for student in sorted_students:
        # Prepare subject data
        subjects_data = []
        for sub_id, sub_name in subjects_list:
            info = student_subject_avg[student.id].get(sub_id, {})
            if info.get("a_score") is not None or info.get("b_score") is not None:
                # Calculate Jumla
                jumla = ""
                if info.get("a_score") is not None and info.get("b_score") is not None:
                    jumla = f"{info['a_score'] + info['b_score']:.1f}"
                elif info.get("a_score") is not None:
                    jumla = f"{info['a_score']:.1f}"
                elif info.get("b_score") is not None:
                    jumla = f"{info['b_score']:.1f}"
                
                avg_val = f"{info['avg']:.1f}" if info.get('avg') else ""
                
                grade_val = info.get('grade', '')
                if grade_val in ["A", "B"]:
                    final_grade = "A"
                elif grade_val in ["C", "D"]:
                    final_grade = "B"
                elif grade_val == "F":
                    final_grade = "C"
                else:
                    final_grade = ""
                
                # Get subject position
                subj_position = subject_positions.get(sub_id, {}).get(student.id, "")
                
                subjects_data.append({
                    "name": sub_name,
                    "a_score": info.get("a_score"),
                    "b_score": info.get("b_score"),
                    "jumla": jumla,
                    "avg": avg_val,
                    "final_grade": final_grade,
                    "position": subj_position
                })
        
        summ = summary_map.get(student.id, {})
        overall_avg = summ.get("overall_avg", 0)
        points_sum = summ.get("points", 0)
        division = summ.get("division", "N/A")
        position = positions.get(student.id, len(sorted_students))
        
        # Get class name
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        kidato = class_obj.name if class_obj else "Form 1"
        
        # Auto-generate remarks
        teacher_remarks = get_teacher_remarks_by_division(division, overall_avg)
        headmaster_remarks = get_headmaster_remarks_by_division(division, overall_avg)
        
        students_data.append({
            "id": student.id,
            "name": student.name,
            "kidato": kidato,
            "term": term_display,
            "year": year,
            "subjects": subjects_data,
            "division": division,
            "points": points_sum,
            "average": overall_avg,
            "position": position,
            "total_students": total_students,
            "teacher_remarks": teacher_remarks,
            "headmaster_remarks": headmaster_remarks,
            "teacher_name": teacher_name or "________________________",
            "headmaster_name": headmaster_name or "________________________",
            "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
            "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
            "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
            "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
            "school_name": school_name,
            "district_name": final_district_name
        })
    
    # 🔥 MUHIMU: Hii inarudi JSON, si PDF!
    return {
        "class_name": school_class.name,
        "school_name": school_name,
        "term": term_display,
        "year": year,
        "students": students_data,
        "total_students": total_students,
        "district_name": final_district_name,
        "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
        "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
        "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
        "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
        "teacher_name": teacher_name or "________________________",
        "headmaster_name": headmaster_name or "________________________"
    }




@router.get("/class/{class_id}/parent-reports-data")
def get_class_parent_reports_data(
    class_id: int,
    term: str = Query("I", description="Muhula: I or II"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None),
    opening_date: Optional[str] = Query(None),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Return JSON data for ALL students in a class for PDF generation"""
    
    # Auto-determine exam types based on term
    term_upper = term.strip().upper()
    if term_upper in ("II", "MUHULA II", "2"):
        exam_a = "MIDTERM9"
        exam_b = "ANNUAL"
        term_display = "II"
    else:
        exam_a = "MIDTERM3"
        exam_b = "TERMINAL"
        term_display = "I"
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "SECONDARY SCHOOL"
    
    # Get district name
    final_district_name = district_name
    if not final_district_name and school:
        final_district_name = getattr(school, 'district', None)
    if not final_district_name:
        final_district_name = "_________________________"
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    # Get subjects
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subjects_list = [(s.id, s.name) for s in subjects]
    
    # Get all marks for this class
    marks = db.query(Mark).join(Student).filter(
        Student.class_id == class_id,
        Mark.exam_type.in_([exam_a, exam_b])
    ).all()
    
    # Build marks map
    marks_map = {}
    for m in marks:
        marks_map[(m.student_id, m.subject_id, m.exam_type)] = m.score
    
    # Build student subject averages
    student_subject_avg = {}
    for student in students:
        student_subject_avg[student.id] = {}
        for sub_id, sub_name in subjects_list:
            a_score = marks_map.get((student.id, sub_id, exam_a))
            b_score = marks_map.get((student.id, sub_id, exam_b))
            
            scores = [s for s in [a_score, b_score] if s is not None]
            avg = round(sum(scores) / len(scores), 2) if scores else None
            grade = calculate_grade(avg)[0] if avg else ""
            
            student_subject_avg[student.id][sub_id] = {
                "avg": avg, "a_score": a_score, "b_score": b_score, "grade": grade
            }
    
    # Calculate subject positions for all students
    subject_positions = {}
    for sub_id, sub_name in subjects_list:
        scores = []
        for student in students:
            info = student_subject_avg[student.id].get(sub_id)
            avg = info.get("avg") if info else None
            if avg is not None:
                scores.append((student.id, avg))
        scores.sort(key=lambda x: x[1], reverse=True)
        for idx, (sid, _) in enumerate(scores, start=1):
            if sub_id not in subject_positions:
                subject_positions[sub_id] = {}
            subject_positions[sub_id][sid] = idx
    
    # Calculate overall summary for each student
    summary_map = {}
    for student in students:
        avgs = []
        for sub_id, _ in subjects_list:
            info = student_subject_avg[student.id].get(sub_id)
            if info and info.get("avg") is not None:
                avgs.append(info["avg"])
        
        avgs.sort(reverse=True)
        best7 = avgs[:7]
        
        if best7:
            overall_avg = round(sum(best7) / len(best7), 2)
            points_sum = sum(calculate_grade(x)[1] for x in best7)
        else:
            overall_avg = 0
            points_sum = 0
        
        division = calculate_division(points_sum, len(best7))
        summary_map[student.id] = {"overall_avg": overall_avg, "points": points_sum, "division": division}
    
    # Calculate positions
    sorted_students = sorted(students, key=lambda s: summary_map.get(s.id, {}).get("overall_avg", 0), reverse=True)
    positions = {s.id: idx + 1 for idx, s in enumerate(sorted_students)}
    total_students = len(students)
    
    # Prepare data for each student
    students_data = []
    for student in sorted_students:
        # Prepare subject data
        subjects_data = []
        for sub_id, sub_name in subjects_list:
            info = student_subject_avg[student.id].get(sub_id, {})
            if info.get("a_score") is not None or info.get("b_score") is not None:
                # Calculate Jumla
                jumla = ""
                if info.get("a_score") is not None and info.get("b_score") is not None:
                    jumla = f"{info['a_score'] + info['b_score']:.1f}"
                elif info.get("a_score") is not None:
                    jumla = f"{info['a_score']:.1f}"
                elif info.get("b_score") is not None:
                    jumla = f"{info['b_score']:.1f}"
                
                avg_val = f"{info['avg']:.1f}" if info.get('avg') else ""
                
                grade_val = info.get('grade', '')
                if grade_val in ["A", "B"]:
                    final_grade = "A"
                elif grade_val in ["C", "D"]:
                    final_grade = "B"
                elif grade_val == "F":
                    final_grade = "C"
                else:
                    final_grade = ""
                
                # Get subject position
                subj_position = subject_positions.get(sub_id, {}).get(student.id, "")
                
                subjects_data.append({
                    "name": sub_name,
                    "a_score": info.get("a_score"),
                    "b_score": info.get("b_score"),
                    "jumla": jumla,
                    "avg": avg_val,
                    "final_grade": final_grade,
                    "position": subj_position
                })
        
        summ = summary_map.get(student.id, {})
        overall_avg = summ.get("overall_avg", 0)
        points_sum = summ.get("points", 0)
        division = summ.get("division", "N/A")
        position = positions.get(student.id, len(sorted_students))
        
        # Get class name
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        kidato = class_obj.name if class_obj else "Form 1"
        
        # Auto-generate remarks
        teacher_remarks = get_teacher_remarks_by_division(division, overall_avg)
        headmaster_remarks = get_headmaster_remarks_by_division(division, overall_avg)
        
        students_data.append({
            "id": student.id,
            "name": student.name,
            "kidato": kidato,
            "term": term_display,
            "year": year,
            "subjects": subjects_data,
            "division": division,
            "points": points_sum,
            "average": overall_avg,
            "position": position,
            "total_students": total_students,
            "teacher_remarks": teacher_remarks,
            "headmaster_remarks": headmaster_remarks,
            "teacher_name": teacher_name or "________________________",
            "headmaster_name": headmaster_name or "________________________",
            "teacher_date": teacher_date or datetime.now().strftime("%Y-%m-%d"),
            "headmaster_date": headmaster_date or datetime.now().strftime("%Y-%m-%d"),
            "closing_date": closing_date or datetime.now().strftime("%Y-%m-%d"),
            "opening_date": opening_date or datetime.now().strftime("%Y-%m-%d"),
            "school_name": school_name,
            "district_name": final_district_name
        })
    
    return {
        "class_name": school_class.name,
        "school_name": school_name,
        "term": term_display,
        "year": year,
        "students": students_data,
        "total_students": total_students
    }

































# ============================================================
# OPTIMIZED MY STUDENTS ENDPOINT - FULLY FIXED! VERSION 3
# ============================================================
@router.get("/marks/my-students")
def get_my_students_marks(
    year: Optional[int] = Query(None, description="Year to filter"),
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.models.teacher import Teacher
    from app.models.teacher_subject import TeacherSubject
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.school_class import SchoolClass
    from app.models.stream import Stream
    from app.models.superadmin import SuperAdmin
    from sqlalchemy import extract, or_
    import logging
    
    logger = logging.getLogger(__name__)
    
    def apply_year_filter(query, year):
        if year:
            return query.filter(extract('year', Mark.created_at) == year)
        return query
    
    # CASE 1: SuperAdmin
    if isinstance(current_user, SuperAdmin):
        query = db.query(Mark)
        query = apply_year_filter(query, year)
        if teacher_id:
            query = query.filter(Mark.teacher_id == teacher_id)
        marks = query.all()
        return {
            "marks": [{
                "id": m.id,
                "student_id": m.student_id,
                "subject_id": m.subject_id,
                "score": m.score,
                "exam_type": m.exam_type,
                "teacher_id": m.teacher_id,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in marks]
        }
    
    # CASE 2: Teacher or Academic Staff
    if isinstance(current_user, Teacher):
        user_role = getattr(current_user, 'role', None)
        if hasattr(user_role, 'value'):
            user_role_value = user_role.value
        else:
            user_role_value = user_role if isinstance(user_role, str) else None
        
        logger.info(f"🔍 Current user role: {user_role_value}")
        
        school_id = getattr(current_user, 'school_id', None)
        if not school_id and hasattr(current_user, 'school') and current_user.school:
            school_id = current_user.school.id
        
        logger.info(f"🏫 School ID: {school_id}")
        
        admin_roles = ["Academic", "Headmaster", "Headmistress", "Second Master", "Second Mistress"]
        is_admin = user_role_value and user_role_value in admin_roles
        
        logger.info(f"🔍 Is admin? {is_admin}")
        
        # ========================================================
        # CASE 2.1: Admin roles - All marks in school
        # ========================================================
        if is_admin:
            if school_id:
                logger.info(f"👑 Admin user: {user_role_value}, School ID: {school_id}")
                logger.info(f"🔍 Filtering by teacher_id: {teacher_id}")
                
                query = db.query(
                    Mark.id,
                    Mark.student_id,
                    Mark.subject_id,
                    Mark.score,
                    Mark.exam_type,
                    Mark.teacher_id,
                    Mark.created_at,
                    Student.name.label("student_name"),
                    Student.roll_number.label("roll_number"),
                    Student.class_id,
                    SchoolClass.name.label("class_name"),
                    Student.stream_id,
                    Stream.name.label("stream_name"),
                    Subject.name.label("subject_name"),
                    Teacher.name.label("teacher_name")
                ).join(
                    Student, Mark.student_id == Student.id
                ).join(
                    Subject, Mark.subject_id == Subject.id
                ).join(
                    Teacher, Mark.teacher_id == Teacher.id
                ).join(
                    SchoolClass, Student.class_id == SchoolClass.id
                ).join(
                    Stream, Student.stream_id == Stream.id
                ).filter(
                    Student.school_id == school_id
                )
                
                if teacher_id:
                    query = query.filter(Mark.teacher_id == teacher_id)
                    logger.info(f"✅ Filtering by teacher_id: {teacher_id}")
                else:
                    logger.info(f"✅ No teacher filter - returning ALL marks in school")
                
                query = apply_year_filter(query, year)
                result = query.all()
                
                logger.info(f"📊 Found {len(result)} marks for admin")
                
                marks = []
                for row in result:
                    marks.append({
                        "id": row.id,
                        "student_id": row.student_id,
                        "student_name": row.student_name,
                        "roll_number": row.roll_number or "",
                        "subject_id": row.subject_id,
                        "subject_name": row.subject_name,
                        "class_id": row.class_id,
                        "class_name": row.class_name,
                        "stream_id": row.stream_id,
                        "stream_name": row.stream_name,
                        "exam_type": row.exam_type,
                        "score": row.score,
                        "teacher_id": row.teacher_id,
                        "teacher_name": row.teacher_name or "Unknown",
                        "created_at": row.created_at.isoformat() if row.created_at else None
                    })
                
                return {"marks": marks}
            else:
                return {"marks": [], "error": "School not found for admin user"}
        
        # ========================================================
        # 🔥🔥🔥 CASE 2.2: Regular Teacher - FIXED! 🔥🔥🔥
        # ========================================================
        else:
            # 🔥 KAMA Kuna teacher_id iliyopitishwa, tumia hiyo!
            effective_teacher_id = teacher_id if teacher_id else current_user.id
            
            logger.info(f"👨‍🏫 Regular teacher: {current_user.id}")
            logger.info(f"🔍 Effective teacher ID: {effective_teacher_id}")
            
            # Get all classes taught by this teacher
            teacher_assignments = db.query(TeacherSubject).filter(
                TeacherSubject.teacher_id == effective_teacher_id
            ).all()
            
            if not teacher_assignments:
                return {"marks": [], "message": "No classes assigned to this teacher"}
            
            # Build conditions
            class_stream_conditions = []
            subject_ids = []
            
            for assignment in teacher_assignments:
                class_stream_conditions.append(
                    (Student.class_id == assignment.class_id) & 
                    (Student.stream_id == assignment.stream_id)
                )
                subject_ids.append(assignment.subject_id)
            
            query = db.query(
                Mark.id,
                Mark.student_id,
                Mark.subject_id,
                Mark.score,
                Mark.exam_type,
                Mark.teacher_id,
                Mark.created_at,
                Student.name.label("student_name"),
                Student.roll_number.label("roll_number"),
                Student.class_id,
                SchoolClass.name.label("class_name"),
                Student.stream_id,
                Stream.name.label("stream_name"),
                Subject.name.label("subject_name"),
                Teacher.name.label("teacher_name")  # ✅ JINA LA MWALIMU!
            ).join(
                Student, Mark.student_id == Student.id
            ).join(
                Subject, Mark.subject_id == Subject.id
            ).join(
                Teacher, Mark.teacher_id == Teacher.id  # ✅ JOIN WITH TEACHER!
            ).join(
                SchoolClass, Student.class_id == SchoolClass.id
            ).join(
                Stream, Student.stream_id == Stream.id
            ).filter(
                or_(*class_stream_conditions),
                Mark.subject_id.in_(subject_ids),
                Mark.teacher_id == effective_teacher_id  # 🔥 TUMIA effective_teacher_id!
            )
            
            query = apply_year_filter(query, year)
            result = query.all()
            
            marks = []
            for row in result:
                marks.append({
                    "id": row.id,
                    "student_id": row.student_id,
                    "student_name": row.student_name,
                    "roll_number": row.roll_number or "",
                    "subject_id": row.subject_id,
                    "subject_name": row.subject_name,
                    "class_id": row.class_id,
                    "class_name": row.class_name,
                    "stream_id": row.stream_id,
                    "stream_name": row.stream_name,
                    "exam_type": row.exam_type,
                    "score": row.score,
                    "teacher_id": row.teacher_id,
                    "teacher_name": row.teacher_name or "Unknown",
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })
            
            return {"marks": marks}
    
    # CASE 3: Other user types
    return {"marks": [], "error": "Unauthorized role"}


















'''
@router.get("/marks/all-results")
def get_all_results(
    teacher_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all marks grouped by teacher, subject, class, stream"""
    from app.models.teacher import Teacher
    from app.models.superadmin import SuperAdmin
    
    user_role = get_role_string(getattr(current_user, 'role', None))
    allowed_roles = ["Academic", "Headmaster", "Headmistress", "Second Master", "Second Mistress"]
    
    if not isinstance(current_user, SuperAdmin) and user_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    school_id = getattr(current_user, 'school_id', None)
    
    # OPTIMIZED: Single query with joins
    query = db.query(
        Mark.id,
        Mark.student_id,
        Mark.subject_id,
        Mark.score,
        Mark.exam_type,
        Mark.teacher_id,
        Mark.created_at,
        Student.name.label("student_name"),
        Student.class_id,
        SchoolClass.name.label("class_name"),
        Student.stream_id,
        Stream.name.label("stream_name"),
        Subject.name.label("subject_name"),
        Teacher.name.label("teacher_name")
    ).join(
        Student, Mark.student_id == Student.id
    ).join(
        Subject, Mark.subject_id == Subject.id
    ).join(
        Teacher, Mark.teacher_id == Teacher.id
    ).join(
        SchoolClass, Student.class_id == SchoolClass.id
    ).join(
        Stream, Student.stream_id == Stream.id
    )
    
    if school_id:
        query = query.filter(Student.school_id == school_id)
    if teacher_id:
        query = query.filter(Mark.teacher_id == teacher_id)
    if year:
        query = query.filter(db.extract('year', Mark.created_at) == year)
    
    marks = query.order_by(Mark.teacher_id, Mark.subject_id, Mark.student_id).all()
    
    # Get available years
    years_query = db.query(db.extract('year', Mark.created_at).label('year')).distinct()
    if school_id:
        years_query = years_query.join(Student).filter(Student.school_id == school_id)
    years = sorted([int(y[0]) for y in years_query.all() if y[0]], reverse=True)
    
    teachers = db.query(Teacher).filter(Teacher.school_id == school_id).all() if school_id else []
    
    result = []
    for mark in marks:
        result.append({
            "id": mark.id,
            "student_id": mark.student_id,
            "student_name": mark.student_name,
            "subject_id": mark.subject_id,
            "subject_name": mark.subject_name,
            "class_id": mark.class_id,
            "class_name": mark.class_name,
            "stream_id": mark.stream_id,
            "stream_name": mark.stream_name,
            "teacher_id": mark.teacher_id,
            "teacher_name": mark.teacher_name,
            "score": mark.score,
            "exam_type": mark.exam_type,
            "created_at": mark.created_at.isoformat() if mark.created_at else None
        })
    
    return {
        "marks": result,
        "years": years,
        "teachers": [{"id": t.id, "name": t.name} for t in teachers]
    }

'''


@router.get("/marks/{mark_id}", response_model=MarkResponse)
def get_mark(mark_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get a single mark by ID"""
    mark = db.query(Mark).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")
    
    student = db.query(Student).filter(Student.id == mark.student_id).first()
    subject = db.query(Subject).filter(Subject.id == mark.subject_id).first()
    teacher = db.query(Teacher).filter(Teacher.id == mark.teacher_id).first()
    
    return MarkResponse(
        id=mark.id,
        student_id=mark.student_id,
        student_name=student.name if student else None,
        student_roll_number=student.roll_number if student else None,
        subject_id=mark.subject_id,
        subject_name=subject.name if subject else None,
        score=mark.score,
        exam_type=mark.exam_type,
        teacher_id=mark.teacher_id,
        teacher_name=teacher.name if teacher else None,
        created_at=mark.created_at
    )



@router.put("/marks/{mark_id}")
def update_mark(
    mark_id: int, 
    mark_data: MarkUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """Update a mark"""
    mark = db.query(Mark).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")
    
    if mark.teacher_id != current_user.id:
        if not isinstance(current_user, SuperAdmin):
            user_role = get_role_string(getattr(current_user, 'role', None))
            admin_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
            if user_role not in admin_roles:
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to edit this mark"
                )
    
    if mark_data.score < 0 or mark_data.score > 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100")
    
    mark.score = mark_data.score
    if mark_data.exam_type:
        mark.exam_type = mark_data.exam_type
    
    db.commit()
    db.refresh(mark)
    
    return {"message": "Mark updated successfully", "mark_id": mark.id, "score": mark.score}



@router.delete("/marks/{mark_id}")
def delete_mark(
    mark_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """Delete a mark"""
    mark = db.query(Mark).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark not found")
    
    if mark.teacher_id != current_user.id:
        if not isinstance(current_user, SuperAdmin):
            user_role = get_role_string(getattr(current_user, 'role', None))
            admin_roles = ['Headmaster', 'Headmistress', 'Second Master', 'Second Mistress', 'Academic']
            if user_role not in admin_roles:
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to delete this mark"
                )
    
    db.delete(mark)
    db.commit()
    
    return {"message": "Mark deleted successfully"}




@router.post("/marks", response_model=MarkResponse)
def create_mark(
    mark_data: MarkCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """Create a new mark"""
    
    print(f"=== CREATE MARK ===")
    print(f"Student ID: {mark_data.student_id}")
    print(f"Subject ID: {mark_data.subject_id}")
    print(f"Teacher ID: {mark_data.teacher_id}")
    print(f"Score: {mark_data.score}")
    print(f"Exam Type: {mark_data.exam_type}")
    
    student = db.query(Student).filter(Student.id == mark_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    subject = db.query(Subject).filter(Subject.id == mark_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    teacher = db.query(Teacher).filter(Teacher.id == mark_data.teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.school_id != student.school_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Teacher and student not in same school"
        )
    
    existing = db.query(Mark).filter(
        Mark.student_id == mark_data.student_id,
        Mark.subject_id == mark_data.subject_id,
        Mark.teacher_id == mark_data.teacher_id,
        Mark.exam_type == mark_data.exam_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Mark already exists for student '{student.name}' in subject '{subject.name}' for exam '{mark_data.exam_type}'"
        )
    
    if mark_data.score < 0 or mark_data.score > 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100")
    
    new_mark = Mark(
        student_id=mark_data.student_id,
        subject_id=mark_data.subject_id,
        teacher_id=mark_data.teacher_id,
        score=mark_data.score,
        exam_type=mark_data.exam_type
    )
    
    db.add(new_mark)
    db.commit()
    db.refresh(new_mark)
    
    print(f"Mark created successfully with ID: {new_mark.id}")
    
    return {
        "id": new_mark.id,
        "student_id": new_mark.student_id,
        "student_name": student.name,
        "student_roll_number": student.roll_number,
        "subject_id": new_mark.subject_id,
        "subject_name": subject.name,
        "score": new_mark.score,
        "exam_type": new_mark.exam_type,
        "teacher_id": new_mark.teacher_id,
        "teacher_name": teacher.name,
        "created_at": new_mark.created_at
    }



@router.get("/exam-types")
def get_exam_types(
    school_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all available exam types"""
    
    query = db.query(Mark.exam_type).distinct()
    
    if school_id:
        query = query.join(Student).filter(Student.school_id == school_id)
    
    exam_types = [et[0] for et in query.order_by(Mark.exam_type).all()]
    
    if not exam_types:
        exam_types = ["MIDTERM3", "MIDTERM9", "TERMINAL", "ANNUAL", "JOINT MOCK"]
    
    return {"exam_types": exam_types}



@router.get("/my-students-list")
def get_my_students_list(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get list of students that a teacher teaches (for dropdown/selection)"""
    from app.models.teacher import Teacher
    from app.models.teacher_subject import TeacherSubject
    from app.models.student import Student
    from app.models.school_class import SchoolClass
    from app.models.stream import Stream
    from sqlalchemy import or_
    
    if not isinstance(current_user, Teacher):
        raise HTTPException(status_code=403, detail="Only teachers can access this endpoint")
    
    user_role = getattr(current_user, 'role', None)
    user_role_value = user_role.value if user_role else None
    
    # Kwa admin roles, warudishe students wote wa shule
    admin_roles = ["Academic", "Headmaster", "Headmistress", "Second Master", "Second Mistress"]
    if user_role_value in admin_roles:
        school_id = getattr(current_user, 'school_id', None)
        if school_id:
            students = db.query(
                Student.id,
                Student.name,
                Student.roll_number,
                Student.class_id,
                SchoolClass.name.label("class_name"),
                Student.stream_id,
                Stream.name.label("stream_name")
            ).join(
                SchoolClass, Student.class_id == SchoolClass.id
            ).join(
                Stream, Student.stream_id == Stream.id
            ).filter(
                Student.school_id == school_id
            ).all()
            
            return {
                "students": [{
                    "id": s.id,
                    "name": s.name,
                    "roll_number": s.roll_number,
                    "class_id": s.class_id,
                    "class_name": s.class_name,
                    "stream_id": s.stream_id,
                    "stream_name": s.stream_name
                } for s in students]
            }
    
    # Kwa teacher wa kawaida
    teacher_assignments = db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == current_user.id
    ).all()
    
    if not teacher_assignments:
        return {"students": [], "message": "No classes assigned"}
    
    # Build conditions
    class_stream_conditions = []
    for assignment in teacher_assignments:
        class_stream_conditions.append(
            (Student.class_id == assignment.class_id) & 
            (Student.stream_id == assignment.stream_id)
        )
    
    students = db.query(
        Student.id,
        Student.name,
        Student.roll_number,
        Student.class_id,
        SchoolClass.name.label("class_name"),
        Student.stream_id,
        Stream.name.label("stream_name")
    ).join(
        SchoolClass, Student.class_id == SchoolClass.id
    ).join(
        Stream, Student.stream_id == Stream.id
    ).filter(
        or_(*class_stream_conditions)
    ).distinct().all()
    
    return {
        "students": [{
            "id": s.id,
            "name": s.name,
            "roll_number": s.roll_number,
            "class_id": s.class_id,
            "class_name": s.class_name,
            "stream_id": s.stream_id,
            "stream_name": s.stream_name
        } for s in students]
    }



# ================================
# Student Results & Grading
# ================================

@router.get("/students/{student_id}/results/{exam_type}", response_model=StudentResultResponse)
def get_student_results(
    student_id: int,
    exam_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get complete results for a specific student by exam type"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    marks = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type == exam_type
    ).all()
    
    if not marks:
        raise HTTPException(status_code=404, detail=f"No marks found for {exam_type}")
    
    sorted_marks = sorted(marks, key=lambda m: m.score, reverse=True)
    top_marks = sorted_marks[:7] if len(sorted_marks) >= 7 else sorted_marks
    
    subject_grades = []
    total_score = 0
    points_sum = 0
    
    for mark in top_marks:
        subject = db.query(Subject).filter(Subject.id == mark.subject_id).first()
        grade, points = calculate_grade(mark.score)
        subject_grades.append(GradeResponse(
            student_id=student.id,
            student_name=student.name,
            student_roll_number=student.roll_number,
            subject_id=mark.subject_id,
            subject_name=subject.name if subject else "Unknown",
            score=mark.score,
            grade=grade,
            points=points
        ))
        total_score += mark.score
        points_sum += points
    
    subject_count = len(top_marks)
    average = round(total_score / subject_count, 2) if subject_count > 0 else 0
    overall_grade, _ = calculate_grade(average)
    division = calculate_division(points_sum, subject_count)
    
    class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    student_averages = []
    
    for s in class_students:
        s_marks = db.query(Mark).filter(
            Mark.student_id == s.id,
            Mark.exam_type == exam_type
        ).all()
        s_sorted = sorted(s_marks, key=lambda m: m.score, reverse=True)
        s_top = s_sorted[:7] if len(s_sorted) >= 7 else s_sorted
        s_avg = sum(m.score for m in s_top) / len(s_top) if s_top else 0
        student_averages.append((s.id, s_avg))
    
    student_averages.sort(key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (sid, _) in enumerate(student_averages) if sid == student.id), len(student_averages) + 1)
    total_students = len(student_averages)
    remarks = calculate_remarks(overall_grade, average)
    
    return StudentResultResponse(
        student_id=student.id,
        student_name=student.name,
        student_roll_number=student.roll_number,
        exam_type=exam_type,
        subjects=subject_grades,
        total_score=total_score,
        average=average,
        overall_grade=overall_grade,
        points_sum=points_sum,
        division=division,
        position=position,
        total_students=total_students,
        remarks=remarks
    )


@router.get("/classes/{class_id}/results/{exam_type}")
def get_class_results(
    class_id: int,
    exam_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all students' results for a specific class and exam type"""
    
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    results = []
    for student in students:
        try:
            student_result = get_student_results(student.id, exam_type, db, current_user)
            results.append({
                "student_id": student.id,
                "student_name": student.name,
                "student_roll_number": student.roll_number,
                "total_score": student_result.total_score,
                "average": student_result.average,
                "overall_grade": student_result.overall_grade,
                "points_sum": student_result.points_sum,
                "division": student_result.division,
                "position": student_result.position
            })
        except HTTPException:
            results.append({
                "student_id": student.id,
                "student_name": student.name,
                "student_roll_number": student.roll_number,
                "total_score": 0,
                "average": 0,
                "overall_grade": "N/A",
                "points_sum": 0,
                "division": "N/A",
                "position": None
            })
    
    results.sort(key=lambda x: x["average"], reverse=True)
    
    for i, result in enumerate(results, 1):
        if result["position"] is not None:
            result["position"] = i
    
    return {
        "class_id": class_id,
        "class_name": school_class.name,
        "exam_type": exam_type,
        "total_students": len(students),
        "results": results
    }


@router.get("/marks/available-years")
def get_available_years(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get list of years that have marks data"""
    from sqlalchemy import extract, distinct
    
    # Get distinct years from marks table
    years = db.query(distinct(extract('year', Mark.created_at))).order_by(extract('year', Mark.created_at).desc()).all()
    
    # Convert to list of integers
    year_list = [int(y[0]) for y in years if y[0] is not None]
    
    # If no years found, provide default current year
    if not year_list:
        from datetime import datetime
        year_list = [datetime.now().year]
    
    return {"years": year_list}



@router.get("/student/{student_id}/parent-report-data")
def get_parent_report_data(
    student_id: int,
    term: str = Query("I", description="Muhula: I or II"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None),
    opening_date: Optional[str] = Query(None),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None, description="Jina la Wilaya"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Return JSON data for PDF generation using React-pdf"""
    
    # Auto-determine exam types based on term
    term_upper = term.strip().upper()
    if term_upper in ("II", "MUHULA II", "2"):
        exam_a = "MIDTERM9"
        exam_b = "ANNUAL"
        term_display = "II"
    else:
        exam_a = "MIDTERM3"
        exam_b = "TERMINAL"
        term_display = "I"
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    school = db.query(School).filter(School.id == student.school_id).first()
    school_name = school.name if school else "SECONDARY SCHOOL"
    
    # Get district name - from parameter, or from school, or from user
    final_district_name = district_name
    if not final_district_name and school:
        # Try to get district from school
        final_district_name = getattr(school, 'district', None)
    if not final_district_name:
        # Try to get from current user's school
        if hasattr(current_user, 'school') and current_user.school:
            final_district_name = getattr(current_user.school, 'district', None)
    if not final_district_name:
        final_district_name = "_________________________"
    
    # Get marks for both exam types
    marks_a = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type == exam_a
    ).all()
    
    marks_b = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type == exam_b
    ).all()
    
    if not marks_a and not marks_b:
        raise HTTPException(status_code=404, detail=f"No marks found for student")
    
    marks_a_dict = {m.subject_id: m.score for m in marks_a}
    marks_b_dict = {m.subject_id: m.score for m in marks_b}
    
    # Get subjects
    subjects = db.query(Subject).filter(Subject.school_id == student.school_id).all()
    subjects_list = [(s.id, s.name) for s in subjects]
    
    # Get class name from database
    from app.models.school_class import SchoolClass
    class_obj = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
    class_name = class_obj.name if class_obj else "Form 1"
    kidato = class_name
    
    # Get all students in same class for position calculation
    class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    
    # ============ CALCULATE SUBJECT POSITIONS ============
    subject_positions = {}
    for sub_id, sub_name in subjects_list:
        scores = []
        for s in class_students:
            s_marks_a = db.query(Mark).filter(
                Mark.student_id == s.id,
                Mark.exam_type == exam_a
            ).all()
            s_marks_b = db.query(Mark).filter(
                Mark.student_id == s.id,
                Mark.exam_type == exam_b
            ).all()
            
            s_marks_a_dict = {m.subject_id: m.score for m in s_marks_a}
            s_marks_b_dict = {m.subject_id: m.score for m in s_marks_b}
            
            a_score = s_marks_a_dict.get(sub_id)
            b_score = s_marks_b_dict.get(sub_id)
            
            if a_score is not None or b_score is not None:
                scores_list = [s for s in [a_score, b_score] if s is not None]
                avg = sum(scores_list) / len(scores_list) if scores_list else 0
                scores.append((s.id, avg))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        for idx, (sid, _) in enumerate(scores, start=1):
            if sub_id not in subject_positions:
                subject_positions[sub_id] = {}
            subject_positions[sub_id][sid] = idx
    
    # Prepare subject data with positions
    subjects_data = []
    for sub_id, sub_name in subjects_list:
        a_score = marks_a_dict.get(sub_id)
        b_score = marks_b_dict.get(sub_id)
        
        if a_score is not None or b_score is not None:
            scores = [s for s in [a_score, b_score] if s is not None]
            avg = round(sum(scores) / len(scores), 2) if scores else None
            
            # Calculate Jumla
            jumla = ""
            if a_score is not None and b_score is not None:
                jumla = f"{a_score + b_score:.1f}"
            elif a_score is not None:
                jumla = f"{a_score:.1f}"
            elif b_score is not None:
                jumla = f"{b_score:.1f}"
            
            avg_val = f"{avg:.1f}" if avg else ""
            
            # Final grade based on WASTANI
            grade_val = calculate_grade(avg)[0] if avg else ""
            if grade_val in ["A", "B"]:
                final_grade = "A"
            elif grade_val in ["C", "D"]:
                final_grade = "B"
            elif grade_val == "F":
                final_grade = "C"
            else:
                final_grade = ""
            
            # Get subject position
            subj_position = subject_positions.get(sub_id, {}).get(student.id, "")
            
            subjects_data.append({
                "name": sub_name,
                "a_score": a_score,
                "b_score": b_score,
                "jumla": jumla,
                "avg": avg_val,
                "final_grade": final_grade,
                "position": subj_position
            })
    
    # Calculate overall performance
    sorted_by_avg = sorted(subjects_data, key=lambda x: float(x["avg"]) if x["avg"] else 0, reverse=True)
    top_7 = sorted_by_avg[:7]
    
    total_score = sum(float(s["avg"]) for s in top_7 if s["avg"]) if top_7 else 0
    avg_score = round(total_score / len(top_7), 2) if top_7 else 0
    points_sum = sum(calculate_grade(float(s["avg"]))[1] for s in top_7 if s["avg"]) if top_7 else 0
    division = calculate_division(points_sum, len(top_7))
    
    # Get overall position in class
    class_averages = []
    for s in class_students:
        s_marks_a = db.query(Mark).filter(Mark.student_id == s.id, Mark.exam_type == exam_a).all()
        s_marks_b = db.query(Mark).filter(Mark.student_id == s.id, Mark.exam_type == exam_b).all()
        s_marks_a_dict = {m.subject_id: m.score for m in s_marks_a}
        s_marks_b_dict = {m.subject_id: m.score for m in s_marks_b}
        
        s_avgs = []
        for sub_id, _ in subjects_list:
            a = s_marks_a_dict.get(sub_id)
            b = s_marks_b_dict.get(sub_id)
            scores = [sc for sc in [a, b] if sc is not None]
            if scores:
                s_avgs.append(sum(scores) / len(scores))
        
        s_avgs.sort(reverse=True)
        s_top = s_avgs[:7]
        s_avg = sum(s_top) / len(s_top) if s_top else 0
        class_averages.append((s.id, s_avg))
    
    class_averages.sort(key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (sid, _) in enumerate(class_averages) if sid == student_id), len(class_averages))
    total_students = len(class_averages)
    
    # Auto-generate remarks
    teacher_remarks = get_teacher_remarks_by_division(division, avg_score)
    headmaster_remarks = get_headmaster_remarks_by_division(division, avg_score)
    
    # ============================================================
    # 🔥 SET DEFAULT DATES - ONGEZA SIKU 1!
    # ============================================================
    if not closing_date:
        closing_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not opening_date:
        opening_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not teacher_date:
        teacher_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not headmaster_date:
        headmaster_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if not teacher_name and hasattr(current_user, 'name'):
        teacher_name = current_user.name
    if not teacher_name:
        teacher_name = "________________________"
    if not headmaster_name:
        headmaster_name = "________________________"
    
    # Return JSON data with district_name
    return {
        "id": student.id,
        "name": student.name,
        "kidato": kidato,
        "term": term_display,
        "year": year,
        "subjects": subjects_data,
        "division": division,
        "points": points_sum,
        "average": avg_score,
        "position": position,
        "total_students": total_students,
        "teacher_remarks": teacher_remarks,
        "headmaster_remarks": headmaster_remarks,
        "teacher_name": teacher_name,
        "headmaster_name": headmaster_name,
        "teacher_date": teacher_date,
        "headmaster_date": headmaster_date,
        "closing_date": closing_date,
        "opening_date": opening_date,
        "school_name": school_name,
        "district_name": final_district_name  # 🔥 NEW: Jina la Wilaya
    }