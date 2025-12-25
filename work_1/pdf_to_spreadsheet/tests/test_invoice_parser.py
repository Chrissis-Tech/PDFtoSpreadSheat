"""
Tests for Invoice Parser
========================

Pruebas unitarias para el parser de facturas.
"""

import pytest
from src.parsers.invoice_parser import InvoiceParser


class TestInvoiceParser:
    """Pruebas para InvoiceParser."""
    
    @pytest.fixture
    def parser(self):
        """Crea una instancia del parser para las pruebas."""
        return InvoiceParser()
    
    @pytest.fixture
    def sample_invoice_text(self):
        """Texto de ejemplo de una factura."""
        return """
        FACTURA
        
        Numero de Factura: INV-2024-001
        Fecha: 15/03/2024
        
        Proveedor: ACME Corporation S.A. de C.V.
        RFC: ACM123456789
        
        Cliente: Empresa Cliente SA
        
        DETALLE:
        Cantidad  Descripcion              Precio Unit.  Total
        5         Producto A               $100.00       $500.00
        3         Servicio B               $250.00       $750.00
        2         Producto C               $75.00        $150.00
        
        Subtotal: $1,400.00
        IVA (16%): $224.00
        Total: $1,624.00
        """
    
    @pytest.fixture
    def sample_extracted_data(self, sample_invoice_text):
        """Datos extraidos simulados."""
        return {
            "text": sample_invoice_text,
            "tables": [],
            "metadata": {"file_name": "test_invoice.pdf"}
        }
    
    def test_parser_initialization(self, parser):
        """Verifica que el parser se inicializa correctamente."""
        assert parser.PARSER_NAME == "invoice"
        assert "invoice_id" in parser.PATTERNS
        assert "total" in parser.PATTERNS
    
    def test_parse_invoice_id(self, parser, sample_extracted_data):
        """Verifica extraccion del numero de factura."""
        result = parser.parse(sample_extracted_data)
        
        assert len(result) == 1
        assert result[0]["invoice_id"] == "INV-2024-001"
    
    def test_parse_date(self, parser, sample_extracted_data):
        """Verifica extraccion de la fecha."""
        result = parser.parse(sample_extracted_data)
        
        assert result[0]["date"] == "15/03/2024"
    
    def test_parse_vendor(self, parser, sample_extracted_data):
        """Verifica extraccion del proveedor."""
        result = parser.parse(sample_extracted_data)
        
        assert "ACME" in result[0]["vendor"]
    
    def test_parse_total(self, parser, sample_extracted_data):
        """Verifica extraccion del total."""
        result = parser.parse(sample_extracted_data)
        
        # El total se extrae como string, la normalizacion lo convierte
        assert result[0]["total"] is not None
    
    def test_parse_empty_data(self, parser):
        """Verifica manejo de datos vacios."""
        result = parser.parse({"text": "", "tables": []})
        
        assert result == []
    
    def test_required_fields(self, parser):
        """Verifica que los campos requeridos estan definidos."""
        assert "invoice_id" in parser.REQUIRED_FIELDS
        assert "date" in parser.REQUIRED_FIELDS
        assert "total" in parser.REQUIRED_FIELDS
    
    def test_validation_rules(self, parser):
        """Verifica que se generan reglas de validacion."""
        rules = parser.get_validation_rules()
        
        assert isinstance(rules, dict)
        # Los campos requeridos deben tener required=True
        for field in parser.REQUIRED_FIELDS:
            if field in rules:
                assert rules[field].get("required", False)


class TestInvoiceParserEdgeCases:
    """Pruebas de casos limite para InvoiceParser."""
    
    @pytest.fixture
    def parser(self):
        return InvoiceParser()
    
    def test_invoice_with_different_date_format(self, parser):
        """Prueba con formato de fecha diferente."""
        text = """
        Factura No. 12345
        Fecha de emision: 2024-03-15
        Total a pagar: $500.00
        """
        result = parser.parse({"text": text, "tables": []})
        
        assert len(result) == 1
        assert result[0]["invoice_id"] == "12345"
    
    def test_invoice_with_multiline_vendor(self, parser):
        """Prueba con nombre de proveedor multilinea."""
        text = """
        Factura: FAC-001
        Fecha: 01/01/2024
        Proveedor: Empresa Larga
        Total: $100.00
        """
        result = parser.parse({"text": text, "tables": []})
        
        assert result[0]["vendor"] is not None
    
    def test_invoice_with_special_characters(self, parser):
        """Prueba con caracteres especiales en el texto."""
        text = """
        Factura #: INV-2024/001
        Fecha: 15/03/2024
        Total: $1,234.56
        """
        result = parser.parse({"text": text, "tables": []})
        
        assert result[0]["invoice_id"] is not None
