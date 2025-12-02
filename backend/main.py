from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import io
import re

app = FastAPI()

# Allow the frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION: IGNORE LIST ---
IGNORE_PHRASES = [
    "ABN 99 657 158 524",
    "6/23 Ashtan Pl",
    "admin@accurateindustries.com.au",
    "www.accurateindustries.com.au",
    "1300 101 666",
    "Accurate Industries", 
    "Page", 
]

def clean_text(text):
    """
    Takes raw text, splits it into lines, and removes any line
    that contains words from our IGNORE_PHRASES list.
    Then combines multi-line comments that start with a number.
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    kept_lines = []
    
    # First pass: filter out unwanted phrases
    for line in lines:
        should_remove = False
        for phrase in IGNORE_PHRASES:
            if phrase.lower() in line.lower():
                should_remove = True
                break
        
        if not should_remove and line.strip() != "":
            kept_lines.append(line.strip())
    
    # Second pass: combine multi-line comments
    # Comments start with a number (e.g., "1.", "2.", etc.)
    combined_lines = []
    current_comment = ""
    
    for line in kept_lines:
        # Check if line starts with a number followed by a period or just a number
        if re.match(r'^\d+\.?\s', line):
            # This is the start of a new comment
            if current_comment:
                combined_lines.append(current_comment)
            current_comment = line
        else:
            # This is a continuation of the previous comment
            if current_comment:
                current_comment += " " + line
            else:
                # Not part of a comment, add as-is
                combined_lines.append(line)
    
    # Don't forget the last comment
    if current_comment:
        combined_lines.append(current_comment)
            
    return "\n".join(combined_lines)

@app.post("/upload")
async def process_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    results = []

    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            width = page.width
            height = page.height
            
            # LOGIC: If it's Page 3, split it down the middle
            if page_num == 3:
                # Left Half (As Found)
                left_bbox = (0, 0, width / 2, height)
                left_crop = page.crop(bbox=left_bbox)
                raw_left = left_crop.extract_text() or ""
                
                # Right Half (As Left)
                right_bbox = (width / 2, 0, width, height)
                right_crop = page.crop(bbox=right_bbox)
                raw_right = right_crop.extract_text() or ""
                
                results.append({
                    "page": page_num,
                    "type": "As Found (Left)",
                    "content": clean_text(raw_left)
                })
                results.append({
                    "page": page_num,
                    "type": "As Left (Right)",
                    "content": clean_text(raw_right)
                })
            else:
                # Normal page extraction
                raw_text = page.extract_text() or ""
                results.append({
                    "page": page_num,
                    "type": "Full Page",
                    "content": clean_text(raw_text)
                })

    return {"data": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)