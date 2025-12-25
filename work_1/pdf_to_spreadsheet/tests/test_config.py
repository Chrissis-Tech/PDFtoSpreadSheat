"""
Tests for Configuration Loader
==============================

Pruebas unitarias para el cargador de configuracion.
"""

import pytest
import yaml
from pathlib import Path
from src.config import load_config, get_parser_config, is_parser_enabled


class TestConfigLoader:
    """Pruebas para el cargador de configuracion."""
    
    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Crea un archivo de configuracion temporal."""
        config_content = """
paths:
  input: "./custom_input"
  output: "./custom_output"

output:
  default_format: "json"
  csv:
    delimiter: ";"

parsers:
  invoice:
    enabled: true
  report:
    enabled: false

validation:
  enabled: true
  on_error: "fail"
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)
        return config_file
    
    @pytest.fixture
    def minimal_config_file(self, tmp_path):
        """Crea un archivo de configuracion minimo."""
        config_file = tmp_path / "minimal_config.yaml"
        config_file.write_text("# Configuracion minima\n")
        return config_file
    
    def test_load_config_basic(self, temp_config_file):
        """Prueba carga basica de configuracion."""
        config = load_config(str(temp_config_file))
        
        assert config["paths"]["input"] == "./custom_input"
        assert config["paths"]["output"] == "./custom_output"
        assert config["output"]["default_format"] == "json"
    
    def test_load_config_with_defaults(self, minimal_config_file):
        """Prueba que se aplican valores por defecto."""
        config = load_config(str(minimal_config_file))
        
        # Verificar valores por defecto
        assert "paths" in config
        assert config["paths"]["input"] == "./input"
        assert config["paths"]["output"] == "./output"
        assert config["output"]["default_format"] == "csv"
    
    def test_load_config_file_not_found(self):
        """Prueba error cuando el archivo no existe."""
        with pytest.raises(FileNotFoundError):
            load_config("archivo_inexistente.yaml")
    
    def test_get_parser_config(self, temp_config_file):
        """Prueba obtencion de configuracion de parser."""
        config = load_config(str(temp_config_file))
        
        invoice_config = get_parser_config(config, "invoice")
        
        assert invoice_config["enabled"] == True
    
    def test_get_parser_config_nonexistent(self, temp_config_file):
        """Prueba obtencion de configuracion de parser inexistente."""
        config = load_config(str(temp_config_file))
        
        result = get_parser_config(config, "parser_inexistente")
        
        assert result == {}
    
    def test_is_parser_enabled_true(self, temp_config_file):
        """Prueba verificacion de parser habilitado."""
        config = load_config(str(temp_config_file))
        
        assert is_parser_enabled(config, "invoice") == True
    
    def test_is_parser_enabled_false(self, temp_config_file):
        """Prueba verificacion de parser deshabilitado."""
        config = load_config(str(temp_config_file))
        
        assert is_parser_enabled(config, "report") == False
    
    def test_is_parser_enabled_default(self, temp_config_file):
        """Prueba que parsers no configurados estan habilitados por defecto."""
        config = load_config(str(temp_config_file))
        
        # Parser no definido en config
        assert is_parser_enabled(config, "unknown_parser") == True


class TestConfigValidation:
    """Pruebas para validacion de configuracion."""
    
    @pytest.fixture
    def empty_config_file(self, tmp_path):
        """Crea un archivo de configuracion vacio."""
        config_file = tmp_path / "empty_config.yaml"
        config_file.write_text("")
        return config_file
    
    def test_validate_empty_config(self, empty_config_file):
        """Prueba que configuracion vacia se completa con defaults."""
        config = load_config(str(empty_config_file))
        
        # Debe tener todas las secciones con valores por defecto
        assert "paths" in config
        assert "output" in config
        assert "extraction" in config
        assert "normalization" in config
        assert "validation" in config
        assert "logging" in config
    
    def test_nested_defaults(self, empty_config_file):
        """Prueba que los valores anidados tienen defaults."""
        config = load_config(str(empty_config_file))
        
        assert config["output"]["csv"]["delimiter"] == ","
        assert config["output"]["csv"]["encoding"] == "utf-8"
        assert config["normalization"]["dates"]["output_format"] == "%Y-%m-%d"
