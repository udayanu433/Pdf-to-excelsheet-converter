from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import re
import pdfplumber # NEW: Handles the binary PDF reading

app = FastAPI()

# --- 1. CONFIGURATION ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. LOGIC ---

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Safely opens a binary PDF file and extracts text from all pages.
    """
    full_text = ""
    try:
        # Open the bytes as a PDF file
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""
    return full_text

def extract_course_map(text: str) -> dict:
    """Dynamically learns Course Codes and Names from the text."""
    course_map = {}
    # Pattern 1: CSV style "CODE","NAME"
    csv_pattern = re.compile(r'"([A-Z]{3,}\d{3})"\s*,\s*"(.*?)"')
    # Pattern 2: Plain text style CODE NAME
    plain_pattern = re.compile(r'(?m)^([A-Z]{3,}\d{3})\s+(?:"?)(.*?)(?:"?)$')
    
    matches = csv_pattern.findall(text)
    if not matches:
        matches = plain_pattern.findall(text)
    
    for code, name in matches:
        if "PKD" in name: continue 
        clean_name = name.replace('\n', ' ').strip()
        course_map[code] = clean_name
        
    return course_map

def parse_text_to_json(text: str) -> list:
    """Finds students and their grades in the text."""
    students = []
    
    # split text by "PKD..." to isolate student blocks
    # This finds the start of every student record
    reg_iter = re.finditer(r'(PKD\d{2}[A-Z]{2}\d{3})', text)
    reg_indices = [(m.start(), m.group(1)) for m in reg_iter]
    
    if not reg_indices:
        return []

    for i in range(len(reg_indices)):
        start, reg_no = reg_indices[i]
        # End at the next student or end of file
        end = reg_indices[i+1][0] if i + 1 < len(reg_indices) else len(text)
        
        # Get the raw text for this student
        raw_block = text[start:end]
        
        # Cleanup: remove the RegNo itself to avoid confusion
        grades_block = raw_block.replace(reg_no, '').replace('\n', ' ')
        
        # Fix missing commas/parentheses common in PDF text
        grades_block = re.sub(r'\)\s*([A-Z]{3,}\d{3})', r'), \1', grades_block)
        
        dept = reg_no[5:7] # e.g. CS from PKD24CS001
        
        student_obj = {"register_no": reg_no, "department": dept, "grades": {}}
        
        # Find CODE(Grade)
        pairs = re.findall(r"([A-Z]{3,}\d{3})\s*\(([^)]+)\)", grades_block)
        for code, grade in pairs:
            student_obj["grades"][code] = grade.strip()
            
        if student_obj["grades"]:
            students.append(student_obj)
            
    return students

def generate_excel_from_json(student_data: list, course_map: dict) -> bytes:
    output = io.BytesIO()
    departments = {}
    
    # Group by Dept
    for s in student_data:
        dept = s['department']
        if dept not in departments: departments[dept] = []
        
        row = {"Register No": s['register_no']}
        for code, grade in s['grades'].items():
            # Use full name if we found it, else code
            header = course_map.get(code, code)
            row[header] = grade
        departments[dept].append(row)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not departments:
             pd.DataFrame(["No Data"]).to_excel(writer, sheet_name="Error")
             
        for dept, rows in departments.items():
            df = pd.DataFrame(rows)
            # Sort cols
            cols = [c for c in df.columns if c != "Register No"]
            cols.sort()
            df = df[["Register No"] + cols]
            
            df.to_excel(writer, sheet_name=f"{dept} Result", index=False)
            
    output.seek(0)
    return output.read()

# --- 3. ENDPOINT ---

@app.post("/generate-excel/")
async def generate_excel(file: UploadFile = File(...)):
    try:
        # 1. Read binary PDF (Do NOT decode to utf-8)
        content = await file.read()
        
        # 2. Extract Text
        text_data = extract_text_from_pdf(content)
        if not text_data:
            raise HTTPException(400, "Could not extract text. Ensure file is a valid PDF.")

        # 3. Process
        course_map = extract_course_map(text_data)
        json_data = parse_text_to_json(text_data)
        
        if not json_data:
            raise HTTPException(400, "No student data found in PDF.")

        # 4. Generate
        excel_bytes = generate_excel_from_json(json_data, course_map)
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Semester_Result.xlsx"}
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)