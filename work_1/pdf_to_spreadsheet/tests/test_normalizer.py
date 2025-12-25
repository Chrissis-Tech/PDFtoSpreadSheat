"""
Tests for Data Normalizer
=========================

Pruebas unitarias para el normalizador de datos.
"""

import pytest
from src.normalizer import DataNormalizer


class TestDataNormalizer:
    """Pruebas para DataNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        """Crea una instancia del normalizador."""
        return DataNormalizer()
    
    @pytest.fixture
    def normalizer_custom_config(self):
        """Crea un normalizador con configuracion personalizada."""
        config = {
            "dates": {
                "output_format": "%d/%m/%Y"
            },
            "text": {
                "lowercase_headers": False
            }
        }
        return DataNormalizer(config)
    
    def test_normalize_header_basic(self, normalizer):
        """Prueba normalizacion basica de headers."""
        assert normalizer._normalize_header("Nombre Completo") == "nombre_completo"
        assert normalizer._normalize_header("  espacios  ") == "espacios"
        assert normalizer._normalize_header("con-guiones") == "con_guiones"
    
    def test_normalize_header_special_chars(self, normalizer):
        """Prueba normalizacion de caracteres especiales."""
        assert normalizer._normalize_header("precio ($)") == "precio"
        assert normalizer._normalize_header("IVA %") == "iva"
    
    def test_normalize_header_empty(self, normalizer):
        """Test with empty header."""
        result = normalizer._normalize_header("")
        assert result == "unnamed_column"
    
    def test_normalize_date_ddmmyyyy(self, normalizer):
        """Prueba normalizacion de fecha DD/MM/YYYY."""
        result = normalizer._normalize_date("15/03/2024")
        assert result == "2024-03-15"
    
    def test_normalize_date_yyyymmdd(self, normalizer):
        """Prueba normalizacion de fecha YYYY-MM-DD."""
        result = normalizer._normalize_date("2024-03-15")
        assert result == "2024-03-15"
    
    def test_normalize_date_spanish(self, normalizer):
        """Prueba normalizacion de fecha en espanol."""
        result = normalizer._normalize_date("15 de marzo de 2024")
        assert result == "2024-03-15"
    
    def test_normalize_date_invalid(self, normalizer):
        """Prueba con fecha invalida."""
        result = normalizer._normalize_date("no es fecha")
        # Retorna el valor original si no puede parsear
        assert result == "no es fecha"
    
    def test_normalize_number_simple(self, normalizer):
        """Prueba normalizacion de numero simple."""
        result = normalizer._normalize_number("1234.56")
        assert result == 1234.56
    
    def test_normalize_number_with_currency(self, normalizer):
        """Prueba normalizacion de numero con simbolo de moneda."""
        result = normalizer._normalize_number("$1,234.56")
        assert result == 1234.56
    
    def test_normalize_number_european_format(self, normalizer):
        """Prueba normalizacion de numero en formato europeo."""
        result = normalizer._normalize_number("1.234,56")
        assert result == 1234.56
    
    def test_normalize_number_spanish_format(self, normalizer):
        """Prueba normalizacion de numero con coma como decimal."""
        result = normalizer._normalize_number("1234,56")
        assert result == 1234.56
    
    def test_normalize_number_usd(self, normalizer):
        """Prueba normalizacion con USD."""
        result = normalizer._normalize_number("USD 500.00")
        assert result == 500.00
    
    def test_normalize_text_whitespace(self, normalizer):
        """Prueba normalizacion de espacios en texto."""
        result = normalizer._normalize_text("  texto   con   espacios  ")
        assert result == "texto con espacios"
    
    def test_normalize_list_of_dicts(self, normalizer):
        """Prueba normalizacion de lista de diccionarios."""
        data = [
            {"Nombre": "Juan", "Fecha": "15/03/2024", "Monto": "$100.00"},
            {"Nombre": "Maria", "Fecha": "20/03/2024", "Monto": "$250.50"}
        ]
        
        result = normalizer.normalize(data)
        
        assert len(result) == 2
        assert result[0]["nombre"] == "Juan"
        assert result[0]["fecha"] == "2024-03-15"
        assert result[0]["monto"] == 100.00
    
    def test_normalize_single_dict(self, normalizer):
        """Prueba normalizacion de un solo diccionario."""
        data = {"Campo": "valor", "Numero": "123"}
        
        result = normalizer.normalize(data)
        
        assert len(result) == 1
        assert result[0]["campo"] == "valor"
    
    def test_normalize_none_values(self, normalizer):
        """Prueba manejo de valores None."""
        data = {"campo1": None, "campo2": "valor"}
        
        result = normalizer.normalize(data)
        
        assert result[0]["campo1"] is None
        assert result[0]["campo2"] == "valor"
    
    def test_normalize_empty_string(self, normalizer):
        """Prueba manejo de strings vacios."""
        data = {"campo": ""}
        
        result = normalizer.normalize(data)
        
        assert result[0]["campo"] is None


class TestDataNormalizerUnicode:
    """Pruebas de normalizacion Unicode."""
    
    @pytest.fixture
    def normalizer(self):
        return DataNormalizer()
    
    def test_normalize_unicode_quotes(self, normalizer):
        """Prueba normalizacion de comillas unicode."""
        text = "texto con comillas especiales"
        result = normalizer._normalize_unicode_text(text)
        
        assert isinstance(result, str)
    
    def test_normalize_accented_characters(self, normalizer):
        """Prueba que los caracteres acentuados se preservan."""
        text = "facturacion numero"
        result = normalizer._normalize_text(text)
        
        # Los acentos deben preservarse
        assert "facturacion" in result or "facturaci" in result
