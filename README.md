# Automated Invoice Data Extraction System

A Python-based solution for batch processing invoices, extracting structured data via OCR.


## Prerequisites 

* A Veryfi account (Client ID, Secret, Username, API Key)

## Usage

### Install dependencies

1.  Install dependencies: This project relies on the veryfi SDK.
    ```bash
    pip install veryfi
    ```

### Configuration 

1.  Create a file named `app_secrets.py` in the root directory.
2.  Add your Veryfi credentials:

    ```python
    # app_secrets.py
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    USERNAME = "your_username"
    API_KEY = "your_api_key"
    ```

3.  Create a `batch_files.txt` inside  main directory with the file listing the relative paths of the PDFs you want to process:

    ```text
    docs/invoice_001.pdf
    docs/invoice_002.pdf
    ...
    ```

### Run 

Run the main orchestrator script to process the files listed in `batch_files.txt`:

```bash
python main.py
```

Successful extractions will be saved as JSON files in the `extractedData/` directory.

## Testing 

The project includes a unit tests suite (`unit_tests.py`) that covers:

1.  **Full Data Extraction:** Verifies that parsing logic correctly converts OCR text to JSON.
2.  **Format Validation:** Ensures invalid documents are rejected.

To run the tests:

```bash
python unit_tests.py
```

## Project Structure

* `main.py`: Entry point for batch processing.
* `invoice_processor.py`: Core logic (API Client, Parser, Validation).
* `unit_tests.py`: Unit tests.
* `app_secrets.py`: Credentials.
* `batch_files.txt`: Input file list.
* `extractedData/`: Output folder for JSON files.
* `docs/`: Input folder for PDF files.
