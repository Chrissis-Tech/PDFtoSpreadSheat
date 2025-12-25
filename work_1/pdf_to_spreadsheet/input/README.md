# Input Directory

Place your PDF files here for processing.

## Sample PDFs Included:

1. **invoice_example_001.pdf** - Standard commercial invoice
2. **invoice_example_002.pdf** - Invoice with multiple items
3. **sales_report_example.pdf** - Tabular sales report

## Usage:

```bash
python main.py --input input/ --output output/ --format csv
```

## Generating Sample PDFs:

If sample PDFs are not present, generate them with:

```bash
pip install reportlab
python generate_sample_pdfs.py
```
