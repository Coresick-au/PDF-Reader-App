from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
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


# --- CONFIGURATION: NOISE PATTERNS ---
class NoisePatterns:
    """Configurable regex patterns for filtering noise from extracted text"""
    
    EMAIL = r'\b[\w\.-]+@[\w\.-]+\.\w+\b'
    URL = r'https?://(?:www\.)?[\w\.-]+\.\w+(?:/[\w\.-]*)*'
    PHONE = r'\b\d{4}\s?\d{3}\s?\d{3}\b|\b1300\s?\d{3}\s?\d{3}\b'
    ABN = r'ABN\s+\d{2}\s+\d{3}\s+\d{3}\s+\d{3}'
    
    @classmethod
    def get_all_patterns(cls) -> List[str]:
        """Returns all noise patterns as a list"""
        return [cls.EMAIL, cls.URL, cls.PHONE, cls.ABN]


# ============================================================================
# STRATEGY PATTERN: VENDOR-SPECIFIC EXTRACTION
# ============================================================================

class VendorStrategy(ABC):
    """
    Abstract base class for vendor-specific PDF extraction strategies.
    """
    
    def __init__(self):
        self.noise_patterns = NoisePatterns.get_all_patterns()
    
    @abstractmethod
    def can_handle(self, first_page_text: str) -> bool:
        pass
    
    @abstractmethod
    def extract(self, pdf) -> List[Dict]:
        pass
    
    def _clean_description(self, text: str) -> str:
        """Remove noise patterns from description text."""
        cleaned = text
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned


class BillroyStrategy(VendorStrategy):
    """
    Strategy for parsing Billroy quote PDFs.
    Uses regex-based "Line: X" anchor parsing for unstructured text.
    """
    
    def can_handle(self, first_page_text: str) -> bool:
        return "BILLROY" in first_page_text.upper()
    
    def extract(self, pdf) -> List[Dict]:
        all_items = []
        for page in pdf.pages:
            raw_text = page.extract_text() or ""
            items = self._parse_line_items(raw_text)
            all_items.extend(items)
        return all_items
    
    def _parse_line_items(self, text: str) -> List[Dict]:
        blocks = self._split_into_blocks(text)
        items = []
        for block in blocks:
            item = self._extract_fields(block)
            if item:
                items.append(item)
        return items
    
    def _split_into_blocks(self, text: str) -> List[str]:
        parts = re.split(r'(Line:\s*\d+)', text)
        blocks = []
        current_block = ""
        for part in parts:
            if re.match(r'Line:\s*\d+', part):
                if current_block.strip():
                    blocks.append(current_block.strip())
                current_block = part
            else:
                current_block += part
        if current_block.strip():
            blocks.append(current_block.strip())
        return blocks
    
    def _extract_fields(self, block: str) -> Optional[Dict]:
        item = {}
        
        # Extract Line Number
        line_match = re.search(r'Line:\s*(\d+)', block)
        if not line_match:
            return None
        item['line_item'] = int(line_match.group(1))
        
        # Extract Part ID
        part_id_match = re.search(r'Part ID:\s*([A-Z0-9-]+)', block, re.IGNORECASE)
        item['part_id'] = part_id_match.group(1).strip() if part_id_match else None
        
        # Extract Description
        description = self._extract_description(block)
        item['description'] = self._clean_description(description)
        
        # Extract Quantity
        quantity_match = re.search(r'Quantity[:\s]*\n?\s*([\d,]+\.?\d*)', block, re.IGNORECASE)
        if quantity_match:
            qty_str = quantity_match.group(1).replace(',', '')
            try:
                item['qty'] = float(qty_str)
            except ValueError:
                item['qty'] = None
        else:
            item['qty'] = None
        
        # Extract Unit Price
        unit_price_match = re.search(r'Unit Price[:\s]*\n?\s*\$?\s*([\d,]+\.?\d*)', block, re.IGNORECASE)
        if unit_price_match:
            price_str = unit_price_match.group(1).replace(',', '')
            try:
                item['price'] = float(price_str)
            except ValueError:
                item['price'] = None
        else:
            item['price'] = None
        
        return item
    
    def _extract_description(self, block: str) -> str:
        pattern = r'Part ID:\s*[A-Z0-9-]+\s*\n?(.*?)(?=Quantity|Unit Price|Total Price|$)'
        match = re.search(pattern, block, re.IGNORECASE | re.DOTALL)
        if match:
            description = match.group(1).strip()
            description = re.sub(r'\s+', ' ', description)
            return description
        return ""


class CPSStrategy(VendorStrategy):
    """
    Strategy for parsing CPS (Conveyor Products & Solutions) quote PDFs.
    Uses pdfplumber's table extraction for structured grid data.
    """
    
    def can_handle(self, first_page_text: str) -> bool:
        text_upper = first_page_text.upper()
        return "CONVEYOR PRODUCTS" in text_upper or "CPS" in text_upper
    
    def extract(self, pdf) -> List[Dict]:
        all_items = []
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            table = tables[0]
            items = self._parse_table(table)
            all_items.extend(items)
        return all_items
    
    def _parse_table(self, table: List[List[str]]) -> List[Dict]:
        items = []
        current_item = None
        
        for row_idx, row in enumerate(table):
            if row_idx < 2: continue
            if len(row) < 7: continue
            
            line_item_col = row[0] if row[0] else ""
            description_col = row[1] if row[1] else ""
            qty_col = row[5] if len(row) > 5 and row[5] else ""
            price_col = row[6] if len(row) > 6 and row[6] else ""
            
            if line_item_col.strip() and line_item_col.strip().isdigit():
                if current_item:
                    items.append(current_item)
                current_item = {
                    'line_item': int(line_item_col.strip()),
                    'part_id': None,
                    'description': description_col.strip(),
                    'qty': self._parse_number(qty_col),
                    'price': self._parse_price(price_col)
                }
            elif current_item and description_col.strip():
                continuation_text = description_col.strip()
                if re.match(r'^[A-Z0-9-]+$', continuation_text, re.IGNORECASE):
                    current_item['part_id'] = continuation_text
                else:
                    if not self._is_noise_row(continuation_text):
                        current_item['description'] += " " + continuation_text
        
        if current_item:
            items.append(current_item)
        
        for item in items:
            item['description'] = self._clean_description(item['description'])
        
        return items
    
    def _parse_number(self, value: str) -> Optional[float]:
        if not value: return None
        cleaned = value.replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _parse_price(self, value: str) -> Optional[float]:
        if not value: return None
        cleaned = value.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _is_noise_row(self, text: str) -> bool:
        noise_keywords = ["grub screw", "includes", "note:", "see attached"]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in noise_keywords)


# ============================================================================
# STRATEGY REGISTRY & FACTORY
# ============================================================================

STRATEGIES: List[type[VendorStrategy]] = [
    BillroyStrategy,
    CPSStrategy,
]

def get_strategy(pdf_content: bytes) -> VendorStrategy:
    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
        if not pdf.pages:
            raise HTTPException(status_code=400, detail="PDF has no pages")
        
        first_page_text = pdf.pages[0].extract_text() or ""
        
        for strategy_class in STRATEGIES:
            strategy = strategy_class()
            if strategy.can_handle(first_page_text):
                return strategy
        
        raise HTTPException(
            status_code=400,
            detail="Unsupported vendor format. Unable to detect vendor from PDF header."
        )


# ============================================================================
# LEGACY FUNCTIONS
# ============================================================================

def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    kept_lines = []
    for line in lines:
        should_remove = False
        for phrase in IGNORE_PHRASES:
            if phrase.lower() in line.lower():
                should_remove = True
                break
        if not should_remove and line.strip() != "":
            kept_lines.append(line.strip())
    
    combined_lines = []
    current_comment = ""
    for line in kept_lines:
        if re.match(r'^\d+\.?\s', line):
            if current_comment:
                combined_lines.append(current_comment)
            current_comment = line
        else:
            if current_comment:
                current_comment += " " + line
            else:
                combined_lines.append(line)
    if current_comment:
        combined_lines.append(current_comment)
    return "\n".join(combined_lines)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/upload")
async def process_pdf(file: UploadFile = File(...)):
    """
    Original endpoint for backward compatibility.
    """
    contents = await file.read()
    results = []

    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            width = page.width
            height = page.height
            
            if page_num == 3:
                left_bbox = (0, 0, width / 2, height)
                left_crop = page.crop(bbox=left_bbox)
                raw_left = left_crop.extract_text() or ""
                
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
                raw_text = page.extract_text() or ""
                results.append({
                    "page": page_num,
                    "type": "Full Page",
                    "content": clean_text(raw_text)
                })

    return {"data": results}


@app.post("/extract-items")
async def extract_line_items(
    file: UploadFile = File(...),
    start_marker: Optional[str] = Form(None),
    end_marker: Optional[str] = Form(None)
):
    """
    Smart endpoint with automatic vendor detection or manual extraction.
    """
    contents = await file.read()
    
    # Check if manual markers are provided
    if start_marker and end_marker:
        # Manual extraction mode
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            # Collect all text
            all_text = ""
            for page in pdf.pages:
                all_text += (page.extract_text() or "") + "\n"
            
            # Extract section between markers
            start_idx = all_text.find(start_marker)
            if start_idx == -1:
                start_idx = 0
            
            end_idx = all_text.find(end_marker, start_idx)
            if end_idx == -1:
                section_text = all_text[start_idx:]
            else:
                section_text = all_text[start_idx:end_idx + len(end_marker)]
            
            # Use BillroyStrategy's parsing on the section
            billroy = BillroyStrategy()
            items = billroy._parse_line_items(section_text)
        
        vendor_name = "manual"
    else:
        # Auto-detection mode
        strategy = get_strategy(contents)
        vendor_name = strategy.__class__.__name__.replace("Strategy", "").lower()
        
        # Extract items using the strategy
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            items = strategy.extract(pdf)
    
    return {
        "vendor": vendor_name,
        "items": items,
        "count": len(items)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)