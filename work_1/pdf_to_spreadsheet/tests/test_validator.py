"""
Tests for Data Validator
========================

Pruebas unitarias para el validador de datos.
"""

import pytest
from src.validator import DataValidator


class TestDataValidator:
    """Pruebas para DataValidator."""
    
    @pytest.fixture
    def validator(self):
        """Crea una instancia del validador."""
        return DataValidator()
    
    @pytest.fixture
    def validator_strict(self):
        """Crea un validador en modo estricto."""
        config = {
            "enabled": True,
            "on_error": "fail",
            "max_errors": 3
        }
        return DataValidator(config)
    
    @pytest.fixture
    def sample_rules(self):
        """Reglas de validacion de ejemplo."""
        return {
            "invoice_id": {
                "type": "string",
                "required": True
            },
            "total": {
                "type": "number",
                "required": True,
                "min": 0
            },
            "date": {
                "type": "date",
                "required": True
            }
        }
    
    def test_validate_valid_data(self, validator, sample_rules):
        """Prueba validacion de datos validos."""
        data = [{
            "invoice_id": "INV-001",
            "total": 1500.00,
            "date": "2024-03-15"
        }]
        
        validated, errors = validator.validate(data, sample_rules)
        
        assert len(validated) == 1
        assert len(errors) == 0
    
    def test_validate_missing_required_field(self, validator, sample_rules):
        """Prueba validacion con campo requerido faltante."""
        data = [{
            "total": 1500.00,
            "date": "2024-03-15"
        }]
        
        validated, errors = validator.validate(data, sample_rules)
        
        assert len(errors) > 0
        assert any("invoice_id" in e for e in errors)
    
    def test_validate_negative_total(self, validator, sample_rules):
        """Prueba validacion de total negativo."""
        data = [{
            "invoice_id": "INV-001",
            "total": -100.00,
            "date": "2024-03-15"
        }]
        
        validated, errors = validator.validate(data, sample_rules)
        
        assert len(errors) > 0
        assert any("menor" in e.lower() or "min" in e.lower() for e in errors)
    
    def test_validate_wrong_type(self, validator, sample_rules):
        """Prueba validacion de tipo incorrecto."""
        data = [{
            "invoice_id": "INV-001",
            "total": "no es numero",
            "date": "2024-03-15"
        }]
        
        validated, errors = validator.validate(data, sample_rules)
        
        assert len(errors) > 0
    
    def test_validate_disabled(self):
        """Prueba validador deshabilitado."""
        validator = DataValidator({"enabled": False})
        data = [{"campo": "valor"}]
        
        validated, errors = validator.validate(data, {})
        
        assert validated == data
        assert len(errors) == 0
    
    def test_validate_empty_data(self, validator):
        """Prueba validacion de datos vacios."""
        validated, errors = validator.validate([], {})
        
        assert validated == []
        assert len(errors) == 0
    
    def test_validate_multiple_rows(self, validator, sample_rules):
        """Prueba validacion de multiples filas."""
        data = [
            {"invoice_id": "INV-001", "total": 100.00, "date": "2024-03-15"},
            {"invoice_id": "INV-002", "total": 200.00, "date": "2024-03-16"},
            {"invoice_id": "", "total": 300.00, "date": "2024-03-17"}  # ID vacio
        ]
        
        validated, errors = validator.validate(data, sample_rules)
        
        # La tercera fila tiene error, pero con on_error="warn" se incluye
        assert len(validated) >= 2
    
    def test_global_rules_non_negative(self, validator):
        """Prueba regla global de totales no negativos."""
        validator.global_rules = {"non_negative_totals": True}
        
        data = [{"total": -50.00}]
        
        validated, errors = validator.validate(data, {})
        
        assert len(errors) > 0
        assert any("negativo" in e.lower() for e in errors)
    
    def test_validate_string_max_length(self, validator):
        """Prueba validacion de longitud maxima de string."""
        rules = {
            "nombre": {
                "type": "string",
                "max_length": 10
            }
        }
        
        data = [{"nombre": "Este nombre es demasiado largo"}]
        
        validated, errors = validator.validate(data, rules)
        
        assert len(errors) > 0
        assert any("largo" in e.lower() for e in errors)


class TestValidatorOnErrorModes:
    """Pruebas para los diferentes modos de manejo de errores."""
    
    def test_on_error_skip(self):
        """Prueba modo skip: omite filas con errores."""
        validator = DataValidator({"enabled": True, "on_error": "skip"})
        rules = {"campo": {"required": True}}
        
        data = [
            {"campo": "valor"},  # Valido
            {},  # Invalido - se omite
            {"campo": "otro"}  # Valido
        ]
        
        validated, errors = validator.validate(data, rules)
        
        assert len(validated) == 2
        assert len(errors) > 0
    
    def test_on_error_warn(self):
        """Prueba modo warn: incluye todas las filas pero reporta errores."""
        validator = DataValidator({"enabled": True, "on_error": "warn"})
        rules = {"campo": {"required": True}}
        
        data = [
            {"campo": "valor"},
            {},
            {"campo": "otro"}
        ]
        
        validated, errors = validator.validate(data, rules)
        
        assert len(validated) == 3
        assert len(errors) > 0
    
    def test_on_error_fail(self):
        """Prueba modo fail: lanza excepcion al exceder max_errors."""
        validator = DataValidator({
            "enabled": True,
            "on_error": "fail",
            "max_errors": 1
        })
        rules = {"campo": {"required": True}}
        
        data = [
            {},  # Error 1
            {},  # Error 2 - deberia fallar
        ]
        
        with pytest.raises(ValueError):
            validator.validate(data, rules)
