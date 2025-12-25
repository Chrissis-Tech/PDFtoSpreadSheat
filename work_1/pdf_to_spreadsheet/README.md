# PDF to Spreadsheet Automation

**Extract structured data from PDFs and export to CSV, JSON, or Google Sheets.**

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)

---

## What This Project Does

Automates data extraction from PDFs (invoices, reports, tables) and converts them to structured formats ready for analysis.

### Before / After

| Before | After |
|--------|-------|
| PDF with scattered data | Clean, validated CSV/JSON |
| Tedious manual extraction | Automation in seconds |
| Frequent human errors | Automatic data validation |

**Visual Example:**

```
INVOICE #12345                    ->    invoice_id,date,vendor,total
Date: 03/15/2024                        12345,2024-03-15,ACME Corp,1500.00
Vendor: ACME Corp                       12346,2024-03-20,TechSupply,2340.50
Total: $1,500.00
```

---

## Key Features

- **Template-based parsers**: Support for invoices, tabular reports, and financial statements
- **Smart extraction**: Direct text, structured tables, optional OCR
- **Data normalization**: Standardized dates, currencies, decimals
- **Robust validation**: Required fields, types, business rules
- **Multiple output formats**: CSV, JSON, Google Sheets
- **Professional CLI**: Complete command-line interface
- **Detailed logging**: Full tracking of each execution

---

## Real-World Example: PEMEX Financial Statements

This tool was tested with **PEMEX's 2024 Consolidated Financial Statements** (170 pages, 42 tables).

```bash
python main.py --input input/pemex_estados_financieros_2024.pdf \
               --output output/ \
               --format csv \
               --parser financial_report
```

**Results:**

| Metric | Value |
|--------|-------|
| Pages processed | 170 |
| Tables detected | 42 |
| Rows extracted | 3,250 |
| Financial line items | 427 |
| Processing time | ~3 minutes |
| Output size | 1.4 MB |

**Extracted data includes:**
- Balance sheet items (assets, liabilities, equity)
- Income statement line items
- Cash flow components
- Segment information (Exploration, Production, Refining, Logistics)
- Notes and disclosures

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/pdf-to-spreadsheet.git
cd pdf-to-spreadsheet

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Optional Dependencies

```bash
# For OCR (scanned PDFs)
pip install pytesseract
# Requires Tesseract installed on the system

# For Google Sheets
pip install google-auth google-auth-oauthlib gspread
```

---

## Web Dashboard & API

### Start the API Server

```bash
python api.py
```

Then open your browser to:
- **Dashboard**: http://localhost:8000/
- **API Docs**: http://localhost:8000/api/docs

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload PDF for processing |
| GET | `/api/jobs/{id}` | Get job status |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/download/{id}` | Download result file |
| GET | `/api/preview/{id}` | Preview extracted data |
| DELETE | `/api/jobs/{id}` | Delete job |

### Folder Watcher

Automatically process PDFs dropped into a folder:

```bash
python watcher.py --input ./watch --output ./output --format csv
```

### Docker

```bash
# Build and run
docker-compose up -d

# With folder watcher
docker-compose --profile watcher up -d
```

---

## Quick Start

### Command Line Interface (CLI)

```bash
# Process all PDFs in input/
python main.py --input input/ --output output/ --format csv

# JSON format
python main.py --input input/ --output output/ --format json

# Google Sheets (requires configuration)
python main.py --input input/ --output output/ --format gsheet

# Single file
python main.py --input input/invoice_001.pdf --output output/ --format csv

# With specific parser
python main.py --input input/ --output output/ --format csv --parser invoice

# Verbose mode
python main.py --input input/ --output output/ --format csv --verbose
```

### As Python Module

```python
from src.pipeline import Pipeline
from src.config import load_config

config = load_config("config.yaml")
pipeline = Pipeline(config)

# Process a single PDF
result = pipeline.process_file("input/invoice_001.pdf")

# Process entire directory
results = pipeline.process_directory("input/")
```

---

## Project Structure

```
pdf_to_spreadsheet/
|-- input/                    # Input PDFs (examples included)
|-- output/                   # Generated files (CSV, JSON)
|-- logs/                     # Execution logs
|-- src/
|   |-- parsers/              # Document type parsers
|   |   |-- base_parser.py
|   |   |-- invoice_parser.py
|   |   |-- report_parser.py
|   |-- extractors/           # Extraction engines
|   |   |-- text_extractor.py
|   |   |-- table_extractor.py
|   |   |-- ocr_extractor.py
|   |-- normalizer.py         # Data normalization
|   |-- validator.py          # Data validation
|   |-- exporters/            # Exporters
|   |   |-- csv_exporter.py
|   |   |-- json_exporter.py
|   |   |-- gsheet_exporter.py
|   |-- pipeline.py           # Main orchestrator
|   |-- config.py             # Configuration loader
|-- tests/                    # Unit tests
|-- .github/workflows/        # CI/CD
|-- config.yaml               # Main configuration
|-- requirements.txt          # Dependencies
|-- main.py                   # CLI entry point
```

---

## How to Add a New Template

### Step 1: Create the Parser

Create a new file in `src/parsers/`:

```python
# src/parsers/my_template_parser.py

from .base_parser import BaseParser

class MyTemplateParser(BaseParser):
    """Parser for MyTemplate document type."""
    
    PARSER_NAME = "my_template"
    
    # Extraction patterns (regex)
    PATTERNS = {
        "field1": r"Label1:\s*(.+)",
        "field2": r"Label2:\s*(\d+)",
    }
    
    # Required fields
    REQUIRED_FIELDS = ["field1", "field2"]
    
    def parse(self, extracted_data: dict) -> dict:
        """Process extracted data."""
        result = {}
        
        for field, pattern in self.PATTERNS.items():
            result[field] = self.extract_pattern(extracted_data["text"], pattern)
        
        return self.normalize(result)
```

### Step 2: Register the Parser

In `src/parsers/__init__.py`:

```python
from .my_template_parser import MyTemplateParser

PARSERS = {
    # ... other parsers
    "my_template": MyTemplateParser,
}
```

### Step 3: Configure Rules (Optional)

In `config.yaml`:

```yaml
parsers:
  my_template:
    enabled: true
    validation:
      field1:
        type: string
        required: true
      field2:
        type: number
        min: 0
```

### Step 4: Add Tests

In `tests/test_my_template_parser.py`:

```python
def test_my_template_parsing():
    parser = MyTemplateParser()
    result = parser.parse(sample_data)
    assert result["field1"] == "expected_value"
```

---

## Configuration

The `config.yaml` file controls system behavior:

```yaml
# Paths
paths:
  input: "./input"
  output: "./output"
  logs: "./logs"

# Default output format
output:
  default_format: "csv"
  csv:
    delimiter: ","
    encoding: "utf-8"

# Enabled parsers
parsers:
  invoice:
    enabled: true
  report:
    enabled: true

# Extraction
extraction:
  prefer_tables: true
  ocr_fallback: true
  ocr_language: "eng"
```

---

## Limitations

### What it DOES:
- Extracts data from PDFs with selectable text
- Processes structured tables (tested with 170+ page documents)
- Handles financial statements, invoices, and tabular reports
- Basic OCR for scanned PDFs (requires Tesseract)
- Validates and normalizes common data (dates, currencies, numbers)
- Exports to multiple formats

### What it DOES NOT:
- Process encrypted or password-protected PDFs
- Extract embedded images or charts
- Handle extremely complex or unstructured layouts
- Machine learning for automatic template detection
- Guarantee 100% accuracy on complex merged-cell tables

### Edge Cases:
- **Scanned PDFs**: Require Tesseract installed; variable accuracy
- **Complex tables**: Merged cells may not parse correctly
- **Languages**: Optimized for English and Spanish
- **Large PDFs**: 100+ pages work but processing takes longer (~3 min for 170 pages)

---

## Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Only parser tests
pytest tests/test_parsers.py -v
```

---

## Logs and Reports

Each execution generates:

1. **Detailed log**: `logs/run_YYYYMMDD_HHMMSS.log`
2. **Console summary**:

```
========================================
        EXECUTION SUMMARY
========================================
PDFs processed:      5
Rows extracted:    127
Errors:              1
Warnings:            3
Total time:       4.2s
========================================
Output file: output/result_20240315.csv
```

---

## Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/new-feature`
3. Commit: `git commit -m "Add new feature"`
4. Push: `git push origin feature/new-feature`
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Contact

- Issues: [GitHub Issues](https://github.com/your-username/pdf-to-spreadsheet/issues)
- Email: your-email@example.com
