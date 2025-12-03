# Manual Strategy for PDF Extraction
# Add this class to main.py before the STRATEGIES registry

class ManualStrategy(VendorStrategy):
    """
    Strategy for manual marker-based extraction.
    Used as a fallback when auto-detection fails.
    """
    
    def __init__(self, start_marker: str = None, end_marker: str = None):
        super().__init__()
        self.start_marker = start_marker
        self.end_marker = end_marker
    
    def can_handle(self, first_page_text: str) -> bool:
        """Manual strategy is explicitly invoked, not auto-detected"""
        return False  # Never auto-selected
    
    def extract(self, pdf) -> List[Dict]:
        """
        Extract line items using custom start/end markers.
        
        Process:
        1. Extract all text from PDF
        2. Find text between start_marker and end_marker
        3. Parse that section for line items using generic regex
        """
        all_text = ""
        
        # Collect all text from PDF
        for page in pdf.pages:
            raw_text = page.extract_text() or ""
            all_text += raw_text + "\n"
        
        # Extract section between markers
        section_text = self._extract_section(all_text)
        
        # Parse line items from the section
        items = self._parse_generic_items(section_text)
        
        return items
    
    def _extract_section(self, text: str) -> str:
        """Extract text between start and end markers"""
        if not self.start_marker or not self.end_marker:
            return text
        
        # Find start marker
        start_idx = text.find(self.start_marker)
        if start_idx == -1:
            # Start marker not found, use entire text
            start_idx = 0
        
        # Find end marker (search after start)
        end_idx = text.find(self.end_marker, start_idx)
        if end_idx == -1:
            # End marker not found, use to end of text
            return text[start_idx:]
        
        # Return text between markers (inclusive of start, exclusive of end)
        return text[start_idx:end_idx]
    
    def _parse_generic_items(self, text: str) -> List[Dict]:
        """
        Parse line items using generic patterns.
        Looks for common patterns like:
        - Lines starting with numbers
        - Part codes (alphanumeric with dashes)
        - Prices (numbers with $ or decimal points)
        - Quantities (standalone numbers)
        """
        items = []
        lines = text.split('\n')
        
        current_item = None
        line_counter = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Pattern 1: Line starts with "Line: X" or just a number
            line_match = re.match(r'^(?:Line:?\s*)?(\d+)[\s\.]', line)
            if line_match:
                # Save previous item
                if current_item:
                    items.append(current_item)
                
                # Start new item
                line_counter += 1
                current_item = {
                    'line_item': int(line_match.group(1)),
                    'part_id': None,
                    'description': '',
                    'qty': None,
                    'price': None
                }
                continue
            
            if not current_item:
                # If we haven't found a line marker yet, try to detect items by other patterns
                # Look for lines that might be part IDs (alphanumeric codes)
                if re.match(r'^[A-Z0-9]{3,}[-\s]?[A-Z0-9]*', line, re.IGNORECASE):
                    line_counter += 1
                    current_item = {
                        'line_item': line_counter,
                        'part_id': line.split()[0] if line else None,
                        'description': '',
                        'qty': None,
                        'price': None
                    }
                continue
            
            # Try to extract part ID (alphanumeric code)
            if not current_item['part_id']:
                part_match = re.search(r'\b([A-Z0-9]{3,}[-]?[A-Z0-9]*)\b', line, re.IGNORECASE)
                if part_match and not re.match(r'^\d+\.?\d*$', part_match.group(1)):
                    current_item['part_id'] = part_match.group(1)
            
            # Try to extract quantity
            if current_item['qty'] is None:
                qty_match = re.search(r'\b(\d+\.?\d*)\s*(?:ea|each|pcs?|units?)?(?:\s|$)', line, re.IGNORECASE)
                if qty_match:
                    try:
                        current_item['qty'] = float(qty_match.group(1))
                    except ValueError:
                        pass
            
            # Try to extract price
            if current_item['price'] is None:
                price_match = re.search(r'\$?\s*([\d,]+\.?\d{0,2})', line)
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(',', '')
                        price_val = float(price_str)
                        # Only accept if it looks like a price (> 0.01)
                        if price_val >= 0.01:
                            current_item['price'] = price_val
                    except ValueError:
                        pass
            
            # Add to description if it's not a price/qty line
            if not re.match(r'^\s*(?:qty|quantity|price|total|unit)[\s:]*[\d\$]', line, re.IGNORECASE):
                if current_item['description']:
                    current_item['description'] += ' ' + line
                else:
                    current_item['description'] = line
        
        # Don't forget the last item
        if current_item:
            items.append(current_item)
        
        # Clean descriptions
        for item in items:
            if item['description']:
                item['description'] = self._clean_description(item['description'])
        
        return items


# Update the /extract-items endpoint to accept optional markers:
# 
# @app.post("/extract-items")
# async def extract_line_items(
#     file: UploadFile = File(...),
#     start_marker: str = Form(None),
#     end_marker: str = Form(None)
# ):
#     contents = await file.read()
#     
#     # Check if manual markers are provided
#     if start_marker and end_marker:
#         # Use ManualStrategy
#         strategy = ManualStrategy(start_marker, end_marker)
#         vendor_name = "manual"
#     else:
#         # Use auto-detection
#         strategy = get_strategy(contents)
#         vendor_name = strategy.__class__.__name__.replace("Strategy", "").lower()
#     
#     # Extract items using the strategy
#     with pdfplumber.open(io.BytesIO(contents)) as pdf:
#         items = strategy.extract(pdf)
#     
#     return {
#         "vendor": vendor_name,
#         "items": items,
#         "count": len(items)
#     }
