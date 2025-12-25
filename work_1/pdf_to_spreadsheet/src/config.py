"""
Configuration Loader
====================

Carga y valida la configuracion desde archivos YAML.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Carga la configuracion desde un archivo YAML.
    
    Args:
        config_path: Ruta al archivo de configuracion.
        
    Returns:
        Diccionario con la configuracion.
        
    Raises:
        FileNotFoundError: Si el archivo no existe.
        yaml.YAMLError: Si el archivo tiene errores de sintaxis.
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Archivo de configuracion no encontrado: {config_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Validar configuracion minima
    config = _validate_config(config)
    
    return config


def _validate_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Valida y completa la configuracion con valores por defecto.
    
    Args:
        config: Configuracion cargada del archivo.
        
    Returns:
        Configuracion validada y completada.
    """
    if config is None:
        config = {}
    
    # Valores por defecto para paths
    if "paths" not in config:
        config["paths"] = {}
    
    config["paths"].setdefault("input", "./input")
    config["paths"].setdefault("output", "./output")
    config["paths"].setdefault("logs", "./logs")
    
    # Valores por defecto para output
    if "output" not in config:
        config["output"] = {}
    
    config["output"].setdefault("default_format", "csv")
    
    if "csv" not in config["output"]:
        config["output"]["csv"] = {}
    config["output"]["csv"].setdefault("delimiter", ",")
    config["output"]["csv"].setdefault("encoding", "utf-8")
    
    # Valores por defecto para extraccion
    if "extraction" not in config:
        config["extraction"] = {}
    
    config["extraction"].setdefault("strategy", "auto")
    config["extraction"].setdefault("prefer_tables", True)
    config["extraction"].setdefault("ocr_fallback", True)
    config["extraction"].setdefault("ocr_language", "spa+eng")
    
    # Valores por defecto para parsers
    if "parsers" not in config:
        config["parsers"] = {
            "invoice": {"enabled": True},
            "report": {"enabled": True}
        }
    
    # Valores por defecto para normalizacion
    if "normalization" not in config:
        config["normalization"] = {}
    
    if "dates" not in config["normalization"]:
        config["normalization"]["dates"] = {}
    config["normalization"]["dates"].setdefault("output_format", "%Y-%m-%d")
    
    # Valores por defecto para validacion
    if "validation" not in config:
        config["validation"] = {}
    config["validation"].setdefault("enabled", True)
    config["validation"].setdefault("on_error", "warn")
    
    # Valores por defecto para logging
    if "logging" not in config:
        config["logging"] = {}
    config["logging"].setdefault("level", "INFO")
    config["logging"].setdefault("console", True)
    config["logging"].setdefault("file", True)
    
    return config


def get_parser_config(config: Dict[str, Any], parser_name: str) -> Dict[str, Any]:
    """
    Obtiene la configuracion especifica de un parser.
    
    Args:
        config: Configuracion global.
        parser_name: Nombre del parser.
        
    Returns:
        Configuracion del parser.
    """
    parsers_config = config.get("parsers", {})
    return parsers_config.get(parser_name, {})


def is_parser_enabled(config: Dict[str, Any], parser_name: str) -> bool:
    """
    Verifica si un parser esta habilitado.
    
    Args:
        config: Configuracion global.
        parser_name: Nombre del parser.
        
    Returns:
        True si el parser esta habilitado.
    """
    parser_config = get_parser_config(config, parser_name)
    return parser_config.get("enabled", True)
