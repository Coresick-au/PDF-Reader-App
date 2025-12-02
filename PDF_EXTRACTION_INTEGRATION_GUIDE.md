# Smart PDF Extraction - Integration Guide

This guide shows you how to integrate the smart PDF extraction feature into your existing application.

## Overview

The smart extraction uses **pdfplumber** to:
1. Split multi-column pages (like page 3) into separate sections
2. Filter out unwanted header/footer content
3. **Combine multi-line comments** - Automatically detects comments that start with numbers (1., 2., 3., etc.) and combines continuation lines into single entries
4. Return clean, structured data

---

## Option 1: Standalone Python Function (Copy & Paste)

If you just need the extraction logic, here's a self-contained function you can drop into your existing Python code:

### Installation
```bash
pip install pdfplumber
```

### The Function

```python
import pdfplumber
import io

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
    
    import re
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


def extract_pdf_smart(pdf_file_path_or_bytes, split_page_3=True):
    """
    Smart PDF extraction with column splitting and text cleaning.
    
    Args:
        pdf_file_path_or_bytes: Either a file path (str) or bytes object
        split_page_3: Whether to split page 3 into left/right columns (default: True)
    
    Returns:
        List of dictionaries with structure:
        [
            {
                "page": 1,
                "type": "Full Page" | "As Found (Left)" | "As Left (Right)",
                "content": "cleaned text content"
            },
            ...
        ]
    """
    results = []
    
    # Handle both file paths and bytes
    if isinstance(pdf_file_path_or_bytes, bytes):
        pdf_context = pdfplumber.open(io.BytesIO(pdf_file_path_or_bytes))
    else:
        pdf_context = pdfplumber.open(pdf_file_path_or_bytes)
    
    with pdf_context as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            width = page.width
            height = page.height
            
            # LOGIC: If it's Page 3 and splitting is enabled, split it down the middle
            if split_page_3 and page_num == 3:
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
    
    return results


# ============================================
# USAGE EXAMPLES
# ============================================

# Example 1: Extract from file path
if __name__ == "__main__":
    # From file path
    data = extract_pdf_smart("path/to/your/report.pdf")
    
    for item in data:
        print(f"\n{'='*60}")
        print(f"Page {item['page']} - {item['type']}")
        print(f"{'='*60}")
        print(item['content'])
    
    # From bytes (useful for uploaded files)
    with open("path/to/your/report.pdf", "rb") as f:
        pdf_bytes = f.read()
    
    data = extract_pdf_smart(pdf_bytes)
    print(f"Extracted {len(data)} sections from PDF")
```

---

## Option 2: FastAPI Endpoint (For Web Apps)

If your larger application uses FastAPI, you can add this endpoint:

### Installation
```bash
pip install fastapi uvicorn python-multipart pdfplumber
```

### Add to your FastAPI app

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import io

app = FastAPI()

# Enable CORS if you have a separate frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
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
    Remove unwanted header/footer content and combine multi-line comments.
    """
    if not text:
        return ""
    
    import re
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

@app.post("/api/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF and get smart extracted data back.
    
    Returns JSON with structure:
    {
        "data": [
            {"page": 1, "type": "Full Page", "content": "..."},
            {"page": 3, "type": "As Found (Left)", "content": "..."},
            {"page": 3, "type": "As Left (Right)", "content": "..."}
        ]
    }
    """
    contents = await file.read()
    results = []

    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            width = page.width
            height = page.height
            
            # Split page 3 into columns
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
```

### Frontend Integration (JavaScript/React)

```javascript
async function uploadAndExtractPDF(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://your-api-url/api/extract-pdf', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to extract PDF');
        }

        const result = await response.json();
        return result.data; // Array of extracted sections
    } catch (error) {
        console.error('PDF extraction error:', error);
        throw error;
    }
}

// Usage
const fileInput = document.getElementById('pdf-upload');
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
        const extractedData = await uploadAndExtractPDF(file);
        console.log('Extracted data:', extractedData);
        // Process extractedData as needed
    }
});
```

---

## Option 3: Flask Endpoint (For Flask Apps)

If you're using Flask instead of FastAPI:

### Installation
```bash
pip install flask flask-cors pdfplumber
```

### Add to your Flask app

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io

app = Flask(__name__)
CORS(app)  # Enable CORS if needed

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
    Remove unwanted header/footer content and combine multi-line comments.
    """
    if not text:
        return ""
    
    import re
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

@app.route('/api/extract-pdf', methods=['POST'])
def extract_pdf():
    """Upload a PDF and get smart extracted data back"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "File must be a PDF"}), 400
    
    contents = file.read()
    results = []

    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            width = page.width
            height = page.height
            
            # Split page 3 into columns
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

    return jsonify({"data": results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## Customization Guide

### 1. Change Which Pages Get Split

Currently, only page 3 is split into columns. To change this:

```python
# Split multiple pages
if page_num in [3, 5, 7]:  # Split pages 3, 5, and 7
    # Column splitting logic...

# Split all pages
if True:  # Always split
    # Column splitting logic...

# Split based on page width (auto-detect multi-column)
if width > 800:  # If page is wide, assume multi-column
    # Column splitting logic...
```

### 2. Adjust Column Split Ratio

Currently splits 50/50. To change:

```python
# 40/60 split
left_bbox = (0, 0, width * 0.4, height)  # Left 40%
right_bbox = (width * 0.4, 0, width, height)  # Right 60%

# Three columns
left_bbox = (0, 0, width / 3, height)
middle_bbox = (width / 3, 0, width * 2/3, height)
right_bbox = (width * 2/3, 0, width, height)
```

### 3. Customize Ignore Phrases

Update the `IGNORE_PHRASES` list with your specific header/footer content:

```python
IGNORE_PHRASES = [
    "Your Company Name",
    "Confidential",
    "Page",
    "Copyright",
    # Add any text you want to filter out
]
```

### 4. Add Vertical Cropping

If you need to crop top/bottom (like removing headers/footers by position):

```python
# Crop top 50px and bottom 50px
crop_bbox = (0, 50, width, height - 50)
cropped_page = page.crop(bbox=crop_bbox)
text = cropped_page.extract_text()
```

### 5. Extract Tables Instead of Text

If your PDFs have tables:

```python
# Extract tables
tables = page.extract_tables()
for table in tables:
    # table is a list of lists (rows and cells)
    for row in table:
        print(row)
```

---

## Integration Checklist

- [ ] Install `pdfplumber`: `pip install pdfplumber`
- [ ] Copy the extraction function into your code
- [ ] Update `IGNORE_PHRASES` with your specific content to filter
- [ ] Adjust page splitting logic if needed (currently page 3)
- [ ] Test with your actual PDF files
- [ ] Handle errors appropriately (invalid PDFs, missing pages, etc.)
- [ ] Consider adding logging for debugging

---

## Common Issues & Solutions

### Issue: Text extraction is garbled
**Solution**: Some PDFs use image-based text. You'll need OCR (like `pytesseract`) for those.

### Issue: Column split is off-center
**Solution**: Adjust the split ratio or use `page.width` to calculate the exact center.

### Issue: Some text is still being filtered incorrectly
**Solution**: Make your `IGNORE_PHRASES` more specific, or use regex patterns instead.

### Issue: Performance is slow with large PDFs
**Solution**: Process pages in parallel using `multiprocessing` or `asyncio`.

---

## Advanced: Dynamic Column Detection

If you want to automatically detect columns instead of hardcoding page 3:

```python
def has_multiple_columns(page, threshold=0.3):
    """
    Detect if a page has multiple columns by analyzing text distribution.
    Returns True if text is split into columns.
    """
    width = page.width
    left_half = page.crop((0, 0, width/2, page.height))
    right_half = page.crop((width/2, 0, width, page.height))
    
    left_text = left_half.extract_text() or ""
    right_text = right_half.extract_text() or ""
    
    # If both halves have substantial text, likely multi-column
    return len(left_text) > 100 and len(right_text) > 100

# Usage in extraction loop
if has_multiple_columns(page):
    # Split into columns
else:
    # Extract as single column
```

---

## Quick Start: Replace Your Current Extraction

If you currently have something like:

```python
# OLD CODE (dumps all text)
import PyPDF2
with open('report.pdf', 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
```

Replace it with:

```python
# NEW CODE (smart extraction)
from pdf_extraction import extract_pdf_smart  # Use the function above

data = extract_pdf_smart('report.pdf')

# Now you have structured data instead of a text dump
for section in data:
    print(f"Page {section['page']} ({section['type']}):")
    print(section['content'])
    print("-" * 60)
```

---

## Optional: Frontend UI Features

If you're building a web interface for your PDF extraction, here are useful features to add:

### Copy to Clipboard Feature

Allow users to copy extracted data with one click:

```javascript
const handleCopy = async () => {
  const textContent = data.map(item => 
    `Page ${item.page} - ${item.type}\n${'='.repeat(60)}\n${item.content}\n\n`
  ).join('\n')

  try {
    await navigator.clipboard.writeText(textContent)
    alert('Copied to clipboard!')
  } catch (err) {
    alert('Failed to copy to clipboard')
  }
}

// In your JSX:
<button onClick={handleCopy}>📋 Copy All</button>
```

### Clear/Reset Feature

Let users clear results and upload a new PDF:

```javascript
const handleClear = () => {
  setData([])
  setError(null)
  // Reset file input
  const fileInput = document.getElementById('file-upload')
  if (fileInput) fileInput.value = ''
}

// In your JSX:
<button onClick={handleClear}>🗑️ Clear</button>
```

### File Validation

Add validation before processing:

```javascript
const handleFile = async (file) => {
  // File type validation
  if (file.type !== 'application/pdf') {
    setError('Invalid file type. Please upload a PDF file.')
    return
  }

  // File size validation (10MB limit)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    setError(`File is too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Maximum size is 10MB.`)
    return
  }
  
  // Continue with upload...
}
```

### Button Styling (CSS)

Modern gradient buttons with hover effects:

```css
.action-btn {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  color: white;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.copy-btn {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
}

.copy-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.clear-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.clear-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}
```

---

## Need Help?

The key components are:
1. **pdfplumber** for PDF parsing
2. **Bounding box cropping** for column splitting
3. **Text filtering** to remove headers/footers
4. **Multi-line comment combining** to merge numbered comments

You can mix and match these techniques based on your specific needs!
