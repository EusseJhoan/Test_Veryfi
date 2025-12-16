import re
import json
import os
from datetime import datetime
from veryfi import Client

class OCRConfig:
    """
    Configuration Manager for OCR credentials.
    
    Responsibilities:
        - Extracts credentials from a secrets module.
        - Validates that all required keys are present before Client initialization.
    """
    def __init__(self, secrets_module):
        # Safely attempt to retrieve credentials using getattr to avoid AttributeErrors
        self.client_id = getattr(secrets_module, 'CLIENT_ID', None)
        self.client_secret = getattr(secrets_module, 'CLIENT_SECRET', None)
        self.username = getattr(secrets_module, 'USERNAME', None)
        self.api_key = getattr(secrets_module, 'API_KEY', None)

        # Enforce strict validation: Fail fast if the environment is not configured correctly
        if not all([self.client_id, self.client_secret, self.username, self.api_key]):
            raise ValueError("Incomplete credentials in secrets module.")

class VeryfiOCRClient:
    """
    Service Wrapper for the Veryfi API.

    """
    def __init__(self, config: OCRConfig):
        self.client = Client(
            config.client_id,
            config.client_secret,
            config.username,
            config.api_key
        )

    def process(self, file_path: str) -> str:
        """
        Uploads a document to Veryfi and retrieves the unstructured OCR text.
        
        Args:
            file_path (str): The local path to the target file.
            
        Returns:
            str: The raw text extracted from the document.
            
        Raises:
            FileNotFoundError: If local file access fails.
            ValueError: If the API returns a successful response but empty text content.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        print(f"Processing: {file_path}...")
        
        # Call external API to process document
        response = self.client.process_document(file_path)
        ocr_text = response.get("ocr_text")
        
        if not ocr_text:
            raise ValueError(f"No text returned from API for {file_path}")
            
        return ocr_text

class InvalidDocumentFormatError(Exception):
    """
    Custom exception used for flow control.
    
    Raised when a document is successfully OCR'd but fails the specific 
    'fingerprinting' validation for the expected invoice format.
    """
    pass

class InvoiceParser:
    """
    Core Logic Engine.
    
    Responsible for:
    1. Validating that the document matches the  vendor format.
    2. Parsing raw unstructured string data into structured JSON-compatible dictionaries.
    3. handling complex multi-line item extraction using State Machine logic.
    """
    def __init__(self):
        # --- Validation Fingerprints ---
        # These patterns must exist to confirm this is the correct document type.
        # Checks for specific address formats, company names, or table headers.
        self.validation_patterns = [
            re.compile(r"[\w\s]+\s+[\w\s]+,\s*[A-Z]{2}\s*\d{5}-\d{4}", re.IGNORECASE),
            re.compile(r"Please make payments to:\s*[\w\s]+,\s*Ltd\.", re.IGNORECASE),
            re.compile(r"Description\s+Quantity\s+Rate\s+Amount", re.IGNORECASE)
        ]

        # --- Extraction Patterns ---
        # 1. Header: Extracts date (MM/DD/YY) and the invoice number.
        self.header_pattern = re.compile(r"(?P<dates>\d{2}/\d{2}/\d{2})\t\d{2}/\d{2}/\d{2}\t(?P<invoice_num>\d+)")
        
        # 2. Vendor: Extracts vendor name and split address lines using tab delimiters.
        self.vendor_pattern = re.compile(r"(?:Invoice|Page\s+\d+\s+of\s+\d+)\s+(?P<vendor>[^\t\n]+)\t(?P<addr_line1>[^\n]+)\n(?P<addr_line2>[^\t\n]+)")
        
        # 3. Bill To: Captures the multi-line block following the date/invoice row.
        self.bill_to_pattern = re.compile(r"\d{2}/\d{2}/\d{2}\t\d{2}/\d{2}/\d{2}\t\d+\n+(?P<bill>.*?)\n")
        
        # 4. Line Items: Captures Description, Quantity, Rate, and Amount.
        #    Note: Handles negative numbers and comma separators.
        self.item_pattern = re.compile(r"(?P<desc>.*?)\s+(?P<qty>-?[\d,]+\.\d{2})\s+(?P<rate>-?[\d,]+\.\d{2})\s+(?P<amt>-?[\d,]+\.\d{2})\s*$")
        
        # 5. Total: Captures the final USD total.
        self.total_pattern = re.compile(r"Total USD\s+\$?(?P<total>-?[\d,]+\.\d{2})")

    def validate_format(self, text: str):
        """
        Performs a 'fingerprint' check. If the text doesn't contain at least one 
        distinctive feature of the expected vendor, processing stops immediately.
        """
        if not any(pattern.search(text) for pattern in self.validation_patterns):
            raise InvalidDocumentFormatError("Document does not match invoice format.")

    def parse(self, text: str) -> dict:
        """
        Orchestrates the extraction pipeline.
        
        Args:
            text (str): The raw text from the OCR client.
            
        Returns:
            dict: A clean, structured dictionary of the invoice data.
        """
        # 1. Ensure this is the right document type
        self.validate_format(text)

        # 2. Pre-processing: Split by Form Feed (\x0c) to handle pagination
        data = {}
        pages = text.split('\x0c')
        first_page = pages[0] # Header info usually resides on page 1

        # 3. Extract Global Metadata (Headers, Vendor, Customer)
        data.update(self._extract_header(first_page))
        data.update(self._extract_vendor(first_page))
        data.update(self._extract_customer(first_page))
        
        # 4. Extract Tabular Data (Line items across all pages)
        line_item_data = self._extract_line_items(pages)
        data.update(line_item_data)
        
        return data

    def _extract_header(self, text: str) -> dict:
        """Parses invoice dates and ID numbers, normalizing dates to ISO 8601."""
        match = self.header_pattern.search(text)
        result = {}
        if match:
            raw_date = match.group('dates')
            try:
                dt_object = datetime.strptime(raw_date, "%m/%d/%y")
                result['date'] = dt_object.strftime("%Y-%m-%d")
            except ValueError:
                # Fallback to raw string if date parsing fails
                result['date'] = raw_date
            result['invoice_number'] = match.group('invoice_num').strip()
        return result

    def _extract_vendor(self, text: str) -> dict:
        """Parses vendor details and constructs a full address string."""
        match = self.vendor_pattern.search(text)
        if match:
            return {
                'vendor_name': match.group('vendor').capitalize(),
                'vendor_address': f"{match.group('addr_line2').strip()}. {match.group('addr_line1').strip()}"
            }
        return {}

    def _extract_customer(self, text: str) -> dict:
        """Extracts the 'Bill To' entity."""
        match = self.bill_to_pattern.search(text)
        if match:
            return {'bill_to_name': match.group('bill')}
        return {}

    def _extract_line_items(self, pages: list) -> dict:
        """
        Parses the table of line items.
        
        State:
            - `current_item`: Holds the dictionary of the item currently being built.
            
        Logic:
            1. If a line matches the `item_pattern` (ends with numbers), we start a new item.
            2. If we hit the `Total USD` line, we finalize and exit.
            3. If a line does NOT match the pattern but we have an active `current_item`,
               we assume it is a continuation of the previous description (unless it matches a stop keyword).
        """
        data = {'total': 0.0, 'line_items': []}
        current_item = None
        
        # Flatten all pages into a single stream of lines
        all_lines = []
        for page in pages:
            all_lines.extend(page.splitlines())

        # Keywords that indicate a line is NOT part of a description continuation
        stop_keywords = ["Invoice", "Page ", "Account No", "Please update", "Description"]

        for line in all_lines:
            line = line.strip()
            if not line: continue
            
            # Check if this line is a new Item row (contains Qty, Rate, Amount)
            item_match = self.item_pattern.match(line)
            
            if item_match:
                # If we were building a previous item, save it now
                if current_item:
                    data['line_items'].append(current_item)
                
                # Initialize new item state
                current_item = {
                    'description': item_match.group('desc').strip(),
                    'quantity': float(item_match.group('qty').replace(',', '')),
                    'price': float(item_match.group('rate').replace(',', '')),
                    'total': float(item_match.group('amt').replace(',', '')),
                    'sku': None,
                    'tax_rate': None
                }
            
            # Check for the Invoice Footer/Total
            elif "Total USD" in line:
                total_match = self.total_pattern.search(line)
                if total_match:
                    data['total'] = float(total_match.group('total').replace(',', ''))
                # Save the final item pending in memory
                if current_item:
                    data['line_items'].append(current_item)
                    current_item = None
                break # End of table processing
            
            # Handling Multi-line descriptions
            elif current_item:
                # If we hit a header/footer keyword, close the current item
                if any(keyword in line for keyword in stop_keywords):
                    data['line_items'].append(current_item)
                    current_item = None
                else:
                    # Append this line to the previous item's description
                    current_item['description'] += " " + line

        # Store last item if loop finishes but an item is still open
        if current_item:
            data['line_items'].append(current_item)
            
        return data

class DataSaver:
    """Handles IO operations for persisting extracted data to disk."""
    def __init__(self, output_dir="extractedData"):
        self.output_dir = output_dir
        # Ensure output directory exists to prevent FileNotFoundError on write
        os.makedirs(self.output_dir, exist_ok=True)

    def save(self, data: dict, original_filepath: str):
        """
        Saves the dictionary as a JSON file, mirroring the original filename.
        """
        filename_only = os.path.splitext(os.path.basename(original_filepath))[0]
        output_filename = f"{filename_only}_data.json"
        full_path = os.path.join(self.output_dir, output_filename)
        
        with open(full_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Success: Saved to {full_path}")