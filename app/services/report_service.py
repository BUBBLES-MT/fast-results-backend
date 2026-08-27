import io
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPDF
from typing import List, Dict, Any, Tuple
from app.models.mark import Mark
from app.models.student import Student
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.school import School

# ================================
# Helper Functions
# ================================

GRADE_POINTS = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5}

def calculate_grade(score: float) -> Tuple[str, int]:
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

def get_grade(score):
    if score is None:
        return ""
    try:
        s = float(score)
    except:
        return ""
    if s >= 75:
        return "A"
    elif s >= 65:
        return "B"
    elif s >= 45:
        return "C"
    elif s >= 30:
        return "D"
    return "F"

# ================================
# Behaviour Items (Fixed)
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
# Excel Report Generator
# ================================

class ExcelReportService:
    
    @staticmethod
    def generate_class_results_excel(
        class_id: int,
        class_name: str,
        exam_type: str,
        results: List[Dict],
        subjects: List[str],
        division_summary: Dict,
        reg_summary: Dict,
        subject_grade_summary: Dict,
        subject_gpa: Dict,
        subject_position: Dict
    ) -> io.BytesIO:
        """Generate Excel report for class results"""
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book
            
            # Main Results Sheet
            worksheet = workbook.add_worksheet(f"{class_name} Results")
            
            # Header
            header_format = workbook.add_format({
                "bold": True, "align": "center", "valign": "vcenter",
                "font_size": 14, "font_color": "blue"
            })
            
            headers = [
                "THE UNITED REPUBLIC OF TANZANIA",
                "PRESIDENT'S OFFICE",
                "REGIONAL ADMINISTRATION AND LOCAL GOVERNMENT",
                "SINGIDA REGION",
                f"{class_name} {exam_type} RESULTS",
                f"Generated: {datetime.now().strftime('%B %Y')}"
            ]
            
            for i, line in enumerate(headers):
                worksheet.merge_range(i, 0, i, len(subjects) + 8, line, header_format)
            
            start_row = len(headers) + 2
            
            # Division Summary
            div_data = [["Sex"] + ["I", "II", "III", "IV", "O"] + ["Total"]]
            for sex in ["M", "F"]:
                row = [sex] + [division_summary.get(sex, {}).get(d, 0) for d in ["I", "II", "III", "IV", "O"]] + [sum(division_summary.get(sex, {}).values())]
                div_data.append(row)
            row_total = ["Total"] + [division_summary["M"].get(d, 0) + division_summary["F"].get(d, 0) for d in ["I", "II", "III", "IV", "O"]] + [sum(division_summary["M"].values()) + sum(division_summary["F"].values())]
            div_data.append(row_total)
            
            for r, row in enumerate(div_data):
                for c, val in enumerate(row):
                    worksheet.write(start_row + r, c, val)
            
            # Registration Summary
            reg_start_col = 10
            reg_data = [["Sex", "REG", "ABS"]]
            for sex in ["M", "F"]:
                reg_data.append([sex, reg_summary[sex]["REG"], reg_summary[sex]["ABS"]])
            reg_data.append(["Total", reg_summary["M"]["REG"] + reg_summary["F"]["REG"], reg_summary["M"]["ABS"] + reg_summary["F"]["ABS"]])
            
            for r, row in enumerate(reg_data):
                for c, val in enumerate(row):
                    worksheet.write(start_row + r, reg_start_col + c, val)
            
            start_row += max(len(div_data), len(reg_data)) + 3
            
            # Main Results Table
            col_headers = ["#", "EXAM NO", "STUDENT NAME", "SEX"] + subjects + ["TOTAL", "AVERAGE", "GRADE", "POINTS", "DIVISION", "POSITION"]
            for c, header in enumerate(col_headers):
                worksheet.write(start_row, c, header, workbook.add_format({"bold": True, "bg_color": "#DCE6F1"}))
            
            for i, result in enumerate(results):
                row = [
                    i + 1,
                    result.get("roll_number", ""),
                    result.get("name", ""),
                    result.get("sex", ""),
                ]
                for sub in subjects:
                    row.append(result.get("marks_dict", {}).get(sub, ""))
                row.extend([
                    result.get("total", 0),
                    result.get("average", 0),
                    result.get("grade", ""),
                    result.get("points", 0),
                    result.get("division", ""),
                    result.get("position", i + 1)
                ])
                for c, val in enumerate(row):
                    worksheet.write(start_row + i + 1, c, val)
            
            start_row += len(results) + 3
            
            # Subject Grade Summary
            grade_headers = ["Grade", "Sex"] + subjects
            for c, header in enumerate(grade_headers):
                worksheet.write(start_row, c, header, workbook.add_format({"bold": True, "bg_color": "#87CEEB"}))
            
            grades = ["A", "B", "C", "D", "F"]
            subgrade_rows = []
            for grade in grades:
                for sex in ["M", "F", "Total"]:
                    row = [grade if sex == "M" else "", sex]
                    for sub in subjects:
                        row.append(subject_grade_summary.get(sub, {}).get(grade, {}).get(sex, 0))
                    subgrade_rows.append(row)
            
            # GPA Row
            gpa_row = ["GPA", ""] + [subject_gpa.get(sub, "-") for sub in subjects]
            subgrade_rows.append(gpa_row)
            
            # Position Row
            pos_row = ["POSITION", ""] + [subject_position.get(sub, "-") for sub in subjects]
            subgrade_rows.append(pos_row)
            
            for r, row in enumerate(subgrade_rows):
                for c, val in enumerate(row):
                    worksheet.write(start_row + r + 1, c, val)
        
        output.seek(0)
        return output

# ================================
# Parent Report PDF Generator
# ================================

class ParentReportPDFService:
    
    @staticmethod
    def generate_parent_report(
        student: Student,
        student_subject_avg: Dict,
        subjects_list: List[Tuple[int, str]],
        summary_map: Dict,
        position: int,
        total_students: int,
        school_name: str,
        exam_a: str,
        exam_b: str,
        exam_term_name: str,
        exam_year: int,
        subject_positions: Dict
    ) -> io.BytesIO:
        """Generate parent report PDF for a single student"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=12,
            rightMargin=12,
            topMargin=12,
            bottomMargin=12
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            alignment=1,
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13
        )
        normal = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=9,
            leading=11
        )
        small = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            leading=10
        )
        
        # Header
        school_name_upper = (school_name or "").upper()
        class_name = student.school_class.name if student.school_class else ""
        
        roman_map = {
            "FORM1": "I", "FORM2": "II", "FORM3": "III", "FORM4": "IV",
            "Form1": "I", "Form2": "II", "Form3": "III", "Form4": "IV"
        }
        kidato = roman_map.get(class_name.replace(" ", ""), class_name)
        
        header_text = (
            "JAMHURI YA MUUNGANO WA TANZANIA<br/>"
            "OFISI YA RAIS TAMISEMI<br/>"
            f"{school_name_upper}<br/>"
            "TAARIFA YA MAENDELEO YA MWANAFUNZI (TAALUMA, KAZI, TABIA NA MWENENDO)<br/><br/>"
            f"<b>JINA LA MWANAFUNZI:</b> {student.name} &nbsp;&nbsp;&nbsp;"
            f"<b>KIDATO:</b> {kidato} &nbsp;&nbsp;&nbsp;"
            f"<b>MUHULA WA:</b> {exam_term_name} &nbsp;&nbsp;&nbsp;"
            f"<b>MWAKA:</b> {exam_year}"
        )
        elements.append(Paragraph(header_text, title_style))
        elements.append(Spacer(1, 10))
        
        # Main Table
        header_titles = [
            "MASOMO", "MAJARIBIO", "DARAJA",
            "MITIHANI", "DARAJA", "JUMLA",
            "WASTANI", "DARAJA", "NAFASI KATI YA",
            "MAONI YA MWALIMU WA SOMO", "SAINI YA MWALIMU WA SOMO",
            "NAMBA", "TABIA & MWENENDO", "DARAJA"
        ]
        
        rows = [[Paragraph(f"<b>{h}</b>", normal) for h in header_titles]]
        
        num_subjects = len(subjects_list)
        num_behaviours = len(BEHAVIOUR_ITEMS)
        max_rows = max(num_subjects, num_behaviours)
        
        for i in range(max_rows):
            if i < num_subjects:
                subid, subname = subjects_list[i]
                info = student_subject_avg.get(student.id, {}).get(subid, {})
                
                a_score = info.get("a")
                b_score = info.get("b")
                comment = info.get("comment") or ""
                
                grade_a = get_grade(a_score)
                grade_b = get_grade(b_score)
                
                if isinstance(a_score, (int, float)) and isinstance(b_score, (int, float)):
                    jumla = round(a_score + b_score, 2)
                    wastani = round((a_score + b_score) / 2, 2)
                elif isinstance(a_score, (int, float)):
                    jumla = a_score
                    wastani = round(a_score / 2, 2)
                elif isinstance(b_score, (int, float)):
                    jumla = b_score
                    wastani = round(b_score / 2, 2)
                else:
                    jumla = 0
                    wastani = 0
                
                grade_avg = get_grade(wastani)
                subj_pos = subject_positions.get(subid, {}).get(student.id, "")
                
                masomo_row = [
                    Paragraph(subname, normal),
                    str(a_score or ""), Paragraph(grade_a or "", normal),
                    str(b_score or ""), Paragraph(grade_b or "", normal),
                    str(jumla or ""),
                    f"{wastani:.2f}" if isinstance(wastani, (int, float)) else "",
                    Paragraph(grade_avg or "", normal),
                    str(subj_pos or ""),
                    Paragraph(comment, normal),
                    "",
                ]
            else:
                masomo_row = [""] * 11
            
            if i < num_behaviours:
                tabia_num = 901 + i
                tabia_name = BEHAVIOUR_ITEMS[i]
                tabia_row = [str(tabia_num), Paragraph(tabia_name, normal), ""]
            else:
                tabia_row = ["", "", ""]
            
            rows.append(masomo_row + tabia_row)
        
        col_widths = [
            30*mm, 15*mm, 10*mm,
            15*mm, 10*mm, 14*mm,
            14*mm, 10*mm, 14*mm,
            25*mm, 25*mm, 12*mm,
            36*mm, 15*mm
        ]
        
        main_table = Table(rows, colWidths=col_widths, repeatRows=1, rowHeights=[13*mm] + [7*mm] * (len(rows) - 1))
        
        main_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 1), (8, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (11, 1), (12, -1), 'LEFT'),
            ('ALIGN', (13, 1), (13, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        elements.append(main_table)
        elements.append(Spacer(1, 10))
        
        # Footer
        summ = summary_map.get(student.id, {})
        overall_avg = summ.get("overall_avg", "")
        points = summ.get("points", "")
        division = summ.get("division", "")
        
        pass_status = "HAJAFAULU"
        if division in ["I", "II", "III", "IV"]:
            pass_status = "AMEFAULU"
        
        footer_text = (
            f"Daraja la ufaulu: {division} &nbsp;&nbsp;&nbsp; "
            f"Point: {points} &nbsp;&nbsp;&nbsp; "
            f"Wastani: {overall_avg} &nbsp;&nbsp;&nbsp; "
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
            [Paragraph("A. Shule imefungwa tarehe: ____________________________ &nbsp;&nbsp;&nbsp; Itafunguliwa tarehe: ____________________________", normal)],
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
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(footer_table)
        elements.append(PageBreak())
        
        doc.build(elements)
        buffer.seek(0)
        return buffer