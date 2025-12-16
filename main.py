import os
import app_secrets
from invoice_processor import (
    OCRConfig, 
    VeryfiOCRClient, 
    InvoiceParser, 
    DataSaver, 
    InvalidDocumentFormatError
)

def load_file_list(list_path):
    """
    Utility to read the batch file text list.
    
    Args:
        list_path (str): Path to the text file containing file paths.
    
    Returns:
        list: A list of file path strings.
    """
    if not os.path.exists(list_path):
        print(f"Error: The file list '{list_path}' was not found.")
        return []
        
    with open(list_path, 'r') as f:
        # Read lines and strip whitespace, filtering out empty lines
        files = [line.strip() for line in f if line.strip()]
    return files

def main():
    """
    Main Execution Pipeline.
    
    Workflow:
    1. Initialize Service Objects (Config, Client, Parser, Saver).
    2. Load the list of files to process.
    3. Iterate through files, applying OCR -> Parse -> Save logic.
    """
    
    # 1. Setup & Dependency Injection
    try:
        config = OCRConfig(app_secrets)
        ocr_client = VeryfiOCRClient(config)
        parser = InvoiceParser()
        saver = DataSaver("extractedData")
    except ValueError as e:
        # Critical failure: If config fails, we cannot proceed with any file.
        print(f"Configuration Error: {e}")
        return

    # 2. Load Batch List
    input_list_file = "batch_files.txt"
    files_to_process = load_file_list(input_list_file)
    
    if not files_to_process:
        print("No files to process.")
        return

    print(f"Starting batch processing for {len(files_to_process)} documents...")

    # 3. Batch Process
    for file_path in files_to_process:
        try:
            # Step A: OCR Extraction
            # Fetches raw text from the external provider
            raw_text = ocr_client.process(file_path)
            
            # Step B: Logic Parsing
            # Validates that format matches expected invoice type
            # and extracts structured data.
            # Raises InvalidDocumentFormatError if the document is not a match.
            structured_data = parser.parse(raw_text)
            
            # Step C: Save data
            saver.save(structured_data, file_path)

        except InvalidDocumentFormatError:
            # Expected behavior: We want to skip non-target documents without crashing.
            print(f"SKIPPING: '{file_path}' - Does not match expected Invoice format.")
            
        except Exception as e:
            # Unexpected behavior: Log the error but continue to the next file (fault tolerance).
            print(f"ERROR: Failed to process '{file_path}': {e}")

if __name__ == "__main__":
    main()