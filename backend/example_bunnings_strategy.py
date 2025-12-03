"""
Example: Adding a new Bunnings vendor strategy
This demonstrates how easy it is to extend the system with new vendors.
"""

from main import VendorStrategy, STRATEGIES
import re
from typing import List, Dict, Optional

class BunningsStrategy(VendorStrategy):
    """
    Strategy for parsing Bunnings quote PDFs.
    Example of how easy it is to add a new vendor!
    """
    
    def can_handle(self, first_page_text: str) -> bool:
        """Check if this is a Bunnings document"""
        return "BUNNINGS" in first_page_text.upper()
    
    def extract(self, pdf) -> List[Dict]:
        """
        Extract line items from Bunnings PDF.
        
        This is a placeholder implementation - you would customize
        this based on the actual Bunnings PDF format.
        """
        all_items = []
        
        for page in pdf.pages:
            raw_text = page.extract_text() or ""
            
            # Example: If Bunnings uses a simple line-by-line format
            items = self._parse_bunnings_format(raw_text)
            all_items.extend(items)
        
        return all_items
    
    def _parse_bunnings_format(self, text: str) -> List[Dict]:
        """
        Parse Bunnings-specific format.
        Customize this based on actual Bunnings PDF structure.
        """
        items = []
        
        # Example pattern: "Item 1: Widget - Qty: 5 - Price: $99.99"
        pattern = r'Item\s+(\d+):\s+([^-]+)-\s+Qty:\s+([\d.]+)\s+-\s+Price:\s+\$?([\d,.]+)'
        
        for match in re.finditer(pattern, text):
            item = {
                'line_item': int(match.group(1)),
                'part_id': None,  # Bunnings may not have part IDs
                'description': self._clean_description(match.group(2).strip()),
                'qty': float(match.group(3)),
                'price': float(match.group(4).replace(',', ''))
            }
            items.append(item)
        
        return items


# ============================================================================
# TO ACTIVATE THIS STRATEGY:
# ============================================================================
# 
# Simply add BunningsStrategy to the STRATEGIES list in main.py:
#
# STRATEGIES: List[type[VendorStrategy]] = [
#     BillroyStrategy,
#     CPSStrategy,
#     BunningsStrategy,  # <-- Add this line!
# ]
#
# That's it! The system will now automatically detect and parse Bunnings PDFs.
# ============================================================================


if __name__ == "__main__":
    # Test the Bunnings strategy
    print("Testing BunningsStrategy...")
    
    bunnings_text = """
    BUNNINGS WAREHOUSE
    Quote #12345
    
    Item 1: Hammer - Qty: 2 - Price: $15.99
    Item 2: Screwdriver Set - Qty: 1 - Price: $29.99
    Item 3: Paint Roller - Qty: 5 - Price: $8.50
    """
    
    strategy = BunningsStrategy()
    
    # Test detection
    can_handle = strategy.can_handle(bunnings_text)
    print(f"✓ Can handle Bunnings text: {can_handle}")
    
    # Test extraction (with mock PDF)
    class MockPage:
        def extract_text(self):
            return bunnings_text
    
    class MockPDF:
        def __init__(self):
            self.pages = [MockPage()]
    
    mock_pdf = MockPDF()
    items = strategy.extract(mock_pdf)
    
    print(f"✓ Extracted {len(items)} items")
    
    for item in items:
        print(f"\nItem {item['line_item']}:")
        print(f"  Description: {item['description']}")
        print(f"  Qty: {item['qty']}")
        print(f"  Price: ${item['price']:.2f}")
    
    print("\n✅ BunningsStrategy is ready to be added to main.py!")
