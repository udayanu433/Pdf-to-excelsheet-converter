import json
import io
import re
import pandas as pd
import pdfplumber
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- 1. CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Grade point mapping for 2024 scheme [cite: 120, 140-145]
GRADE_POINTS = {
    'S': 10, 'A+': 9, 'A': 8.5, 'B+': 8, 'B': 7.5, 'C+': 7, 'C': 6.5, 'D': 6, 
    'P': 5.5, 'PASS': 5.5, 'F': 0, 'FE': 0, 'I': 0, 'ABSENT': 0, 'WITHHELD': 0
}

# Strictly requested fixed denominators per semester [cite: 35, 114, 217, 316, 410]
SEMESTER_TOTAL_CREDITS = {
    "S1": 20, "S2": 24, "S3": 25, "S4": 24, "S5": 23, "S6": 23, "S7": 17, "S8": 11
}

# --- 2. MODULAR FUNCTIONS ---

def pdf_to_raw_json(content):
    """MODULE 1: EXTRACTION - Converts PDF text into structured JSON data."""
    students = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    # Match KTU Register Numbers [cite: 16]
    reg_iter = list(re.finditer(r'(PKD\d{2}([A-Z]{2})\d{3})', full_text))

    for i in range(len(reg_iter)):
        match = reg_iter[i]
        reg_no = match.group(1).upper()
        
        start_pos = match.start()
        end_pos = reg_iter[i+1].start() if i+1 < len(reg_iter) else len(full_text)
        block = full_text[start_pos:end_pos].replace('\n', ' ')

        # Extract Course(Grade) pairs [cite: 28, 33]
        pairs = re.findall(r"([A-Z]{3,}\d{3})\s*\(([^)]+)\)", block)
        grades = {code: grade.strip().upper() for code, grade in pairs}
        
        if grades:
            students.append({
                "register_no": reg_no,
                "dept": reg_no[5:7],
                "grades": grades
            })
    return students

def calculate_modular_data(student_grades, semester_key, credit_lookup):
    """MODULE 2: CALCULATION - Strictly calculates SGPA and tracks obtained credits."""
    total_weighted_points = 0
    total_creds_obtained = 0
    official_denominator = SEMESTER_TOTAL_CREDITS.get(semester_key, 24)
    
    # 1. Start with the mandatory UCSEM129 logic for S2 
    # This ensures every S2 student gets this credit even if it's missing from PDF text
    if semester_key == "S2":
        # Automatically add 1 credit and 'PASS' grade points (5.5) 
        total_weighted_points += (1 * 5.5)
        total_creds_obtained += 1
    
    # 2. Add points from all other subjects found in the PDF
    for code, grade in student_grades.items():
        # Skip UCSEM129 if found in text to avoid double counting
        if code == "UCSEM129":
            continue
            
        creds = credit_lookup.get(code, 0)
        if creds == 0:
            for pattern, credit in credit_lookup.items():
                if 'XX' in pattern:
                    regex_pat = pattern.replace('XX', '[A-Z]{2}')
                    if re.fullmatch(regex_pat, code):
                        creds = credit
                        break
            
        if creds > 0:
            gp = GRADE_POINTS.get(grade, 0)
            total_weighted_points += (creds * gp)
            if gp > 0: # Only count obtained credit if student passed [cite: 120]
                total_creds_obtained += creds
            
    sgpa = round(total_weighted_points / official_denominator, 2) if official_denominator > 0 else 0.0
    return sgpa, total_creds_obtained

# --- 3. MAIN API ENDPOINT ---

@app.post("/generate-excel/")
async def generate_excel(file: UploadFile = File(...), semester: str = Form(...), scheme: str = Form(...)):
    try:
        with open('credits_2024.json', 'r') as f:
            credit_lookup = json.load(f)

        content = await file.read()
        raw_students = pdf_to_raw_json(content)

        if not raw_students:
            raise HTTPException(400, "Extraction failed.")

        dept_buckets = {}
        for s in raw_students:
            dept = s["dept"]
            if dept not in dept_buckets:
                dept_buckets[dept] = []
            
            # Calculate modular data (SGPA and Total Credits)
            sgpa, creds_obtained = calculate_modular_data(s["grades"], semester, credit_lookup)
            s["sgpa"] = sgpa
            s["total_credits"] = creds_obtained
            dept_buckets[dept].append(s)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for dept_name in sorted(dept_buckets.keys()):
                student_list = dept_buckets[dept_name]
                dept_courses = sorted(list(set(c for s in student_list for c in s["grades"].keys())))
                
                rows = []
                for s in student_list:
                    row = {"Register No": s["register_no"]}
                    row.update({c: s["grades"].get(c, "") for c in dept_courses})
                    row["Credits Obtained"] = s["total_credits"]
                    row["SGPA"] = s["sgpa"]
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                
                # Failed Count Summary [cite: 140-145]
                summary_row = {"Register No": "FAILED COUNT"}
                for course in dept_courses:
                    summary_row[course] = df[course].isin(['F', 'FE']).sum()
                summary_row["Credits Obtained"] = ""
                summary_row["SGPA"] = ""
                df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)

                final_cols = ["Register No"] + dept_courses + ["Credits Obtained", "SGPA"]
                df[final_cols].to_excel(writer, index=False, sheet_name=f"{dept_name} Results")

        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Results_{semester}.xlsx"}
        )

    except Exception as e:
        raise HTTPException(500, detail=str(e))