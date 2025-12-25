"""
Pytest Configuration
====================

Configuracion y fixtures compartidos para tests.
"""

import sys
from pathlib import Path

import pytest

# Agregar el directorio raiz al path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sample_invoice_text():
    """Texto de ejemplo de una factura estandar."""
    return """
    FACTURA COMERCIAL
    
    Numero de Factura: FAC-2024-00123
    Fecha de Emision: 15/03/2024
    Fecha de Vencimiento: 15/04/2024
    
    EMISOR:
    Proveedor: Soluciones Tech S.A. de C.V.
    RFC: STS123456ABC
    Direccion: Av. Reforma 1234, Col. Centro, CDMX
    
    RECEPTOR:
    Cliente: Corporativo XYZ
    RFC: CXY987654DEF
    
    CONCEPTOS:
    Cantidad  Descripcion                    Precio Unit.    Total
    ----------------------------------------------------------------
    10        Licencia Software Anual        $500.00         $5,000.00
    5         Horas de Implementacion        $200.00         $1,000.00
    3         Modulos Adicionales            $800.00         $2,400.00
    
    ----------------------------------------------------------------
    Subtotal:                                                $8,400.00
    IVA (16%):                                               $1,344.00
    ----------------------------------------------------------------
    TOTAL A PAGAR:                                           $9,744.00
    
    Metodo de Pago: Transferencia Bancaria
    Cuenta: 1234567890
    """


@pytest.fixture
def sample_report_text():
    """Texto de ejemplo de un reporte tabular."""
    return """
    REPORTE DE VENTAS REGIONAL
    Periodo: Enero 2024
    Pagina 1 de 1
    
    ID      Vendedor            Region      Ventas      Comision    Fecha
    -----------------------------------------------------------------------
    V001    Juan Perez          Norte       $45,000     $4,500      05/01/2024
    V002    Maria Garcia        Sur         $38,000     $3,800      08/01/2024
    V003    Carlos Lopez        Centro      $52,000     $5,200      12/01/2024
    V004    Ana Martinez        Este        $41,000     $4,100      15/01/2024
    -----------------------------------------------------------------------
    TOTAL                                   $176,000    $17,600
    
    Notas: Comision calculada al 10% sobre ventas.
    """


@pytest.fixture
def sample_table_data():
    """Datos de tabla de ejemplo (como los retornaria pdfplumber)."""
    return [[
        ["ID", "Nombre", "Cantidad", "Precio", "Total"],
        ["001", "Producto A", "10", "100.00", "1000.00"],
        ["002", "Producto B", "5", "200.00", "1000.00"],
        ["003", "Producto C", "3", "150.00", "450.00"],
        [None, None, None, "Subtotal:", "2450.00"],
    ]]


@pytest.fixture
def sample_extracted_invoice(sample_invoice_text):
    """Datos extraidos de ejemplo para factura."""
    return {
        "text": sample_invoice_text,
        "tables": [],
        "metadata": {
            "file_name": "factura_test.pdf",
            "extraction_method": "text"
        }
    }


@pytest.fixture
def sample_extracted_report(sample_report_text):
    """Datos extraidos de ejemplo para reporte."""
    return {
        "text": sample_report_text,
        "tables": [],
        "metadata": {
            "file_name": "reporte_test.pdf",
            "extraction_method": "text"
        }
    }


@pytest.fixture
def temp_config(tmp_path):
    """Crea un archivo de configuracion temporal."""
    config_content = """
paths:
  input: "./input"
  output: "./output"
  logs: "./logs"

output:
  default_format: "csv"

parsers:
  invoice:
    enabled: true
  report:
    enabled: true

validation:
  enabled: true
  on_error: "warn"
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def mock_pdf_content():
    """
    Contenido mock para simular un PDF.
    
    En tests reales, usariamos un PDF real o mocks de pdfplumber.
    """
    return {
        "pages": 1,
        "text": "Contenido de prueba",
        "tables": []
    }
