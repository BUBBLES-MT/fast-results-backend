from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.mark import Mark
from app.models.student import Student
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.school import School
from app.models.school_announcement import SchoolAnnouncement
from app.models.teacher import Teacher
import io
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPDF

router = APIRouter()

# ================================
# 🔥 HELPER FUNCTION - FORMAT DATE
# ================================

def format_date_for_pdf(date_value):
    """
    Format date in DD/MM/YYYY format - NO DAY ADDED!
    Tarehe inabaki kama ilivyo.
    """
    if not date_value:
        return "____________________________"
    try:
        if isinstance(date_value, str):
            if '-' in date_value:
                parts = date_value.split('-')
                if len(parts) == 3:
                    return f"{parts[2]}/{parts[1]}/{parts[0]}"
            elif '/' in date_value:
                return date_value
            return date_value
        if hasattr(date_value, 'strftime'):
            return date_value.strftime("%d/%m/%Y")
        return str(date_value)
    except Exception as e:
        print(f"Error formatting date: {e}")
        return str(date_value) if date_value else "____________________________"

def format_date_from_frontend(date_str):
    """Convert YYYY-MM-DD to DD/MM/YYYY"""
    if not date_str:
        return None
    try:
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        elif '/' in date_str:
            return date_str
        return date_str
    except:
        return date_str

# ================================
# Helper Functions (Grading)
# ================================

def calculate_grade(score: float) -> tuple:
    """Calculate grade and points based on score"""
    if score is None:
        return "N/A", 0
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
    """Calculate division based on points sum and subject count"""
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
    return "N/A"

# ================================
# Behaviour Items
# ================================

BEHAVIOUR_ITEMS = [
    "Bidii na Maarifa",
    "Ari ya kazi",
    "Ubora wa kazi",
    "Utunzaji wa vifaa",
    "Ushirikiano na wenzake",
    "Heshima kwa wote",
    "Uongozi",
    "Utii na Kujituma",
    "Usafi binafsi",
    "Utamaduni na michezo",
    "Uaminifu na kujiamini",
    "Mahudhurio shuleni"
]

# ================================
# Parent Report PDF Generator (Single Student)
# ================================

def generate_parent_report_pdf(
    student,
    student_subject_avg,
    subjects_list,
    summary_map,
    position,
    total_students,
    school_name,
    exam_a,
    exam_b,
    exam_term_name,
    exam_year,
    subject_positions,
    announcement=None
):
    """Generate Parent Report PDF for a single student"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A3),
        leftMargin=12, rightMargin=12, topMargin=12, bottomMargin=12
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        alignment=1, fontName='Helvetica-Bold', fontSize=11, leading=13
    )
    normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9, leading=11)
    small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10)
    
    elements = []
    
    # Get class name
    class_name = student.school_class.name if student.school_class else "N/A"
    
    # Roman numeral for class
    roman_map = {
        "Form 1": "I", "Form 2": "II", "Form 3": "III", "Form 4": "IV",
        "Form1": "I", "Form2": "II", "Form3": "III", "Form4": "IV"
    }
    kidato = roman_map.get(class_name, class_name)
    
    # Header
    header_text = (
        f"<b>JAMHURI YA MUUNGANO WA TANZANIA</b><br/>"
        f"<b>OFISI YA RAIS TAMISEMI</b><br/>"
        f"<b>{school_name.upper()}</b><br/>"
        f"<b>TAARIFA YA MAENDELEO YA MWANAFUNZI (TAALUMA, KAZI, TABIA NA MWENENDO)</b><br/><br/>"
        f"<b>JINA LA MWANAFUNZI:</b> {student.name} &nbsp;&nbsp;&nbsp;"
        f"<b>KIDATO:</b> {kidato} &nbsp;&nbsp;&nbsp;"
        f"<b>MUHULA WA:</b> {exam_term_name} &nbsp;&nbsp;&nbsp;"
        f"<b>MWAKA:</b> {exam_year}"
    )
    elements.append(Paragraph(header_text, title_style))
    elements.append(Spacer(1, 10))
    
    # Table Header
    header_titles = [
        "MASOMO", "MAJARIBIO", "DARAJA",
        "MITIHANI", "DARAJA", "JUMLA",
        "WASTANI", "DARAJA", "NAFASI KATI YA",
        "MAONI YA MWALIMU WA SOMO", "SAINI YA MWALIMU WA SOMO",
        "NAMBA", "TABIA & MWENENDO", "DARAJA"
    ]
    
    rows = [[Paragraph(f"<b>{h}</b>", normal) for h in header_titles]]
    
    # Add subject rows
    sid = student.id
    subj_map = student_subject_avg.get(sid, {})
    
    for i, (sub_id, sub_name) in enumerate(subjects_list):
        info = subj_map.get(sub_id, {})
        a_score = info.get("a")
        b_score = info.get("b")
        avg_score = info.get("avg")
        grade, _ = calculate_grade(avg_score) if avg_score else ("N/A", 0)
        
        row = [
            Paragraph(sub_name, normal),
            f"{a_score:.2f}" if a_score else "", grade if a_score else "",
            f"{b_score:.2f}" if b_score else "", grade if b_score else "",
            f"{avg_score:.2f}" if avg_score else "",
            "", grade, "", "", "", "", "", ""
        ]
        rows.append(row)
    
    # Add behaviour rows
    for i, behaviour in enumerate(BEHAVIOUR_ITEMS):
        tabia_num = 901 + i
        rows.append([
            "", "", "", "", "", "", "", "", "", "", "",
            str(tabia_num), Paragraph(behaviour, normal), ""
        ])
    
    col_widths = [
        30*mm, 15*mm, 10*mm, 15*mm, 10*mm, 14*mm,
        14*mm, 10*mm, 14*mm, 25*mm, 25*mm, 12*mm, 36*mm, 15*mm
    ]
    
    main_table = Table(rows, colWidths=col_widths, repeatRows=1,
                       rowHeights=[13*mm] + [7*mm] * (len(rows) - 1))
    
    style_commands = [
        ('GRID', (0,0), (-1,-1), 0.35, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,1), (8,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('ALIGN', (11,1), (12,-1), 'LEFT'),
        ('ALIGN', (13,1), (13,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]
    main_table.setStyle(TableStyle(style_commands))
    elements.append(main_table)
    elements.append(Spacer(1, 10))
    
    # Footer
    summ = summary_map.get(sid, {})
    overall_avg = summ.get("overall_avg", 0)
    points = summ.get("points", 0)
    division = summ.get("division", "N/A")
    
    pass_status = "HAJAFAULU"
    if division in ["I", "II", "III", "IV"]:
        pass_status = "AMEFAULU"
    
    footer_text = (
        f"Daraja la ufaulu: {division} &nbsp;&nbsp;&nbsp; "
        f"Point: {points} &nbsp;&nbsp;&nbsp; "
        f"Wastani: {overall_avg:.2f} &nbsp;&nbsp;&nbsp; "
        f"Nafasi yake ni: {position}&nbsp; kati ya &nbsp;{total_students}. "
        f"<b>{pass_status}</b>"
    )
    
    closing_date = format_date_for_pdf(announcement.closing_date) if announcement else "____________________________"
    opening_date = format_date_for_pdf(announcement.opening_date) if announcement else "____________________________"
    
    footer_data = [
        [Paragraph(footer_text, normal)],
        [Paragraph(
            "TAFSIRI YA MADARAJA: (A: 100–75 = Vizuri sana), (B: 74–65 = Vizuri), "
            "(C: 64–45 = Wastani), (D: 44–30 = Dhaifu), (F: 29–0 = Feli).<br/>"
            "Madaraja I = 7–17, II = 18–21, III = 22–25, IV = 26–33, 0 = 34–35.", small)],
        [Spacer(1, 6)],
        [Paragraph(f"A. Shule imefungwa tarehe: {closing_date} &nbsp;&nbsp;&nbsp; Itafunguliwa tarehe: {opening_date}", normal)],
        [Paragraph("B. Maoni ya mwalimu wa darasa kuhusu masomo na tabia:", normal)],
        [Paragraph("......................................................................................................................................................................................................................", normal)],
        [Paragraph(".............................................................................................................................................................................................................................", normal)],
        [Paragraph("Tarehe: ________________________ &nbsp;&nbsp;&nbsp; Sahihi: ________________________", normal)],
        [Spacer(1, 6)],
        [Paragraph("C. Maoni ya Mkuu wa Shule:", normal)],
        [Paragraph(".........................................................................................................................................................................................................................", normal)],
        [Paragraph("..............................................................................................................................................................................................................................", normal)],
        [Paragraph("Tarehe: ________________________ &nbsp;&nbsp;&nbsp; Sahihi: ________________________<br/><br/><br/>", normal)],
        [Spacer(1, 6)],
        [Paragraph(
            "D. MAONI YA MZAZI/MLEZI KUHUSU MWANAO "
            "(IRUDISHWE SHULENI BAADA YA KUJAZA MAONI YAKO KUHUSU MAENDELEO YA MWANAO <br/> "
            "KITAALUMA, KITABIA NA KUKIRI KUPOKEA TAARIFA HII:", normal)],
        [Paragraph("....................................................................................................................................................................................................................", normal)],
        [Paragraph(".......................................................................................................................................................................................................................", normal)],
        [Paragraph("...........................................................................................................................................................................................................................", normal)],
        [Paragraph("JINA LA MZAZI/MLEZI: ___________________________________________ &nbsp;&nbsp;&nbsp; Sahihi: ___________________ &nbsp;&nbsp;&nbsp; Tarehe: ____________________", normal)]
    ]
    
    footer_table = Table(footer_data, colWidths=[sum(col_widths)])
    footer_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    
    elements.append(footer_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ================================
# Batch Parent Report PDF Generator (Class)
# ================================

def generate_class_parent_reports_pdf(
    students_data,
    school_name,
    class_name,
    exam_type,
    term,
    year,
    announcement=None,
    closing_date_override=None,
    opening_date_override=None
):
    """Generate Parent Report PDFs for all students in a class (merged)"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        leftMargin=12, rightMargin=12, topMargin=12, bottomMargin=12
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        alignment=1, fontName='Helvetica-Bold', fontSize=11, leading=13
    )
    normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9, leading=11)
    small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10)
    
    elements = []
    
    roman_map = {
        "Form 1": "I", "Form 2": "II", "Form 3": "III", "Form 4": "IV",
        "Form1": "I", "Form2": "II", "Form3": "III", "Form4": "IV"
    }
    kidato = roman_map.get(class_name, class_name)
    
    # 🔥 TUMIA OVERRIDE KABLA YA DATABASE!
    if closing_date_override:
        closing_date = closing_date_override
    elif announcement and announcement.closing_date:
        if hasattr(announcement.closing_date, 'strftime'):
            closing_date = announcement.closing_date.strftime("%d/%m/%Y")
        else:
            closing_date = str(announcement.closing_date)
    else:
        closing_date = "____________________________"
    
    if opening_date_override:
        opening_date = opening_date_override
    elif announcement and announcement.opening_date:
        if hasattr(announcement.opening_date, 'strftime'):
            opening_date = announcement.opening_date.strftime("%d/%m/%Y")
        else:
            opening_date = str(announcement.opening_date)
    else:
        opening_date = "____________________________"
    
    for student_data in students_data:
        student = student_data["student"]
        subjects_data = student_data["subjects"]
        total_score = student_data["total_score"]
        average = student_data["average"]
        points_sum = student_data["points_sum"]
        division = student_data["division"]
        position = student_data["position"]
        total_students = student_data["total_students"]
        
        # Header
        header_text = (
            f"<b>JAMHURI YA MUUNGANO WA TANZANIA</b><br/>"
            f"<b>OFISI YA RAIS TAMISEMI</b><br/>"
            f"<b>{school_name.upper()}</b><br/>"
            f"<b>TAARIFA YA MAENDELEO YA MWANAFUNZI (TAALUMA, KAZI, TABIA NA MWENENDO)</b><br/><br/>"
            f"<b>JINA LA MWANAFUNZI:</b> {student.name} &nbsp;&nbsp;&nbsp;"
            f"<b>KIDATO:</b> {kidato} &nbsp;&nbsp;&nbsp;"
            f"<b>MUHULA WA:</b> {term} &nbsp;&nbsp;&nbsp;"
            f"<b>MWAKA:</b> {year}"
        )
        elements.append(Paragraph(header_text, title_style))
        elements.append(Spacer(1, 10))
        
        # Table Header
        header_titles = [
            "MASOMO", "MAJARIBIO", "DARAJA",
            "MITIHANI", "DARAJA", "JUMLA",
            "WASTANI", "DARAJA", "NAFASI KATI YA",
            "MAONI YA MWALIMU WA SOMO", "SAINI YA MWALIMU WA SOMO",
            "NAMBA", "TABIA & MWENENDO", "DARAJA"
        ]
        
        rows = [[Paragraph(f"<b>{h}</b>", normal) for h in header_titles]]
        
        # Add subject rows
        for subj in subjects_data:
            row = [
                Paragraph(subj["name"], normal),
                "", "", "", "", f"{subj['score']:.2f}", "", Paragraph(subj["grade"], normal),
                "", "", "", "", "", ""
            ]
            rows.append(row)
        
        # Add behaviour rows
        for i, behaviour in enumerate(BEHAVIOUR_ITEMS):
            tabia_num = 901 + i
            rows.append([
                "", "", "", "", "", "", "", "", "", "", "",
                str(tabia_num), Paragraph(behaviour, normal), ""
            ])
        
        col_widths = [
            30*mm, 15*mm, 10*mm, 15*mm, 10*mm, 14*mm,
            14*mm, 10*mm, 14*mm, 25*mm, 25*mm, 12*mm, 36*mm, 15*mm
        ]
        
        main_table = Table(rows, colWidths=col_widths, repeatRows=1,
                           rowHeights=[13*mm] + [7*mm] * (len(rows) - 1))
        
        style_commands = [
            ('GRID', (0,0), (-1,-1), 0.35, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,1), (8,-1), 'CENTER'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),
            ('ALIGN', (11,1), (12,-1), 'LEFT'),
            ('ALIGN', (13,1), (13,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]
        main_table.setStyle(TableStyle(style_commands))
        elements.append(main_table)
        elements.append(Spacer(1, 10))
        
        # Footer
        pass_status = "HAJAFAULU"
        if division in ["I", "II", "III", "IV"]:
            pass_status = "AMEFAULU"
        
        footer_text = (
            f"Daraja la ufaulu: {division} &nbsp;&nbsp;&nbsp; "
            f"Point: {points_sum} &nbsp;&nbsp;&nbsp; "
            f"Wastani: {average:.2f} &nbsp;&nbsp;&nbsp; "
            f"Nafasi yake ni: {position}&nbsp; kati ya &nbsp;{total_students}. "
            f"<b>{pass_status}</b>"
        )
        
        footer_data = [
            [Paragraph(footer_text, normal)],
            [Paragraph(
                "TAFSIRI YA MADARAJA: (A: 100–75 = Vizuri sana), (B: 74–65 = Vizuri), "
                "(C: 64–45 = Wastani), (D: 44–30 = Dhaifu), (F: 29–0 = Feli).<br/>"
                "Madaraja I = 7–17, II = 18–21, III = 22–25, IV = 26–33, 0 = 34–35.", small)],
            [Spacer(1, 6)],
            [Paragraph(f"A. Shule imefungwa tarehe: {closing_date} &nbsp;&nbsp;&nbsp; Itafunguliwa tarehe: {opening_date}", normal)],
            [Paragraph("B. Maoni ya mwalimu wa darasa kuhusu masomo na tabia:", normal)],
            [Paragraph("......................................................................................................................................................................................................................", normal)],
            [Paragraph(".............................................................................................................................................................................................................................", normal)],
            [Paragraph("Tarehe: ________________________ &nbsp;&nbsp;&nbsp; Sahihi: ________________________", normal)],
            [Spacer(1, 6)],
            [Paragraph("C. Maoni ya Mkuu wa Shule:", normal)],
            [Paragraph(".........................................................................................................................................................................................................................", normal)],
            [Paragraph("..............................................................................................................................................................................................................................", normal)],
            [Paragraph("Tarehe: ________________________ &nbsp;&nbsp;&nbsp; Sahihi: ________________________<br/><br/><br/>", normal)],
            [Spacer(1, 6)],
            [Paragraph(
                "D. MAONI YA MZAZI/MLEZI KUHUSU MWANAO "
                "(IRUDISHWE SHULENI BAADA YA KUJAZA MAONI YAKO KUHUSU MAENDELEO YA MWANAO <br/> "
                "KITAALUMA, KITABIA NA KUKIRI KUPOKEA TAARIFA HII:", normal)],
            [Paragraph("....................................................................................................................................................................................................................", normal)],
            [Paragraph(".......................................................................................................................................................................................................................", normal)],
            [Paragraph("...........................................................................................................................................................................................................................", normal)],
            [Paragraph("JINA LA MZAZI/MLEZI: ___________________________________________ &nbsp;&nbsp;&nbsp; Sahihi: ___________________ &nbsp;&nbsp;&nbsp; Tarehe: ____________________", normal)]
        ]
        
        footer_table = Table(footer_data, colWidths=[sum(col_widths)])
        footer_table.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        
        elements.append(footer_table)
        elements.append(PageBreak())
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ================================
# API Endpoints
# ================================

@router.get("/class/{class_id}/export-excel")
def export_class_excel(
    class_id: int,
    exam_type: str = Query(..., description="Exam type (MIDTERM3, MIDTERM9, TERMINAL, ANNUAL)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export class results to Excel"""
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found in this class")
    
    # Get all subjects
    subjects = db.query(Subject).filter(Subject.school_id == school_class.school_id).all()
    subject_names = [s.name for s in subjects]
    
    # Process results
    results = []
    division_summary = {"I": {"M": 0, "F": 0, "Total": 0}, "II": {"M": 0, "F": 0, "Total": 0}, 
                        "III": {"M": 0, "F": 0, "Total": 0}, "IV": {"M": 0, "F": 0, "Total": 0}, 
                        "O": {"M": 0, "F": 0, "Total": 0}}
    reg_summary = {"M": {"REG": 0, "ABS": 0}, "F": {"REG": 0, "ABS": 0}}
    
    for student in students:
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type == exam_type
        ).all()
        
        marks_dict = {m.subject.name: m.score for m in marks}
        top_marks = sorted(marks, key=lambda m: m.score, reverse=True)[:7]
        
        total = sum(m.score for m in top_marks)
        average = round(total / len(top_marks), 2) if top_marks else 0
        grade, _ = calculate_grade(average)
        points_sum = sum(calculate_grade(m.score)[1] for m in top_marks) if top_marks else 0
        division = calculate_division(points_sum, len(top_marks))
        
        results.append({
            "roll_number": student.roll_number or "-",
            "name": student.name,
            "sex": student.sex,
            "marks_dict": marks_dict,
            "total": round(total, 2),
            "average": average,
            "grade": grade,
            "points": points_sum,
            "division": division
        })
        
        # Update division summary
        if division in division_summary:
            division_summary[division][student.sex] += 1
            division_summary[division]["Total"] += 1
        
        # Update registration summary
        if marks:
            reg_summary[student.sex]["REG"] += 1
        else:
            reg_summary[student.sex]["ABS"] += 1
    
    # Sort results by average (highest first)
    results.sort(key=lambda x: x["average"], reverse=True)
    
    # Add position
    for i, result in enumerate(results, 1):
        result["position"] = i
    
    reg_summary["Total"] = {"REG": reg_summary["M"]["REG"] + reg_summary["F"]["REG"], 
                            "ABS": reg_summary["M"]["ABS"] + reg_summary["F"]["ABS"]}
    
    # Create Excel file
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Main results sheet
        df_main = pd.DataFrame([{
            "Position": r["position"],
            "Roll Number": r["roll_number"],
            "Student Name": r["name"],
            "Sex": r["sex"],
            **{sub: r["marks_dict"].get(sub, "") for sub in subject_names},
            "Total": r["total"],
            "Average": r["average"],
            "Grade": r["grade"],
            "Points": r["points"],
            "Division": r["division"]
        } for r in results])
        
        df_main.to_excel(writer, sheet_name=f"{school_class.name} Results", index=False)
        
        # Division summary sheet
        df_div = pd.DataFrame([{
            "Division": div,
            "Male": data["M"],
            "Female": data["F"],
            "Total": data["Total"]
        } for div, data in division_summary.items()])
        df_div.to_excel(writer, sheet_name="Division Summary", index=False)
        
        # Registration summary sheet
        df_reg = pd.DataFrame([
            {"Sex": "Male", "Registered": reg_summary["M"]["REG"], "Absent": reg_summary["M"]["ABS"]},
            {"Sex": "Female", "Registered": reg_summary["F"]["REG"], "Absent": reg_summary["F"]["ABS"]},
            {"Sex": "Total", "Registered": reg_summary["Total"]["REG"], "Absent": reg_summary["Total"]["ABS"]}
        ])
        df_reg.to_excel(writer, sheet_name="Registration Summary", index=False)
    
    output.seek(0)
    
    filename = f"class_{school_class.name}_{exam_type}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/class/{class_id}/top-students")
def get_top_students(
    class_id: int,
    exam_type: str = Query("MIDTERM3", description="Exam type"),
    limit: int = Query(10, description="Number of top students"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get top performing students in a class"""
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    # Calculate averages for each student
    student_results = []
    for student in students:
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type == exam_type
        ).all()
        
        if marks:
            top_marks = sorted(marks, key=lambda m: m.score, reverse=True)[:7]
            total = sum(m.score for m in top_marks)
            average = round(total / len(top_marks), 2)
            grade, _ = calculate_grade(average)
            
            student_results.append({
                "student_id": student.id,
                "name": student.name,
                "roll_number": student.roll_number,
                "average": average,
                "total": total,
                "grade": grade,
                "subjects_count": len(top_marks)
            })
    
    # Sort by average (highest first)
    student_results.sort(key=lambda x: x["average"], reverse=True)
    
    # Add position
    for i, result in enumerate(student_results, 1):
        result["position"] = i
    
    # Return top N students
    top_students = student_results[:limit]
    
    return {
        "class_id": class_id,
        "class_name": school_class.name,
        "exam_type": exam_type,
        "total_students": len(student_results),
        "top_students": top_students
    }


@router.get("/student/{student_id}/parent-report")
def generate_parent_report(
    student_id: int,
    exam_type: str = Query("MIDTERM3", description="Exam type"),
    term: str = Query("I", description="Term (I or II)"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate parent report PDF for a SINGLE student"""
    
    # Get student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get school
    school = db.query(School).filter(School.id == student.school_id).first()
    school_name = school.name if school else "School Name"
    
    # 🔥 FETCH ANNOUNCEMENT
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == student.school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    # Get all marks for this student and exam type
    marks = db.query(Mark).filter(
        Mark.student_id == student_id,
        Mark.exam_type == exam_type
    ).all()
    
    if not marks:
        raise HTTPException(status_code=404, detail=f"No marks found for {exam_type}")
    
    # Get all subjects
    subjects_list = []
    for mark in marks:
        subject = db.query(Subject).filter(Subject.id == mark.subject_id).first()
        if subject and (mark.subject_id, subject.name) not in subjects_list:
            subjects_list.append((mark.subject_id, subject.name))
    
    # Build student_subject_avg
    student_subject_avg = {student_id: {}}
    for sub_id, sub_name in subjects_list:
        mark = next((m for m in marks if m.subject_id == sub_id), None)
        if mark:
            grade, points = calculate_grade(mark.score)
            student_subject_avg[student_id][sub_id] = {
                "a": mark.score,
                "b": None,
                "avg": mark.score,
                "grade": grade,
                "points": points,
                "comment": ""
            }
    
    # Calculate summary
    top_marks = sorted(marks, key=lambda m: m.score, reverse=True)[:7]
    total_score = sum(m.score for m in top_marks)
    average = round(total_score / len(top_marks), 2) if top_marks else 0
    points_sum = sum(calculate_grade(m.score)[1] for m in top_marks) if top_marks else 0
    division = calculate_division(points_sum, len(top_marks))
    
    summary_map = {
        student_id: {
            "overall_avg": average,
            "points": points_sum,
            "division": division
        }
    }
    
    # Calculate position within class
    class_students = db.query(Student).filter(Student.class_id == student.class_id).all()
    student_averages = []
    for s in class_students:
        s_marks = db.query(Mark).filter(
            Mark.student_id == s.id,
            Mark.exam_type == exam_type
        ).all()
        s_top = sorted(s_marks, key=lambda m: m.score, reverse=True)[:7]
        s_avg = sum(m.score for m in s_top) / len(s_top) if s_top else 0
        student_averages.append((s.id, s_avg))
    
    student_averages.sort(key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (sid, _) in enumerate(student_averages) if sid == student_id), len(student_averages) + 1)
    total_students = len(student_averages)
    
    # Generate PDF
    pdf_buffer = generate_parent_report_pdf(
        student=student,
        student_subject_avg=student_subject_avg,
        subjects_list=subjects_list,
        summary_map=summary_map,
        position=position,
        total_students=total_students,
        school_name=school_name,
        exam_a=exam_type,
        exam_b=None,
        exam_term_name=term,
        exam_year=year,
        subject_positions={},
        announcement=announcement
    )
    
    filename = f"parent_report_{student.name}_{exam_type}_{year}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ================================
# Batch Parent Reports for Entire Class
# ================================

@router.get("/class/{class_id}/parent-reports")
def generate_class_parent_reports(
    class_id: int,
    exam_type: str = Query("MIDTERM3", description="Exam type"),
    term: str = Query("I", description="Term (I or II)"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None, description="Closing date from frontend"),
    opening_date: Optional[str] = Query(None, description="Opening date from frontend"),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate parent report PDFs for ALL students in a class (merged into one PDF)"""
    
    # Get class
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get all students in class
    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found in this class")
    
    # Get school
    school = db.query(School).filter(School.id == school_class.school_id).first()
    school_name = school.name if school else "School Name"
    
    # 🔥 FETCH ANNOUNCEMENT
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_class.school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    # 🔥 FORMAT TAREHE KUTOKA FRONTEND
    closing_date_pdf = format_date_from_frontend(closing_date)
    opening_date_pdf = format_date_from_frontend(opening_date)
    
    # 🔥 KAMA FRONTEND HAINA, TUMIA DATABASE
    if not closing_date_pdf and announcement and announcement.closing_date:
        if hasattr(announcement.closing_date, 'strftime'):
            closing_date_pdf = announcement.closing_date.strftime("%d/%m/%Y")
        else:
            closing_date_pdf = str(announcement.closing_date)
    
    if not opening_date_pdf and announcement and announcement.opening_date:
        if hasattr(announcement.opening_date, 'strftime'):
            opening_date_pdf = announcement.opening_date.strftime("%d/%m/%Y")
        else:
            opening_date_pdf = str(announcement.opening_date)
    
    # 🔥 DEFAULT
    if not closing_date_pdf:
        closing_date_pdf = "____________________________"
    if not opening_date_pdf:
        opening_date_pdf = "____________________________"
    
    # Calculate class averages for position
    class_averages = []
    for student in students:
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type == exam_type
        ).all()
        top_marks = sorted(marks, key=lambda m: m.score, reverse=True)[:7] if marks else []
        avg = sum(m.score for m in top_marks) / len(top_marks) if top_marks else 0
        class_averages.append((student.id, avg))
    class_averages.sort(key=lambda x: x[1], reverse=True)
    
    # Prepare data for each student
    students_data = []
    for student in students:
        marks = db.query(Mark).filter(
            Mark.student_id == student.id,
            Mark.exam_type == exam_type
        ).all()
        
        if not marks:
            continue
        
        # Get subjects data
        subjects_data = []
        total_score = 0
        points_sum = 0
        
        for mark in marks:
            subject = db.query(Subject).filter(Subject.id == mark.subject_id).first()
            grade, points = calculate_grade(mark.score)
            subjects_data.append({
                "name": subject.name if subject else "Unknown",
                "score": mark.score,
                "grade": grade,
                "points": points
            })
            total_score += mark.score
            points_sum += points
        
        # Sort by score
        subjects_data.sort(key=lambda x: x["score"], reverse=True)
        top_subjects = subjects_data[:7]
        
        # Calculate averages
        subject_count = len(top_subjects)
        average = round(total_score / subject_count, 2) if subject_count > 0 else 0
        overall_grade, _ = calculate_grade(average)
        division = calculate_division(points_sum, subject_count)
        
        # Get position
        position = next((i + 1 for i, (sid, _) in enumerate(class_averages) if sid == student.id), len(class_averages))
        total_students = len(class_averages)
        
        students_data.append({
            "student": student,
            "subjects": top_subjects,
            "total_score": total_score,
            "average": average,
            "points_sum": points_sum,
            "division": division,
            "position": position,
            "total_students": total_students
        })
    
    if not students_data:
        raise HTTPException(status_code=404, detail="No students with marks found in this class")
    
    # 🔥 GENERATE PDF - PITIA TAREHE ZILIZOBO RESHA
    pdf_buffer = generate_class_parent_reports_pdf(
        students_data=students_data,
        school_name=school_name,
        class_name=school_class.name,
        exam_type=exam_type,
        term=term,
        year=year,
        announcement=announcement,
        closing_date_override=closing_date_pdf,
        opening_date_override=opening_date_pdf
    )
    
    filename = f"class_{school_class.name}_{exam_type}_parent_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================
# 🔥🔥🔥 NEW ENDPOINT - parent-reports-pdf (KWA FRONTEND!) 🔥🔥🔥
# ============================================================

@router.get("/class/{class_id}/parent-reports-pdf")
def generate_class_parent_reports_pdf_endpoint(
    class_id: int,
    exam_type: str = Query("MIDTERM3", description="Exam type"),
    term: str = Query("I", description="Term (I or II)"),
    year: int = Query(default_factory=lambda: datetime.now().year),
    closing_date: Optional[str] = Query(None, description="Closing date from frontend"),
    opening_date: Optional[str] = Query(None, description="Opening date from frontend"),
    teacher_date: Optional[str] = Query(None),
    headmaster_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    headmaster_name: Optional[str] = Query(None),
    district_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 HII NDIO INAYOITWA NA FRONTEND YA MWALIMU!
    Generate parent report PDFs for ALL students in a class.
    Tarehe zinachukuliwa moja kwa moja kutoka DATABASE!
    """
    
    # 🔥 PATA SHULE KUTOKA CLASS
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # 🔥🔥🔥 CHUKUA TAREHE KUTOKA DATABASE MOJA KWA MOJA! 🔥🔥🔥
    announcement = db.query(SchoolAnnouncement).filter(
        SchoolAnnouncement.school_id == school_class.school_id,
        SchoolAnnouncement.is_active == 1
    ).first()
    
    # 🔥🔥🔥 BADILISHA TAREHE - ONGEZA SIKU 1 KULIPA TIMEZONE! 🔥🔥🔥
    def format_db_date(date_value):
        if not date_value:
            return None
        if hasattr(date_value, 'strftime'):
            # 🔥 ONGEZA SIKU 1!
            fixed_date = date_value + timedelta(days=1)
            return fixed_date.strftime("%d/%m/%Y")
        return str(date_value)
    
    # 🔥 TUMIA TAREHE KUTOKA DATABASE (ZILIZOBO RESHA)
    db_closing_date = format_db_date(announcement.closing_date) if announcement else None
    db_opening_date = format_db_date(announcement.opening_date) if announcement else None
    
    # 🔥 KAMA FRONTEND HAITUMA, TUMIA KUTOKA DATABASE
    final_closing_date = db_closing_date
    final_opening_date = db_opening_date
    
    # 🔥 KAMA BADO HAKUNA, WEKA DEFAULT
    if not final_closing_date:
        final_closing_date = "____________________________"
    if not final_opening_date:
        final_opening_date = "____________________________"
    
    print(f"📅 Closing date (FINAL): {final_closing_date}")
    print(f"📅 Opening date (FINAL): {final_opening_date}")
    
    # 🔥 CALL EXISTING ENDPOINT WITH FINAL DATES
    return generate_class_parent_reports(
        class_id=class_id,
        exam_type=exam_type,
        term=term,
        year=year,
        closing_date=final_closing_date,   # 🔥 TAREHE KUTOKA DATABASE!
        opening_date=final_opening_date,   # 🔥 TAREHE KUTOKA DATABASE!
        teacher_date=teacher_date,
        headmaster_date=headmaster_date,
        teacher_name=teacher_name,
        headmaster_name=headmaster_name,
        district_name=district_name,
        db=db,
        current_user=current_user
    )