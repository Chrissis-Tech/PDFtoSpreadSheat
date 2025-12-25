"""
Parsers Package
===============

Parsers for different PDF document types.
"""

from typing import Any, Dict, Optional

from .base_parser import BaseParser
from .invoice_parser import InvoiceParser
from .report_parser import ReportParser
from .financial_report_parser import FinancialReportParser


# Available parsers registry
PARSERS = {
    "invoice": InvoiceParser,
    "report": ReportParser,
    "financial_report": FinancialReportParser,
}


def get_parser(parser_type: str, config: Optional[Dict[str, Any]] = None) -> BaseParser:
    """
    Get an instance of the specified parser.
    
    Args:
        parser_type: Parser type (invoice, report, financial_report).
        config: Parser configuration.
        
    Returns:
        Parser instance.
        
    Raises:
        ValueError: If parser type doesn't exist.
    """
    if parser_type not in PARSERS:
        raise ValueError(f"Unknown parser: {parser_type}. Available: {list(PARSERS.keys())}")
    
    parser_class = PARSERS[parser_type]
    return parser_class(config or {})


def detect_parser_type(extracted_data: Dict[str, Any], config: Dict[str, Any]) -> str:
    """
    Automatically detect the appropriate parser type.
    
    Args:
        extracted_data: Extracted data from PDF.
        config: Global configuration.
        
    Returns:
        Detected parser name.
    """
    text = extracted_data.get("text", "").lower()
    tables = extracted_data.get("tables", [])
    
    # Check for financial report keywords first
    financial_keywords = [
        "estados financieros", "financial statements", 
        "balance general", "balance sheet",
        "estado de resultados", "income statement",
        "patrimonio", "stockholders equity",
        "activo", "pasivo", "assets", "liabilities"
    ]
    financial_matches = sum(1 for kw in financial_keywords if kw in text)
    if financial_matches >= 3:
        return "financial_report"
    
    parsers_config = config.get("parsers", {})
    
    # Check keywords for each parser
    for parser_name, parser_cfg in parsers_config.items():
        if not parser_cfg.get("enabled", True):
            continue
        
        if not parser_cfg.get("auto_detect", True):
            continue
        
        keywords = parser_cfg.get("keywords", [])
        
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in text)
        
        # If enough matches, use this parser
        if matches >= 2:
            return parser_name
    
    # If there are tables, use report parser
    if tables:
        return "report"
    
    # Default to invoice
    return "invoice"


__all__ = [
    "BaseParser",
    "InvoiceParser",
    "ReportParser",
    "FinancialReportParser",
    "get_parser",
    "detect_parser_type",
    "PARSERS",
]

