# PDF Data Extractor

A modern web application for extracting data from PDF files with special handling for multi-column layouts.

## Features

- 📄 **PDF Upload**: Drag-and-drop or click to upload PDF files
- 🔍 **Smart Extraction**: Automatically extracts text from PDFs
- 📊 **Multi-Column Support**: Special handling for page 3 with side-by-side columns (As Found/As Left)
- 🎨 **Modern UI**: Beautiful glassmorphism design with smooth animations
- 🧹 **Data Cleaning**: Filters out common header/footer information

## Tech Stack

### Frontend
- React 19.2
- Vite
- Modern CSS with glassmorphism effects

### Backend
- FastAPI
- pdfplumber for PDF text extraction
- Python 3.x

## Getting Started

### Prerequisites
- Node.js (v16 or higher)
- Python 3.8 or higher
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run the backend server:
```bash
python main.py
```

The backend will start on `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will start on `http://localhost:5173` (or another port if 5173 is busy)

## Usage

1. Make sure both backend and frontend servers are running
2. Open your browser to the frontend URL (typically `http://localhost:5173`)
3. Upload a PDF file by:
   - Dragging and dropping it onto the upload area, or
   - Clicking the upload area to browse for a file
4. View the extracted data organized by page and section

## Special Features

### Page 3 Column Splitting
The application automatically detects page 3 and splits it into two columns:
- **Left Half**: "As Found" data
- **Right Half**: "As Left" data

### Data Filtering
The backend automatically filters out common header/footer information including:
- Company name and contact details
- Page numbers
- Standard footer text

You can customize the filter list in `backend/main.py` by modifying the `IGNORE_PHRASES` array.

## Project Structure

```
PDF Reader App/
├── backend/
│   ├── main.py              # FastAPI server with PDF processing logic
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.jsx         # Main React component
    │   ├── App.css         # Component styles
    │   ├── index.css       # Global styles
    │   └── main.jsx        # React entry point
    ├── index.html          # HTML template
    └── package.json        # Node dependencies
```

## API Endpoints

### POST /upload
Upload and process a PDF file.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: PDF file

**Response:**
```json
{
  "data": [
    {
      "page": 1,
      "type": "Full Page",
      "content": "Extracted text content..."
    }
  ]
}
```

## Customization

### Modify Ignored Phrases
Edit `backend/main.py` and update the `IGNORE_PHRASES` list:

```python
IGNORE_PHRASES = [
    "Your custom phrase",
    "Another phrase to ignore",
]
```

### Change Column Split Logic
Modify the page number check in `backend/main.py`:

```python
if page_num == 3:  # Change this to target different pages
    # Column splitting logic
```

## Troubleshooting

### Backend won't start
- Ensure Python 3.8+ is installed
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify port 8000 is not in use

### Frontend won't connect to backend
- Ensure backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify the API URL in `App.jsx` matches your backend URL

### PDF upload fails
- Ensure the file is a valid PDF
- Check backend logs for error messages
- Verify the PDF is not password-protected

## License

This project is provided as-is for educational and development purposes.
