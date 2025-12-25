"""
Data Normalizer
===============

Estandariza fechas, monedas, decimales y limpia datos.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from dateutil import parser as date_parser
from loguru import logger


class DataNormalizer:
    """
    Normaliza y limpia datos extraidos de PDFs.
    
    Funcionalidades:
    - Estandariza fechas a formato ISO
    - Normaliza numeros y monedas
    - Limpia texto (whitespace, unicode)
    - Corrige headers problematicos
    """
    
    # Meses en espanol para parsing
    SPANISH_MONTHS = {
        "enero": "January", "febrero": "February", "marzo": "March",
        "abril": "April", "mayo": "May", "junio": "June",
        "julio": "July", "agosto": "August", "septiembre": "September",
        "octubre": "October", "noviembre": "November", "diciembre": "December"
    }
    
    # Simbolos de moneda a eliminar
    CURRENCY_SYMBOLS = ["$", "USD", "MXN", "EUR", "COP", "ARS", "CLP"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el normalizador.
        
        Args:
            config: Configuracion de normalizacion.
        """
        self.config = config or {}
        
        # Configuracion de fechas
        date_config = self.config.get("dates", {})
        self.date_output_format = date_config.get("output_format", "%Y-%m-%d")
        self.date_input_formats = date_config.get("input_formats", [
            "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d",
            "%d de %B de %Y", "%B %d, %Y"
        ])
        
        # Configuracion de numeros
        num_config = self.config.get("numbers", {})
        self.decimal_sep = num_config.get("decimal_separator", ".")
        self.thousands_sep = num_config.get("thousands_separator", ",")
        
        # Configuracion de texto
        text_config = self.config.get("text", {})
        self.strip_whitespace = text_config.get("strip_whitespace", True)
        self.normalize_unicode = text_config.get("normalize_unicode", True)
        self.lowercase_headers = text_config.get("lowercase_headers", True)
    
    def normalize(self, data: Union[Dict, List[Dict]]) -> List[Dict[str, Any]]:
        """
        Normaliza los datos extraidos.
        
        Args:
            data: Datos a normalizar (diccionario o lista de diccionarios).
            
        Returns:
            Lista de diccionarios normalizados.
        """
        # Convertir a lista si es un solo diccionario
        if isinstance(data, dict):
            data = [data]
        
        normalized = []
        
        for row in data:
            normalized_row = {}
            
            for key, value in row.items():
                # Normalizar key (header)
                normalized_key = self._normalize_header(key)
                
                # Normalizar value
                normalized_value = self._normalize_value(value, normalized_key)
                
                normalized_row[normalized_key] = normalized_value
            
            normalized.append(normalized_row)
        
        return normalized
    
    def _normalize_header(self, header: str) -> str:
        """
        Normaliza el nombre de una columna/header.
        
        Args:
            header: Nombre original del header.
            
        Returns:
            Header normalizado.
        """
        if not isinstance(header, str):
            header = str(header)
        
        # Limpiar whitespace
        header = header.strip()
        
        # Normalizar unicode
        if self.normalize_unicode:
            header = self._normalize_unicode_text(header)
        
        # Replace spaces and special characters with underscores
        header = re.sub(r'[\s\-\.]+', '_', header)
        header = re.sub(r'[^\w_]', '', header)
        
        # Remove leading/trailing underscores
        header = header.strip('_')
        
        # Lowercase
        if self.lowercase_headers:
            header = header.lower()
        
        # Avoid empty headers
        if not header:
            header = "unnamed_column"
        
        return header
    
    def _normalize_value(self, value: Any, field_name: str = "") -> Any:
        """
        Normaliza un valor individual.
        
        Args:
            value: Valor a normalizar.
            field_name: Nombre del campo (para inferir tipo).
            
        Returns:
            Valor normalizado.
        """
        if value is None:
            return None
        
        if not isinstance(value, str):
            return value
        
        value = value.strip() if self.strip_whitespace else value
        
        if not value:
            return None
        
        # Detectar tipo basado en contenido o nombre de campo
        if self._looks_like_date(value, field_name):
            return self._normalize_date(value)
        
        if self._looks_like_number(value, field_name):
            return self._normalize_number(value)
        
        # Normalizar texto general
        return self._normalize_text(value)
    
    def _looks_like_date(self, value: str, field_name: str) -> bool:
        """Detecta si un valor parece ser una fecha."""
        date_keywords = ["fecha", "date", "dia", "day", "vencimiento", "emision"]
        
        # Por nombre de campo
        if any(kw in field_name.lower() for kw in date_keywords):
            return True
        
        # Por patron
        date_patterns = [
            r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}',  # DD/MM/YYYY
            r'\d{4}[/\-]\d{1,2}[/\-]\d{1,2}',     # YYYY-MM-DD
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',   # DD de Mes de YYYY
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _looks_like_number(self, value: str, field_name: str) -> bool:
        """Detecta si un valor parece ser un numero."""
        number_keywords = [
            "total", "subtotal", "monto", "cantidad", "precio", "importe",
            "amount", "price", "qty", "quantity", "tax", "iva", "descuento"
        ]
        
        # Por nombre de campo
        if any(kw in field_name.lower() for kw in number_keywords):
            return True
        
        # Por patron (numero con posibles separadores y simbolos de moneda)
        # Limpiar simbolos de moneda primero
        clean_value = value
        for symbol in self.CURRENCY_SYMBOLS:
            clean_value = clean_value.replace(symbol, "").strip()
        
        # Patron numerico
        number_pattern = r'^[\d\s,.\-+]+$'
        if re.match(number_pattern, clean_value):
            # Verificar que tenga al menos un digito
            if re.search(r'\d', clean_value):
                return True
        
        return False
    
    def _normalize_date(self, value: str) -> Optional[str]:
        """
        Normaliza una fecha al formato configurado.
        
        Args:
            value: Fecha en formato original.
            
        Returns:
            Fecha en formato ISO o None si no se puede parsear.
        """
        if not value:
            return None
        
        # Reemplazar meses en espanol
        value_normalized = value.lower()
        for esp, eng in self.SPANISH_MONTHS.items():
            value_normalized = value_normalized.replace(esp, eng)
        
        # Intentar con formatos conocidos primero
        for fmt in self.date_input_formats:
            try:
                parsed = datetime.strptime(value_normalized, fmt)
                return parsed.strftime(self.date_output_format)
            except ValueError:
                continue
        
        # Fallback: usar dateutil parser
        try:
            parsed = date_parser.parse(value_normalized, dayfirst=True)
            return parsed.strftime(self.date_output_format)
        except (ValueError, TypeError):
            logger.debug(f"No se pudo parsear fecha: {value}")
            return value  # Retornar original si no se puede parsear
    
    def _normalize_number(self, value: str) -> Optional[float]:
        """
        Normaliza un numero/moneda.
        
        Args:
            value: Numero en formato original.
            
        Returns:
            Numero como float o None si no se puede parsear.
        """
        if not value:
            return None
        
        # Limpiar simbolos de moneda
        clean = value
        for symbol in self.CURRENCY_SYMBOLS:
            clean = clean.replace(symbol, "")
        
        # Limpiar espacios
        clean = clean.strip()
        
        # Determinar formato (europeo vs americano)
        # Si tiene coma seguida de exactamente 2 digitos al final, es decimal
        # Si tiene punto seguido de exactamente 2 digitos al final, es decimal
        
        # Contar comas y puntos
        comma_count = clean.count(",")
        dot_count = clean.count(".")
        
        if comma_count == 1 and dot_count == 0:
            # Formato europeo: 1234,56
            if re.search(r',\d{1,2}$', clean):
                clean = clean.replace(",", ".")
        elif dot_count == 1 and comma_count == 0:
            # Formato americano: 1234.56 (ya esta bien)
            pass
        elif comma_count >= 1 and dot_count >= 1:
            # Formato mixto: determinar cual es decimal
            last_comma = clean.rfind(",")
            last_dot = clean.rfind(".")
            
            if last_comma > last_dot:
                # Coma es decimal: 1.234,56 -> 1234.56
                clean = clean.replace(".", "").replace(",", ".")
            else:
                # Punto es decimal: 1,234.56 -> 1234.56
                clean = clean.replace(",", "")
        else:
            # Multiples del mismo separador: asumir miles
            clean = clean.replace(",", "").replace(".", "")
        
        # Parsear como float
        try:
            return float(clean)
        except ValueError:
            logger.debug(f"No se pudo parsear numero: {value}")
            return None
    
    def _normalize_text(self, value: str) -> str:
        """
        Normaliza texto general.
        
        Args:
            value: Texto a normalizar.
            
        Returns:
            Texto normalizado.
        """
        if not value:
            return ""
        
        # Normalizar unicode
        if self.normalize_unicode:
            value = self._normalize_unicode_text(value)
        
        # Normalizar whitespace
        if self.strip_whitespace:
            value = " ".join(value.split())
        
        return value
    
    def _normalize_unicode_text(self, text: str) -> str:
        """
        Normaliza caracteres unicode problematicos.
        
        Args:
            text: Texto con posibles caracteres unicode.
            
        Returns:
            Texto con unicode normalizado.
        """
        import unicodedata
        
        # Normalizar a forma NFC
        text = unicodedata.normalize("NFC", text)
        
        # Reemplazar caracteres especiales comunes
        replacements = {
            "\u2018": "'",  # Left single quote
            "\u2019": "'",  # Right single quote
            "\u201c": '"',  # Left double quote
            "\u201d": '"',  # Right double quote
            "\u2013": "-",  # En dash
            "\u2014": "-",  # Em dash
            "\u00a0": " ",  # Non-breaking space
            "\u2026": "...",  # Ellipsis
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
