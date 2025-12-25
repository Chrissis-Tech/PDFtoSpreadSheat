"""
Financial Report Parser
=======================

Parser for financial statements and annual reports.
Optimized for documents like PEMEX financial statements.
"""

import re
from typing import Any, Dict, List, Optional

from loguru import logger

from .base_parser import BaseParser


class FinancialReportParser(BaseParser):
    """
    Parser for financial reports and statements.
    
    Extracts:
    - Balance sheet items (assets, liabilities, equity)
    - Income statement items
    - Cash flow items
    - Segment information
    - Notes and disclosures
    """
    
    PARSER_NAME = "financial_report"
    
    # Patterns for financial statement headers
    PATTERNS = {
        "report_title": r"(?:estados?\s+financieros?|financial\s+statements?|annual\s+report)",
        "company_name": r"^([A-Z][A-Za-z\s,\.]+(?:S\.A\.|Inc\.|Corp\.|LLC)?)",
        "report_date": r"(?:al|as\s+of|at)\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
        "currency": r"(?:cifras\s+(?:expresadas\s+)?en|amounts?\s+in)\s+(miles\s+de\s+pesos|millones|thousands|millions)",
        "fiscal_year": r"(?:ejercicio|year|periodo)\s*(?:terminado|ended)?\s*(?:el|the)?\s*\d{4}",
    }
    
    # Keywords to identify table types
    TABLE_KEYWORDS = {
        "balance_sheet": [
            "activo", "pasivo", "patrimonio", "capital",
            "assets", "liabilities", "equity", "stockholders"
        ],
        "income_statement": [
            "ingresos", "gastos", "utilidad", "perdida", "rendimiento",
            "revenue", "expenses", "profit", "loss", "income", "earnings"
        ],
        "cash_flow": [
            "flujo de efectivo", "flujos de efectivo", "operacion", "inversion", "financiamiento",
            "cash flow", "operating", "investing", "financing"
        ],
        "segment": [
            "segmento", "exploracion", "produccion", "refinacion", "logistica",
            "segment", "exploration", "production", "refining"
        ]
    }
    
    # Financial line item patterns
    LINE_ITEM_PATTERNS = {
        "amount": r"[\$\s]*([\d,\.]+)\s*$",
        "negative": r"\(([\d,\.]+)\)",
        "percentage": r"([\d\.]+)\s*%",
    }
    
    REQUIRED_FIELDS = []
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.extract_notes = config.get("extract_notes", False) if config else False
        self.max_pages = config.get("max_pages", 100) if config else 100
    
    def parse(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse financial report data.
        
        Args:
            extracted_data: Extracted data from PDF.
            
        Returns:
            List of dictionaries with financial data.
        """
        text = extracted_data.get("text", "")
        tables = extracted_data.get("tables", [])
        
        all_records = []
        
        # Extract metadata from text
        metadata = self._extract_metadata(text)
        
        # Process tables - main source of financial data
        if tables:
            for table_idx, table in enumerate(tables):
                table_records = self._process_financial_table(table, table_idx, metadata)
                all_records.extend(table_records)
        
        logger.debug(f"Financial report parsed: {len(all_records)} records from {len(tables)} tables")
        
        return all_records
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract report metadata from text."""
        metadata = {}
        
        # Company name (usually at the beginning)
        company_match = re.search(self.PATTERNS["company_name"], text, re.MULTILINE)
        if company_match:
            metadata["company"] = company_match.group(1).strip()
        
        # Report date
        date_match = re.search(self.PATTERNS["report_date"], text, re.IGNORECASE)
        if date_match:
            metadata["report_date"] = date_match.group(1).strip()
        
        # Currency/units
        currency_match = re.search(self.PATTERNS["currency"], text, re.IGNORECASE)
        if currency_match:
            metadata["currency_unit"] = currency_match.group(1).strip()
        
        return metadata
    
    def _process_financial_table(
        self, 
        table: List[List[Any]], 
        table_idx: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process a single financial table."""
        records = []
        
        if not table or len(table) < 2:
            return records
        
        # Detect table type based on content
        table_type = self._detect_table_type(table)
        
        # Find header row
        header_idx = self._find_header_row(table)
        
        # Get column headers
        if header_idx is not None and header_idx < len(table):
            headers = self._clean_headers(table[header_idx])
        else:
            headers = [f"col_{i}" for i in range(len(table[0]) if table[0] else 0)]
            header_idx = -1
        
        # Process data rows
        for row_idx, row in enumerate(table[header_idx + 1:], start=header_idx + 2):
            if not row or not any(cell for cell in row if cell):
                continue
            
            record = self._process_row(row, headers, table_type, metadata)
            if record:
                record["_table_index"] = table_idx + 1
                record["_row_index"] = row_idx
                record["_table_type"] = table_type
                records.append(record)
        
        return records
    
    def _detect_table_type(self, table: List[List[Any]]) -> str:
        """Detect the type of financial table based on content."""
        # Combine first few rows to text for analysis
        sample_text = ""
        for row in table[:5]:
            if row:
                sample_text += " ".join(str(c).lower() for c in row if c) + " "
        
        # Check each table type
        for table_type, keywords in self.TABLE_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in sample_text)
            if matches >= 2:
                return table_type
        
        return "general"
    
    def _find_header_row(self, table: List[List[Any]]) -> Optional[int]:
        """Find the header row in a financial table."""
        for i, row in enumerate(table[:5]):
            if not row:
                continue
            
            # Financial tables often have year headers like "2024", "2023"
            year_count = sum(
                1 for cell in row 
                if cell and re.search(r'\b20\d{2}\b', str(cell))
            )
            
            if year_count >= 2:
                return i
            
            # Or text headers with keywords
            text_cells = sum(
                1 for cell in row 
                if cell and not re.match(r'^[\d,\.\-\(\)\$\s]+$', str(cell).strip())
            )
            
            if text_cells >= len(row) * 0.5:
                return i
        
        return 0
    
    def _clean_headers(self, header_row: List[Any]) -> List[str]:
        """Clean and normalize header row."""
        headers = []
        seen = set()
        
        for i, cell in enumerate(header_row):
            if cell:
                # Clean the header
                h = str(cell).strip()
                h = re.sub(r'\s+', ' ', h)
                h = h[:50]  # Limit length
                
                # Handle duplicates
                base_h = h
                counter = 1
                while h.lower() in seen:
                    h = f"{base_h}_{counter}"
                    counter += 1
                
                seen.add(h.lower())
                headers.append(h)
            else:
                headers.append(f"col_{i}")
        
        return headers
    
    def _process_row(
        self, 
        row: List[Any], 
        headers: List[str],
        table_type: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process a single data row."""
        if not row:
            return None
        
        record = {}
        has_data = False
        
        # First column is usually the line item description
        if row[0]:
            line_item = str(row[0]).strip()
            # Skip empty or purely numeric first columns
            if line_item and not re.match(r'^[\d,\.\-\(\)\$\s]+$', line_item):
                record["line_item"] = line_item
                has_data = True
        
        # Process remaining columns as values
        for i, cell in enumerate(row[1:], start=1):
            if i < len(headers):
                header = headers[i]
            else:
                header = f"col_{i}"
            
            if cell:
                value = self._parse_financial_value(str(cell))
                if value is not None:
                    record[header] = value
                    has_data = True
                elif str(cell).strip():
                    record[header] = str(cell).strip()
                    has_data = True
        
        # Add metadata
        if has_data:
            record["company"] = metadata.get("company", "")
            record["currency_unit"] = metadata.get("currency_unit", "")
        
        return record if has_data else None
    
    def _parse_financial_value(self, value_str: str) -> Optional[float]:
        """Parse a financial value string to float."""
        if not value_str:
            return None
        
        value_str = value_str.strip()
        
        # Check for negative in parentheses: (1,234.56)
        negative = False
        paren_match = re.match(r'^\(([\d,\.]+)\)$', value_str)
        if paren_match:
            value_str = paren_match.group(1)
            negative = True
        
        # Remove currency symbols and spaces
        value_str = re.sub(r'[\$\s]', '', value_str)
        
        # Handle different number formats
        # Remove thousand separators and normalize decimal
        if ',' in value_str and '.' in value_str:
            # Determine which is decimal separator
            if value_str.rfind(',') > value_str.rfind('.'):
                # European: 1.234,56
                value_str = value_str.replace('.', '').replace(',', '.')
            else:
                # American: 1,234.56
                value_str = value_str.replace(',', '')
        elif ',' in value_str:
            # Could be thousand separator or decimal
            if re.search(r',\d{3}(?:,|$)', value_str):
                # Thousand separator
                value_str = value_str.replace(',', '')
            else:
                # Decimal separator
                value_str = value_str.replace(',', '.')
        
        try:
            result = float(value_str)
            return -result if negative else result
        except ValueError:
            return None
