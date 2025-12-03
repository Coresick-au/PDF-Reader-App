from fastapi import FastAPI, File, UploadFile, HTTPException
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
    
    To add a new vendor:
    1. Create a new class that inherits from VendorStrategy
    2. Implement can_handle() to detect your vendor's format
    3. Implement extract() to parse the PDF
    4. Add the class to the STRATEGIES list at the bottom
    """
    
    def __init__(self):
        self.noise_patterns = NoisePatterns.get_all_patterns()
    
    @abstractmethod
    def can_handle(self, first_page_text: str) -> bool:
        """
        Determine if this strategy can handle the given PDF.
        
        Args:
            first_page_text: Text from the first page of the PDF
            
        Returns:
            True if this strategy should handle this PDF, False otherwise
        """
        pass
    
    @abstractmethod
    def extract(self, pdf) -> List[Dict]:
        """
        Extract structured data from the PDF.
        
        Args:
            pdf: pdfplumber PDF object
            
        Returns:
            List of dictionaries with standardized format:
            {
                'line_item': int,
                'part_id': str,
                'description': str,
                'qty': float,
                'price': float
            }
        """
        pass
    
    def _clean_description(self, text: str) -> str:
        """
        Remove noise patterns (emails, URLs, phone numbers) from description text.
        
        Args:
            text: Raw description text
            
        Returns:
            Cleaned description text
        """
        cleaned = text
        
        # Remove each noise pattern
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace left by removals
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned


class BillroyStrategy(VendorStrategy):
    """
    Strategy for parsing Billroy quote PDFs.
    Uses regex-based "Line: X" anchor parsing for unstructured text.
    """
    
    def can_handle(self, first_page_text: str) -> bool:
        """Check if this is a Billroy document"""
        return "BILLROY" in first_page_text.upper()
    
    def extract(self, pdf) -> List[Dict]:
        """
        Extract line items from Billroy PDF using regex anchor parsing.
        
        Billroy format:
            Line: 1
            Part ID: ABC123
            Description text...
            Quantity
            2.0
            Unit Price
            100.00
        """
        all_items = []
        
        for page in pdf.pages:
            raw_text = page.extract_text() or ""
            items = self._parse_line_items(raw_text)
            all_items.extend(items)
        
        return all_items
    
    def _parse_line_items(self, text: str) -> List[Dict]:
        """Parse line items from text using regex"""
        blocks = self._split_into_blocks(text)
        items = []
        
        for block in blocks:
            item = self._extract_fields(block)
            if item:
                items.append(item)
        
        return items
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """Split text into individual line item blocks based on 'Line: X' markers"""
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
        """Extract all fields from a single line item block"""
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
        """Extract description text from a line item block"""
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
        """Check if this is a CPS document"""
        text_upper = first_page_text.upper()
        return "CONVEYOR PRODUCTS" in text_upper or "CPS" in text_upper
    
    def extract(self, pdf) -> List[Dict]:
        """
        Extract line items from CPS PDF using table extraction.
        
        CPS format uses a structured table with columns:
        Col 0: Line Item
        Col 1: Description (may span multiple rows)
        Col 5: Qty
        Col 6: Unit Price
        """
        all_items = []
        
        for page in pdf.pages:
            # Extract table from page
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            # Process the first/main table on the page
            table = tables[0]
            items = self._parse_table(table)
            all_items.extend(items)
        
        return all_items
    
    def _parse_table(self, table: List[List[str]]) -> List[Dict]:
        """Parse items from extracted table data"""
        items = []
        current_item = None
        
        for row_idx, row in enumerate(table):
            # Skip header rows (usually first 1-2 rows)
            if row_idx < 2:
                continue
            
            # Ensure row has enough columns
            if len(row) < 7:
                continue
            
            line_item_col = row[0] if row[0] else ""
            description_col = row[1] if row[1] else ""
            qty_col = row[5] if len(row) > 5 and row[5] else ""
            price_col = row[6] if len(row) > 6 and row[6] else ""
            
            # Check if this is a new line item (has a line number)
            if line_item_col.strip() and line_item_col.strip().isdigit():
                # Save previous item if exists
                if current_item:
                    items.append(current_item)
                
                # Start new item
                current_item = {
                    'line_item': int(line_item_col.strip()),
                    'part_id': None,  # CPS may not have part IDs in same format
                    'description': description_col.strip(),
                    'qty': self._parse_number(qty_col),
                    'price': self._parse_price(price_col)
                }
            
            elif current_item and description_col.strip():
                # This is a continuation row - append to description
                # Common pattern: "Weigh Roller" on one row, "R04..." on next row
                continuation_text = description_col.strip()
                
                # Check if this looks like a part ID (alphanumeric code)
                if re.match(r'^[A-Z0-9-]+$', continuation_text, re.IGNORECASE):
                    current_item['part_id'] = continuation_text
                else:
                    # Append to description, filtering out noise like "Grub Screw"
                    if not self._is_noise_row(continuation_text):
                        current_item['description'] += " " + continuation_text
        
        # Don't forget the last item
        if current_item:
            items.append(current_item)
        
        # Clean all descriptions
        for item in items:
            item['description'] = self._clean_description(item['description'])
        
        return items
    
    def _parse_number(self, value: str) -> Optional[float]:
        """Parse a numeric value from string"""
        if not value:
            return None
        
        # Remove commas and whitespace
        cleaned = value.replace(',', '').strip()
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _parse_price(self, value: str) -> Optional[float]:
        """Parse a price value (removes $ sign)"""
        if not value:
            return None
        
        # Remove $, commas, and whitespace
        cleaned = value.replace('$', '').replace(',', '').strip()
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _is_noise_row(self, text: str) -> bool:
        """Check if a row is noise that should be filtered out"""
        noise_keywords = [
            "grub screw",
            "includes",
            "note:",
            "see attached",
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in noise_keywords)


# ============================================================================
# STRATEGY REGISTRY & FACTORY
# ============================================================================

# Register all available strategies here
# To add a new vendor, just add the class to this list!
STRATEGIES: List[type[VendorStrategy]] = [
    BillroyStrategy,
    CPSStrategy,
    # Add more strategies here as needed
]


def get_strategy(pdf_content: bytes) -> VendorStrategy:
    """
    Factory function to get the appropriate strategy for a PDF.
    
    Args:
        pdf_content: Raw PDF file bytes
        
    Returns:
        Initialized strategy instance
        
    Raises:
        HTTPException: If no strategy can handle the PDF
    """
    # Open PDF and read first page
    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
        if not pdf.pages:
            raise HTTPException(status_code=400, detail="PDF has no pages")
        
        first_page_text = pdf.pages[0].extract_text() or ""
        
        # Try each strategy
        for strategy_class in STRATEGIES:
            strategy = strategy_class()
            if strategy.can_handle(first_page_text):
                return strategy
        
        # No strategy found
        raise HTTPException(
            status_code=400,
            detail="Unsupported vendor format. Unable to detect vendor from PDF header."
        )


# ============================================================================
# LEGACY FUNCTIONS (for backward compatibility)
# ============================================================================

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
    Extracts text from PDF and returns cleaned text by page.
    """
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


@app.post("/extract-items")
async def extract_line_items(file: UploadFile = File(...)):
    """
    Smart endpoint with automatic vendor detection.
    Uses Strategy Pattern to handle different vendor formats.
    
    Returns:
        {
            "vendor": str,  # Detected vendor name
            "items": List[Dict],  # Extracted line items
            "count": int  # Number of items
        }
    
    Raises:
        HTTPException 400: If vendor format is not supported
    """
    contents = await file.read()
    
    # Get the appropriate strategy
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