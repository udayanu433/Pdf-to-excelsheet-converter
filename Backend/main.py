import json
import io
import re
import pandas as pd
import pdfplumber
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

# --- 1. CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Simplified for performance; update for production security
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Processed-Data"]
)

GRADE_POINTS = {
    'S': 10, 'A+': 9, 'A': 8.5, 'B+': 8, 'B': 7.5, 'C+': 7, 'C': 6.5, 'D': 6, 
    'P': 5.5, 'PASS': 5.5, 'F': 0, 'FE': 0, 'I': 0, 'ABSENT': 0, 'WITHHELD': 0
}

SEMESTER_TOTAL_CREDITS = {
    "S1": 20, "S2": 24, "S3": 25, "S4": 24, "S5": 23, "S6": 23, "S7": 17, "S8": 11
}

# Pre-compiled Regex Patterns for speed
REG_NO_PATTERN = re.compile(r'(PKD\d{2}([A-Z]{2})\d{3})')
COURSE_GRADE_PATTERN = re.compile(r"([A-Z]{3,}\d{3})\s*\(([^)]+)\)")

# --- 2. OPTIMIZED HELPERS ---

def extract_text_from_page(page):
    """Worker function for parallel text extraction."""
    return (page.extract_text() or "") + "\n"

def get_compiled_patterns(credit_lookup):
    """Pre-compiles 'XX' patterns to avoid re-compiling inside loops."""
    compiled = []
    for pattern, credit in credit_lookup.items():
        if 'XX' in pattern:
            compiled.append((re.compile(pattern.replace('XX', '[A-Z]{2}')), credit))
    return compiled

def calculate_modular_data(student_grades, semester_key, credit_lookup, compiled_patterns):
    total_weighted_points = 0
    total_creds_obtained = 0
    official_denominator = SEMESTER_TOTAL_CREDITS.get(semester_key, 24)
    
    ucsem_already_in_pdf = "UCSEM129" in student_grades

    for code, grade in student_grades.items():
        creds = credit_lookup.get(code, 0)
        
        # Fast pattern matching using pre-compiled regex
        if creds == 0:
            for regex, credit in compiled_patterns:
                if regex.fullmatch(code):
                    creds = credit
                    break
        
        if creds > 0:
            gp = GRADE_POINTS.get(grade, 0)
            total_weighted_points += (creds * gp)
            if gp > 0: 
                total_creds_obtained += creds
            
    if semester_key == "S2" and not ucsem_already_in_pdf:
        total_weighted_points += (1 * 5.5)
        total_creds_obtained += 1

    sgpa = round(total_weighted_points / official_denominator, 2) if official_denominator > 0 else 0.0
    return sgpa, total_creds_obtained

# --- 3. OPTIMIZED API ENDPOINT ---

@app.post("/generate-excel/")
async def generate_excel(file: UploadFile = File(...), semester: str = Form(...), scheme: str = Form(...)):
    try:
        # Load credits once per request
        with open('credits_2024.json', 'r') as f:
            credit_lookup = json.load(f)
        compiled_patterns = get_compiled_patterns(credit_lookup)

        # A. PARALLEL PDF EXTRACTION
        content = await file.read()
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            # Use ThreadPoolExecutor for CPU-bound text extraction
            with ThreadPoolExecutor() as executor:
                page_texts = list(executor.map(extract_text_from_page, pdf.pages))
            full_text = "".join(page_texts)

        # B. EFFICIENT DATA PARSING
        raw_students = []
        reg_iter = list(REG_NO_PATTERN.finditer(full_text))

        for i in range(len(reg_iter)):
            match = reg_iter[i]
            reg_no = match.group(1).upper()
            start_pos = match.start()
            end_pos = reg_iter[i+1].start() if i+1 < len(reg_iter) else len(full_text)
            
            block = full_text[start_pos:end_pos].replace('\n', ' ')
            grades = {m[0]: m[1].strip().upper() for m in COURSE_GRADE_PATTERN.findall(block)}
            
            if grades:
                raw_students.append({"register_no": reg_no, "dept": reg_no[5:7], "grades": grades})

        if not raw_students: raise HTTPException(400, "Extraction failed.")

        # C. BUCKETING & CALCULATION
        dept_buckets = {}
        processed_for_dashboard = []
        for s in raw_students:
            sgpa, creds_obtained = calculate_modular_data(s["grades"], semester, credit_lookup, compiled_patterns)
            s["sgpa"] = sgpa
            s["total_credits"] = creds_obtained
            processed_for_dashboard.append(s)
            
            dept = s["dept"]
            dept_buckets.setdefault(dept, []).append(s)

        # D. EXCEL GENERATION
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
                
                # Optimized Failed Count (Vectorized)
                failed_counts = df[dept_courses].isin(['F', 'FE']).sum()
                summary_row = {"Register No": "FAILED COUNT", **failed_counts.to_dict()}
                summary_row.update({"Credits Obtained": "", "SGPA": ""})
                
                df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)
                df.to_excel(writer, index=False, sheet_name=f"{dept_name} Results")

        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=Results_{semester}.xlsx",
                "X-Processed-Data": json.dumps(processed_for_dashboard),
                "Access-Control-Expose-Headers": "X-Processed-Data"
            }
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))