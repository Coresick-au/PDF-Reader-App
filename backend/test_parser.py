"""
Test script for the new /extract-items endpoint.
Creates a sample PDF with line items and tests the structured extraction.
"""

# Sample text that mimics the invoice format
SAMPLE_INVOICE_TEXT = """
Line: 1
Part ID: 14782A
AI4-4 BELTSCALE-2000BW-1000IS
Includes Billet Bearing Shims.
Quantity
2.0
Unit Price
5091.00
Total Price
10182.00

Line: 2
Part ID: XYZ-123
High Performance Widget
Premium quality with extended warranty
Quantity
5.0
Unit Price
299.99
Total Price
1499.95

Line: 3
Part ID: ABC-789
Standard Component
Basic model
Quantity
10.0
Unit Price
50.00
Total Price
500.00
"""

print("Sample Invoice Text:")
print("=" * 60)
print(SAMPLE_INVOICE_TEXT)
print("=" * 60)

# Test the parser directly
import sys
sys.path.append('.')
from main import InvoiceParser

parser = InvoiceParser()
items = parser.parse_line_items(SAMPLE_INVOICE_TEXT)

print("\nExtracted Items:")
print("=" * 60)
import json
print(json.dumps(items, indent=2))
print("=" * 60)
print(f"\nTotal items extracted: {len(items)}")

# Verify expected results
expected_count = 3
if len(items) == expected_count:
    print(f"✓ SUCCESS: Extracted {expected_count} items as expected")
else:
    print(f"✗ FAILED: Expected {expected_count} items, got {len(items)}")

# Check first item details
if items and len(items) > 0:
    first_item = items[0]
    print("\nFirst item validation:")
    print(f"  Line: {first_item.get('line')} (expected: 1)")
    print(f"  Part ID: {first_item.get('part_id')} (expected: 14782A)")
    print(f"  Quantity: {first_item.get('quantity')} (expected: 2.0)")
    print(f"  Unit Price: {first_item.get('unit_price')} (expected: 5091.0)")
    print(f"  Total Price: {first_item.get('total_price')} (expected: 10182.0)")
    
    if (first_item.get('line') == 1 and 
        first_item.get('part_id') == '14782A' and
        first_item.get('quantity') == 2.0 and
        first_item.get('unit_price') == 5091.0 and
        first_item.get('total_price') == 10182.0):
        print("  ✓ All fields match expected values!")
    else:
        print("  ✗ Some fields don't match expected values")
