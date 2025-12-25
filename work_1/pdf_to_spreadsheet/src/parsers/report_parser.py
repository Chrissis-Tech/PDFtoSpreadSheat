"""
Report Parser
=============

Parser para reportes y documentos con tablas estructuradas.
"""

import re
from typing import Any, Dict, List, Optional

from loguru import logger

from .base_parser import BaseParser


class ReportParser(BaseParser):
    """
    Parser para documentos tipo reporte/tabla.
    
    Diseado para extraer datos tabulares de:
    - Reportes financieros
    - Listados de inventario
    - Registros de transacciones
    - Cualquier documento con tablas estructuradas
    """
    
    PARSER_NAME = "report"
    
    # Patrones para metadatos comunes de reportes
    PATTERNS = {
        # Titulo del reporte
        "title": r"^(.+?(?:reporte|informe|report|listado).+?)$",
        
        # Fecha del reporte
        "report_date": r"(?:fecha|date|periodo|period)\s*[:.]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        
        # Periodo
        "period": r"(?:periodo|period)\s*[:.]?\s*(.+?)(?:\n|$)",
        
        # Pagina
        "page": r"(?:pagina|page|pag\.?)\s*[:.]?\s*(\d+)\s*(?:de|of|/)\s*(\d+)",
        
        # Total de registros
        "record_count": r"(?:total\s*(?:de\s*)?registros?|records?|filas?|rows?)\s*[:.]?\s*(\d+)",
    }
    
    REQUIRED_FIELDS = []  # Los reportes son mas flexibles
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Configuracion especifica para reportes
        self.skip_empty_rows = self.config.get("skip_empty_rows", True)
        self.min_columns = self.config.get("min_columns", 2)
        self.max_header_rows = self.config.get("max_header_rows", 3)
    
    def parse(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsea datos de reporte tabular.
        
        Args:
            extracted_data: Datos extraidos del PDF.
            
        Returns:
            Lista de diccionarios con los registros del reporte.
        """
        text = extracted_data.get("text", "")
        tables = extracted_data.get("tables", [])
        
        records = []
        metadata = self._extract_metadata(text)
        
        # Preferir tablas si estan disponibles
        if tables:
            records = self._parse_tables(tables)
        else:
            # Intentar parsear texto como tabla
            records = self._parse_text_as_table(text)
        
        # Agregar metadatos a cada registro si se especifica
        if metadata and self.config.get("include_metadata", False):
            for record in records:
                record["_report_title"] = metadata.get("title")
                record["_report_date"] = metadata.get("report_date")
        
        logger.debug(f"Reporte parseado: {len(records)} registros")
        
        return records
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extrae metadatos del reporte."""
        metadata = {}
        
        metadata["title"] = self.extract_pattern(text, self.PATTERNS["title"])
        metadata["report_date"] = self.extract_pattern(text, self.PATTERNS["report_date"])
        metadata["period"] = self.extract_pattern(text, self.PATTERNS["period"])
        
        # Pagina
        page_match = re.search(self.PATTERNS["page"], text, re.IGNORECASE)
        if page_match:
            metadata["current_page"] = page_match.group(1)
            metadata["total_pages"] = page_match.group(2)
        
        return metadata
    
    def _parse_tables(self, tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
        """Parsea las tablas extraidas."""
        all_records = []
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                logger.debug(f"Tabla {table_idx} omitida: muy pequena")
                continue
            
            # Detectar y validar headers
            header_row_idx = self._find_header_row(table)
            if header_row_idx is None:
                logger.debug(f"Tabla {table_idx}: no se encontro header valido")
                continue
            
            headers = table[header_row_idx]
            
            # Limpiar y validar headers
            clean_headers = self._clean_headers(headers)
            
            if len([h for h in clean_headers if h]) < self.min_columns:
                logger.debug(f"Tabla {table_idx}: muy pocas columnas")
                continue
            
            # Convertir filas a diccionarios
            for row_idx, row in enumerate(table[header_row_idx + 1:]):
                if self._is_empty_row(row):
                    continue
                
                if self._is_summary_row(row, clean_headers):
                    continue
                
                record = self._row_to_dict(row, clean_headers)
                if record:
                    all_records.append(record)
        
        return all_records
    
    def _parse_text_as_table(self, text: str) -> List[Dict[str, Any]]:
        """
        Intenta parsear texto sin tablas como datos tabulares.
        
        Util cuando pdfplumber no detecta tablas pero el texto
        tiene estructura tabular.
        """
        records = []
        lines = text.split('\n')
        
        if len(lines) < 2:
            return records
        
        # Intentar detectar separadores comunes
        separators = ['\t', '|', ';', '  ']  # Tab, pipe, semicolon, doble espacio
        
        for sep in separators:
            # Verificar si el separador esta presente consistentemente
            sep_counts = [line.count(sep) for line in lines[:10] if line.strip()]
            
            if not sep_counts:
                continue
            
            # Si la mayoria de lineas tienen el mismo numero de separadores
            most_common = max(set(sep_counts), key=sep_counts.count)
            
            if most_common >= self.min_columns - 1:
                if sep_counts.count(most_common) >= len(sep_counts) * 0.6:
                    # Usar este separador
                    records = self._parse_delimited_text(text, sep)
                    if records:
                        break
        
        return records
    
    def _parse_delimited_text(
        self, 
        text: str, 
        delimiter: str
    ) -> List[Dict[str, Any]]:
        """Parsea texto delimitado como tabla."""
        records = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if len(lines) < 2:
            return records
        
        # Primera linea no vacia como header
        header_line = None
        data_start = 0
        
        for i, line in enumerate(lines):
            if delimiter in line:
                parts = line.split(delimiter)
                if len(parts) >= self.min_columns:
                    header_line = line
                    data_start = i + 1
                    break
        
        if not header_line:
            return records
        
        headers = self._clean_headers(header_line.split(delimiter))
        
        # Procesar lineas de datos
        for line in lines[data_start:]:
            if delimiter not in line:
                continue
            
            row = line.split(delimiter)
            record = self._row_to_dict(row, headers)
            
            if record:
                records.append(record)
        
        return records
    
    def _find_header_row(self, table: List[List[str]]) -> Optional[int]:
        """Encuentra la fila que contiene los headers."""
        for i in range(min(self.max_header_rows, len(table))):
            row = table[i]
            
            if not row:
                continue
            
            # Criterios para ser header:
            # 1. Mayoria de celdas son texto (no numeros)
            # 2. No hay celdas vacias o pocas
            
            non_empty = [cell for cell in row if cell and str(cell).strip()]
            
            if len(non_empty) < self.min_columns:
                continue
            
            # Verificar que no sean todo numeros
            numeric_count = sum(
                1 for cell in non_empty 
                if re.match(r'^[\d,.\-\s\$%]+$', str(cell).strip())
            )
            
            if numeric_count < len(non_empty) * 0.5:
                return i
        
        # Por defecto, asumir primera fila
        return 0
    
    def _clean_headers(self, headers: List[Any]) -> List[str]:
        """Limpia y normaliza headers."""
        clean = []
        seen = set()
        
        for i, header in enumerate(headers):
            if header is None:
                h = f"col_{i}"
            else:
                h = str(header).strip()
                
                # Limpiar caracteres especiales
                h = re.sub(r'[\n\r\t]+', ' ', h)
                h = re.sub(r'\s+', ' ', h)
                
                if not h:
                    h = f"col_{i}"
            
            # Evitar duplicados
            original_h = h
            counter = 1
            while h.lower() in seen:
                h = f"{original_h}_{counter}"
                counter += 1
            
            seen.add(h.lower())
            clean.append(h)
        
        return clean
    
    def _is_empty_row(self, row: List[Any]) -> bool:
        """Verifica si una fila esta vacia."""
        if not row:
            return True
        
        return all(
            cell is None or str(cell).strip() == "" 
            for cell in row
        )
    
    def _is_summary_row(self, row: List[Any], headers: List[str]) -> bool:
        """Detecta filas de resumen/totales que no son datos."""
        if not row:
            return False
        
        first_cell = str(row[0]).lower().strip() if row[0] else ""
        
        summary_keywords = [
            "total", "subtotal", "suma", "promedio", "average",
            "gran total", "grand total"
        ]
        
        return any(kw in first_cell for kw in summary_keywords)
    
    def _row_to_dict(
        self, 
        row: List[Any], 
        headers: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Convierte una fila a diccionario."""
        if not row:
            return None
        
        record = {}
        has_data = False
        
        for i, cell in enumerate(row):
            if i >= len(headers):
                break
            
            header = headers[i]
            value = cell
            
            # Limpiar valor
            if value is not None:
                value = str(value).strip()
                if value:
                    has_data = True
                else:
                    value = None
            
            record[header] = value
        
        return record if has_data else None
