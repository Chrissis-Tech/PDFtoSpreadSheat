"""
Tests for CSV Exporter
======================

Pruebas unitarias para el exportador CSV.
"""

import csv
import pytest
from pathlib import Path
from src.exporters.csv_exporter import CSVExporter


class TestCSVExporter:
    """Pruebas para CSVExporter."""
    
    @pytest.fixture
    def exporter(self):
        """Crea una instancia del exportador."""
        return CSVExporter()
    
    @pytest.fixture
    def sample_data(self):
        """Datos de ejemplo para exportar."""
        return [
            {"nombre": "Juan", "edad": 30, "ciudad": "Madrid"},
            {"nombre": "Maria", "edad": 25, "ciudad": "Barcelona"},
            {"nombre": "Pedro", "edad": 35, "ciudad": "Valencia"}
        ]
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Directorio temporal para pruebas."""
        return tmp_path
    
    def test_export_basic(self, exporter, sample_data, temp_dir):
        """Prueba exportacion basica a CSV."""
        output_file = exporter.export(sample_data, temp_dir, "test_output")
        
        assert output_file.exists()
        assert output_file.suffix == ".csv"
        
        # Verificar contenido
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0]["nombre"] == "Juan"
    
    def test_export_empty_data(self, exporter, temp_dir):
        """Prueba exportacion con datos vacios."""
        output_file = exporter.export([], temp_dir, "empty_test")
        
        # Debe crear el archivo aunque este vacio
        assert output_file.name == "empty_test.csv"
    
    def test_export_with_custom_delimiter(self, temp_dir):
        """Prueba exportacion con delimitador personalizado."""
        exporter = CSVExporter({"delimiter": ";"})
        data = [{"col1": "val1", "col2": "val2"}]
        
        output_file = exporter.export(data, temp_dir, "semicolon_test")
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert ";" in content
    
    def test_export_with_none_values(self, exporter, temp_dir):
        """Prueba exportacion con valores None."""
        data = [{"col1": "valor", "col2": None, "col3": "otro"}]
        
        output_file = exporter.export(data, temp_dir, "none_test")
        
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        
        assert row["col2"] == ""
    
    def test_export_filters_internal_fields(self, exporter, temp_dir):
        """Prueba que los campos internos (_) se filtran."""
        data = [
            {"nombre": "Test", "_source_file": "archivo.pdf", "_internal": "data"}
        ]
        
        output_file = exporter.export(data, temp_dir, "internal_test")
        
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        
        assert "_source_file" not in row
        assert "_internal" not in row
        assert "nombre" in row
    
    def test_export_with_special_characters(self, exporter, temp_dir):
        """Prueba exportacion con caracteres especiales."""
        data = [{"texto": "Linea con, coma y \"comillas\""}]
        
        output_file = exporter.export(data, temp_dir, "special_test")
        
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        
        assert "coma" in row["texto"]
        assert "comillas" in row["texto"]
    
    def test_get_all_headers(self, exporter):
        """Prueba obtencion de todos los headers."""
        data = [
            {"col1": "a", "col2": "b"},
            {"col1": "c", "col3": "d"},  # col3 solo en segunda fila
        ]
        
        headers = exporter._get_all_headers(data)
        
        assert "col1" in headers
        assert "col2" in headers
        assert "col3" in headers
    
    def test_clean_row_datetime(self, exporter):
        """Prueba limpieza de fila con datetime."""
        from datetime import datetime
        
        row = {"fecha": datetime(2024, 3, 15, 10, 30)}
        headers = ["fecha"]
        
        clean = exporter._clean_row(row, headers)
        
        assert "2024-03-15" in clean["fecha"]
    
    def test_clean_row_boolean(self, exporter):
        """Prueba limpieza de fila con booleanos."""
        row = {"activo": True, "eliminado": False}
        headers = ["activo", "eliminado"]
        
        clean = exporter._clean_row(row, headers)
        
        assert clean["activo"] == "true"
        assert clean["eliminado"] == "false"
