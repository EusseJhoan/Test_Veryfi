import os
import invoice_processor  # The module we are testing

# --- MOCK_OCR_TEXT ---

SAMPLE_OCR_TEXT = """
Invoice
	Page 1 of 2
Generic Corp	City, ST 12345-6789
PO Box 000000

	Invoice Date Due Date	Invoice No.
	09/06/24	05/06/24	0123456

Company, Inc.
Address Line 1
Address Line 2

Account No.			P.O. Number
	Services for month of November
O-0000000					PO-0000-0000
Description				Quantity	Rate	Amount
Transport | 71 Gbps Fiber (08/2025)				1,000.00	500.00	5,000,000.00
Transport |  Fiber Pair (Intra-campus) | Pairs  (05/2025 | 10 Gbps Fiber	1,000.00	500.00	5,000,000.00
to xxxxxxxx (04/2024)

	Invoice
Generic Corp	City, ST 12345-6789
PO Box 000000								Page 2 of 2

	Invoice Date Due Date	Invoice No.
	09/06/24	05/06/24	0123456

Company, Inc.
Address Line 1
Address Line 2

Account No.			P.O. Number
	Services for month of November
O-0000000				PO-0000-0000
Description				Quantity	Rate	Amount
Installation of Cross Connect | 023 Gbps Fiber 		1,000.00	500.00	5,000,000.00
	Total USD	$15,000,000.00
Please make payments to: Generic Corp, Ltd.
"""

EXPECTED_JSON_RESULT = {
    "date": "2024-09-06",
    "invoice_number": "0123456",
    "vendor_name": "Generic corp",
    "vendor_address": "PO Box 000000. City, ST 12345-6789",
    "bill_to_name": "Company, Inc.",
    "total": 15000000.0,
    "line_items": [
        {
            "description": "Transport | 71 Gbps Fiber (08/2025)",
            "quantity": 1000.0,
            "price": 500.0,
            "total": 5000000.0,
            'sku': None,
            'tax_rate': None
        },
        {
            "description": "Transport |  Fiber Pair (Intra-campus) | Pairs  (05/2025 | 10 Gbps Fiber to xxxxxxxx (04/2024)",
            "quantity": 1000.0,
            "price": 500.0,
            "total": 5000000.0,
            'sku': None,
            'tax_rate': None
        },
        {
            "description": "Installation of Cross Connect | 023 Gbps Fiber",
            "quantity": 1000.0,
            "price": 500.0,
            "total": 5000000.0,
            'sku': None,
            'tax_rate': None
        }
    ]
}

# --- Test Functions ---

def test_format_validation():
    """
    Verify that validate_format correctly accepts valid layouts
    and raises InvalidDocumentFormatError for mismatched documents.
    """
    print("Running test_format_validation...", end=" ")
    
    parser = invoice_processor.InvoiceParser()
    
    # Sub-test 1: Valid Text (Should pass silently)
    try:
        parser.validate_format(SAMPLE_OCR_TEXT)
    except invoice_processor.InvalidDocumentFormatError:
        print("FAIL (Positive case)")
        print("Valid text was rejected! Check regex patterns.")
        return
    except Exception as e:
        print(f"FAIL (Positive case): Unexpected error {e}")
        return

    # Sub-test 2: Invalid Text (Should raise exception)
    # This text lacks the specific address format and payment instruction
    invalid_text = """
    Invoice
    Some Other Vendor
    123 Main St
    
    Total: $500.00
    """
    
    try:
        parser.validate_format(invalid_text)
        print("FAIL (Negative case)")
        print("Invalid text was incorrectly accepted!")
    except invoice_processor.InvalidDocumentFormatError:
        print("PASS")
    except Exception as e:
        print(f"FAIL (Negative case): Unexpected error {e}")
        
        
def test_full_data_extraction():
    """
    Validate that the InvoiceParser extracts the OCR text 
    and produces a JSON structure exactly matching expectations.
    """
    print("Running test_full_data_extraction...", end=" ")
    
    parser = invoice_processor.InvoiceParser()
    
    # Execute parsing logic
    actual_result = parser.parse(SAMPLE_OCR_TEXT)
    
    # Compare dictionaries
    try:
        assert actual_result == EXPECTED_JSON_RESULT
        print("PASS")
    except AssertionError:
        print("FAIL")
        print(f"Expected: {EXPECTED_JSON_RESULT}")
        print(f"Got:      {actual_result}")



if __name__ == "__main__":
    print("--- Starting Unit Tests ---\n")
    test_format_validation()
    test_full_data_extraction()
    print("\n--- Tests Finished ---")