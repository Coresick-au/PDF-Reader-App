# PDF Extraction Feature - Request Template for Antigravity

Copy and paste this to Antigravity when you want to add smart PDF extraction to your application:

---

## REQUEST:

I need to add smart PDF extraction to my application. Here are the requirements:

### What I Need:

1. **Extract text from PDF files** with these features:
   - Split multi-column pages (specifically page 3) into separate left/right sections
   - Filter out common header/footer content (company info, page numbers, etc.)
   - **Automatically combine multi-line comments** - comments that start with numbers (1., 2., 3., etc.) should have their continuation lines merged into single entries
   - Return clean, structured data

2. **My application setup:**
   - [ ] I'm using Python with FastAPI
   - [ ] I'm using Python with Flask  
   - [ ] I'm using standalone Python (no web framework)
   - [ ] Other: ___________

3. **Specific requirements:**
   - Page 3 should be split into two columns: "As Found (Left)" and "As Left (Right)"
   - Remove these phrases from the output: company name, contact details, "Page", etc.
   - Each numbered comment (1., 2., 3., etc.) should appear as a single line, even if it spans multiple lines in the original PDF

### Example of What I Want:

**Input (from PDF):**
```
1. Minor inspections completed. The billet mass was unable to be fitted on this
occasion due to weather delays and the unavailability
of cranage due to road conditions.

2. The weigher was found to be running at approximately -180t/hr as found.
Testing was completed to determine the cause and it
would appear site have performed a zero calibration...
```

**Desired Output:**
```
1. Minor inspections completed. The billet mass was unable to be fitted on this occasion due to weather delays and the unavailability of cranage due to road conditions.

2. The weigher was found to be running at approximately -180t/hr as found. Testing was completed to determine the cause and it would appear site have performed a zero calibration...
```

### What to Provide:

Please give me:
1. The complete Python code I can copy/paste into my project
2. Any dependencies I need to install (with pip install commands)
3. Configuration options (like which pages to split, what text to filter)
4. If I'm building a web API, include the endpoint code
5. Instructions on how to customize it for my specific needs

### Additional Details:

- My PDFs are inspection reports
- Some pages have side-by-side columns that need to be extracted separately
- Comment numbers always start with a digit followed by a period (1., 2., 3., etc.)
- I want to filter out: [list your specific header/footer text here]

---

## EXAMPLE FULL REQUEST:

Here's a complete example you can modify:

---

Hi! I need help adding smart PDF extraction to my existing Flask application. 

**Current situation:**
- I have a Flask app that currently just dumps all PDF text in one block
- My PDFs are inspection reports with numbered comments
- Page 3 has two columns side-by-side ("As Found" and "As Left")
- Comments often span multiple lines and I want them combined

**What I need:**
1. Extract text from uploaded PDFs
2. Split page 3 into left/right columns  
3. Combine multi-line comments (they always start with numbers like "1.", "2.", etc.)
4. Filter out this header/footer content:
   - "Accurate Industries"
   - "ABN 99 657 158 524"
   - "admin@accurateindustries.com.au"
   - "Page"

**Can you provide:**
- Complete Flask endpoint code I can add to my app
- The text processing function with comment combining
- Installation commands for any dependencies
- Instructions on how to customize which pages get split

Please make it copy-paste ready so I can integrate it quickly!

---

## OPTIONAL: Pre-filled Code Request

If you want Antigravity to just give you the code directly without asking questions:

---

Please create a smart PDF extraction function for my Python application with these exact requirements:

**Feature List:**
- Use pdfplumber for PDF parsing
- Split page 3 into left/right halves (50/50)
- Combine multi-line comments that start with numbers (regex: `^\d+\.?\s`)
- Filter out these phrases: "Accurate Industries", "ABN 99 657 158 524", "admin@accurateindustries.com.au", "www.accurateindustries.com.au", "1300 101 666", "Page"
- Return structured JSON: `{"data": [{"page": 1, "type": "Full Page", "content": "..."}, ...]}`

**Framework:** [FastAPI / Flask / Standalone]

**Provide:**
1. Complete function/endpoint code
2. pip install command
3. Usage example

Make it production-ready and well-commented!

---

## Tips for Best Results:

When requesting this feature, be specific about:
- ✅ Your framework (FastAPI, Flask, Django, standalone)
- ✅ What text patterns to look for (numbered comments, specific formats)
- ✅ What to filter out (your specific header/footer content)
- ✅ Which pages have special layouts (columns, tables, etc.)
- ✅ Whether you need API endpoints or just functions

The more specific you are, the better Antigravity can help!
