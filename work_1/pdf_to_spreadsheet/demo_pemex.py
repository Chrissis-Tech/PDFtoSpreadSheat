"""
Demo: PEMEX Financial Report Extraction
========================================

This script demonstrates the PDF to Spreadsheet tool
extracting real financial data from PEMEX's consolidated
financial statements (170 pages).
"""

import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, '.')

from src.config import load_config
from src.pipeline import Pipeline


def main():
    print()
    print("=" * 60)
    print("   PDF TO SPREADSHEET - PEMEX FINANCIAL REPORT DEMO")
    print("=" * 60)
    print()
    
    pdf_file = "input/pemex_estados_financieros_2024.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"ERROR: PDF not found at {pdf_file}")
        return
    
    file_size = os.path.getsize(pdf_file) / (1024 * 1024)
    print(f"Input PDF: {pdf_file}")
    print(f"File size: {file_size:.2f} MB")
    print()
    
    # Load configuration
    config = load_config("config.yaml")
    
    # Create pipeline
    pipeline = Pipeline(
        config=config,
        output_format="csv",
        parser_type="financial_report",
        dry_run=False
    )
    
    print("Processing PDF (170 pages)...")
    print("-" * 60)
    
    start_time = datetime.now()
    
    results = pipeline.process_file(pdf_file, "output")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("                    RESULTS")
    print("=" * 60)
    print(f"  Total rows extracted:  {results.get('total_rows', 0):,}")
    print(f"  Processing time:       {elapsed:.1f} seconds")
    print(f"  Errors:                {results.get('errors', 0)}")
    print(f"  Warnings:              {results.get('warnings', 0)}")
    print("=" * 60)
    
    output_file = results.get('output_file')
    if output_file and os.path.exists(output_file):
        output_size = os.path.getsize(output_file) / 1024
        print(f"\nOutput CSV: {output_file}")
        print(f"Output size: {output_size:.1f} KB")
        
        # Analyze the data
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Count tables by type
        table_types = {}
        for row in rows:
            tt = row.get('_table_type', 'unknown')
            table_types[tt] = table_types.get(tt, 0) + 1
        
        print(f"\nData by table type:")
        for tt, count in sorted(table_types.items(), key=lambda x: -x[1]):
            print(f"  - {tt}: {count} rows")
        
        # Show sample line items
        line_items = [r.get('line_item', '') for r in rows if r.get('line_item')]
        unique_items = list(set(line_items))[:20]
        
        print(f"\nSample extracted line items ({len(line_items)} total):")
        for item in unique_items[:15]:
            if item and len(item) > 5:
                print(f"  - {item[:70]}")


if __name__ == "__main__":
    main()
