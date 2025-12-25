"""
Base Parser
===========

Clase base abstracta para todos los parsers de documentos.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from loguru import logger


class BaseParser(ABC):
    """
    Clase base para parsers de documentos PDF.
    
    Todos los parsers especificos deben heredar de esta clase
    e implementar el metodo parse().
    """
    
    # Nombre del parser (sobreescribir en subclases)
    PARSER_NAME = "base"
    
    # Patrones de extraccion (sobreescribir en subclases)
    PATTERNS: Dict[str, str] = {}
    
    # Campos obligatorios (sobreescribir en subclases)
    REQUIRED_FIELDS: List[str] = []
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el parser.
        
        Args:
            config: Configuracion especifica del parser.
        """
        self.config = config or {}
        self.validation_rules = self._build_validation_rules()
    
    @abstractmethod
    def parse(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsea los datos extraidos y retorna registros estructurados.
        
        Args:
            extracted_data: Diccionario con:
                - text: Texto extraido del PDF
                - tables: Lista de tablas extraidas
                - metadata: Metadatos del documento
                
        Returns:
            Lista de diccionarios con los datos parseados.
        """
        pass
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Retorna las reglas de validacion para este parser.
        
        Returns:
            Diccionario con reglas por campo.
        """
        return self.validation_rules
    
    def _build_validation_rules(self) -> Dict[str, Any]:
        """
        Construye las reglas de validacion desde la configuracion.
        
        Returns:
            Diccionario con reglas de validacion.
        """
        rules = {}
        validation_config = self.config.get("validation", {})
        
        for field, field_rules in validation_config.items():
            if isinstance(field_rules, dict):
                rules[field] = field_rules
        
        # Agregar campos obligatorios
        for field in self.REQUIRED_FIELDS:
            if field not in rules:
                rules[field] = {}
            rules[field]["required"] = True
        
        return rules
    
    def extract_pattern(
        self,
        text: str,
        pattern: str,
        group: int = 0,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract a value using a regex pattern.
        
        Args:
            text: Text to search.
            pattern: Regex pattern with capture groups.
            group: Specific group to extract (0 = first non-empty group).
            default: Default value if no match.
            
        Returns:
            Extracted value or default.
        """
        try:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                # If group specified, use that group
                if group > 0:
                    return match.group(group).strip()
                # Otherwise, find first non-empty group
                for g in match.groups():
                    if g and g.strip():
                        return g.strip()
        except (re.error, IndexError) as e:
            logger.debug(f"Error extracting pattern '{pattern}': {e}")
        
        return default
    
    def extract_all_patterns(
        self,
        text: str,
        pattern: str,
        group: int = 1
    ) -> List[str]:
        """
        Extrae todos los valores que coinciden con un patron.
        
        Args:
            text: Texto donde buscar.
            pattern: Patron regex con grupos de captura.
            group: Numero de grupo a extraer.
            
        Returns:
            Lista de valores encontrados.
        """
        try:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                if isinstance(matches[0], tuple):
                    return [m[group - 1].strip() for m in matches]
                return [m.strip() for m in matches]
        except re.error as e:
            logger.debug(f"Error extrayendo patron '{pattern}': {e}")
        
        return []
    
    def extract_table_data(
        self,
        tables: List[List[List[str]]],
        header_row: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Convierte tablas extraidas a lista de diccionarios.
        
        Args:
            tables: Lista de tablas (cada tabla es lista de filas).
            header_row: Indice de la fila que contiene headers.
            
        Returns:
            Lista de diccionarios con datos de las tablas.
        """
        all_records = []
        
        for table in tables:
            if not table or len(table) <= header_row:
                continue
            
            # Obtener headers
            headers = table[header_row]
            if not headers:
                continue
            
            # Limpiar headers
            headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(headers)]
            
            # Procesar filas de datos
            for row in table[header_row + 1:]:
                if not row or not any(row):
                    continue
                
                record = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        header = headers[i]
                        record[header] = value
                
                if record:
                    all_records.append(record)
        
        return all_records
    
    def clean_text(self, text: str) -> str:
        """
        Limpia texto de caracteres no deseados.
        
        Args:
            text: Texto a limpiar.
            
        Returns:
            Texto limpio.
        """
        if not text:
            return ""
        
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def split_into_sections(
        self,
        text: str,
        section_patterns: List[str]
    ) -> Dict[str, str]:
        """
        Divide el texto en secciones usando patrones.
        
        Args:
            text: Texto completo.
            section_patterns: Lista de patrones que marcan inicio de seccion.
            
        Returns:
            Diccionario con nombre de seccion y contenido.
        """
        sections = {}
        combined_pattern = "|".join(f"({p})" for p in section_patterns)
        
        # Encontrar todas las coincidencias
        matches = list(re.finditer(combined_pattern, text, re.IGNORECASE))
        
        for i, match in enumerate(matches):
            section_name = match.group().strip().lower()
            start = match.end()
            
            # El fin es el inicio de la siguiente seccion o el final del texto
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)
            
            sections[section_name] = text[start:end].strip()
        
        return sections
