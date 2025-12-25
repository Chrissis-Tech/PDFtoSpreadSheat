"""
Invoice Parser
==============

Parser especializado para facturas y documentos fiscales.
"""

import re
from typing import Any, Dict, List, Optional

from loguru import logger

from .base_parser import BaseParser


class InvoiceParser(BaseParser):
    """
    Parser para documentos tipo factura.
    
    Extrae campos comunes de facturas:
    - Numero de factura
    - Fecha de emision
    - Proveedor/Cliente
    - Items/Lineas
    - Subtotal, IVA, Total
    """
    
    PARSER_NAME = "invoice"
    
    # Patterns for common invoice fields
    PATTERNS = {
        # Invoice number - requires colon after keyword phrase
        "invoice_id": r"(?:factura|invoice|folio)(?:\s+(?:no\.?|numero|num|#))?\s*[:.]\s*([A-Z0-9][\w\-]*)|(?:no\.?|#)\s*[:.#]?\s*([A-Z0-9][\w\-]*)",
        
        # Date
        "date": r"(?:fecha|date|emision)\s*[:.]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        
        # Fecha alternativa (formato largo)
        "date_long": r"(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
        
        # Proveedor
        "vendor": r"(?:proveedor|vendor|emisor|razon social)\s*[:.]?\s*(.+?)(?:\n|$)",
        
        # RFC/NIF
        "tax_id": r"(?:rfc|nif|cif|tax\s*id)\s*[:.]?\s*([A-Z0-9\-]+)",
        
        # Subtotal
        "subtotal": r"(?:subtotal|sub\s*total)\s*[:.]?\s*\$?\s*([\d,\.]+)",
        
        # IVA
        "tax": r"(?:iva|tax|impuesto)\s*[:.]?\s*\$?\s*([\d,\.]+)",
        
        # Total
        "total": r"(?:total\s*(?:a\s*pagar)?|grand\s*total|importe\s*total)\s*[:.]?\s*\$?\s*([\d,\.]+)",
        
        # Cliente
        "client": r"(?:cliente|customer|comprador|receptor)\s*[:.]?\s*(.+?)(?:\n|$)",
    }
    
    # Patrones para detectar lineas de items
    ITEM_PATTERNS = {
        # Patron: cantidad, descripcion, precio unitario, total linea
        "full_line": r"(\d+)\s+(.+?)\s+\$?([\d,\.]+)\s+\$?([\d,\.]+)",
        
        # Patron alternativo: descripcion y total
        "simple_line": r"(.+?)\s+\$?([\d,\.]+)\s*$",
    }
    
    REQUIRED_FIELDS = ["invoice_id", "date", "total"]
    
    def parse(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsea datos de factura.
        
        Args:
            extracted_data: Datos extraidos del PDF.
            
        Returns:
            Lista con un diccionario de datos de la factura.
        """
        text = extracted_data.get("text", "")
        tables = extracted_data.get("tables", [])
        
        if not text and not tables:
            logger.warning("No hay datos para parsear")
            return []
        
        # Limpiar texto
        text = self.clean_text(text)
        
        # Extraer campos principales
        invoice_data = self._extract_header_fields(text)
        
        # Extraer items (lineas de la factura)
        if tables:
            items = self._extract_items_from_tables(tables)
        else:
            items = self._extract_items_from_text(text)
        
        invoice_data["items"] = items
        invoice_data["items_count"] = len(items)
        
        # Si hay items, calcular totales si faltan
        if items and not invoice_data.get("subtotal"):
            invoice_data["subtotal"] = sum(
                float(item.get("line_total", 0) or 0) 
                for item in items
            )
        
        logger.debug(f"Factura parseada: {invoice_data.get('invoice_id', 'N/A')}")
        
        return [invoice_data]
    
    def _extract_header_fields(self, text: str) -> Dict[str, Any]:
        """Extrae campos del encabezado de la factura."""
        result = {}
        
        # Extraer cada campo usando patrones
        result["invoice_id"] = self.extract_pattern(text, self.PATTERNS["invoice_id"])
        
        # Fecha (intentar varios patrones)
        date = self.extract_pattern(text, self.PATTERNS["date"])
        if not date:
            date = self.extract_pattern(text, self.PATTERNS["date_long"])
        result["date"] = date
        
        result["vendor"] = self.extract_pattern(text, self.PATTERNS["vendor"])
        result["client"] = self.extract_pattern(text, self.PATTERNS["client"])
        result["tax_id"] = self.extract_pattern(text, self.PATTERNS["tax_id"])
        result["subtotal"] = self.extract_pattern(text, self.PATTERNS["subtotal"])
        result["tax"] = self.extract_pattern(text, self.PATTERNS["tax"])
        result["total"] = self.extract_pattern(text, self.PATTERNS["total"])
        
        return result
    
    def _extract_items_from_tables(
        self, 
        tables: List[List[List[str]]]
    ) -> List[Dict[str, Any]]:
        """Extrae items de las tablas detectadas."""
        items = []
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Detectar header
            header_row = self._detect_header_row(table)
            if header_row is None:
                continue
            
            headers = table[header_row]
            
            # Mapear headers a campos estandar
            field_mapping = self._map_headers_to_fields(headers)
            
            # Procesar filas de datos
            for row in table[header_row + 1:]:
                if not row or not any(cell for cell in row if cell):
                    continue
                
                item = {}
                for i, cell in enumerate(row):
                    if i < len(headers):
                        field = field_mapping.get(i)
                        if field:
                            item[field] = cell
                
                if item:
                    items.append(item)
        
        return items
    
    def _extract_items_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extrae items del texto cuando no hay tablas."""
        items = []
        
        # Intentar patron de linea completa
        matches = re.findall(
            self.ITEM_PATTERNS["full_line"], 
            text, 
            re.MULTILINE
        )
        
        for match in matches:
            qty, desc, unit_price, line_total = match
            items.append({
                "quantity": qty,
                "description": desc.strip(),
                "unit_price": unit_price,
                "line_total": line_total
            })
        
        return items
    
    def _detect_header_row(self, table: List[List[str]]) -> Optional[int]:
        """Detecta la fila que contiene los headers de items."""
        header_keywords = [
            "descripcion", "description", "concepto", "producto",
            "cantidad", "qty", "quantity",
            "precio", "price", "unitario",
            "importe", "total", "amount"
        ]
        
        for i, row in enumerate(table[:5]):  # Solo revisar primeras 5 filas
            if not row:
                continue
            
            row_text = " ".join(str(cell).lower() for cell in row if cell)
            
            # Contar coincidencias
            matches = sum(1 for kw in header_keywords if kw in row_text)
            
            if matches >= 2:
                return i
        
        return None
    
    def _map_headers_to_fields(self, headers: List[str]) -> Dict[int, str]:
        """Mapea headers originales a campos estandar."""
        mapping = {}
        
        field_keywords = {
            "quantity": ["cantidad", "qty", "quantity", "cant", "unidades"],
            "description": ["descripcion", "description", "concepto", "producto", "servicio", "detalle"],
            "unit_price": ["precio", "price", "unitario", "p.u.", "pu", "costo"],
            "line_total": ["importe", "total", "amount", "monto", "subtotal"],
            "unit": ["unidad", "unit", "um", "u.m."],
        }
        
        for i, header in enumerate(headers):
            if not header:
                continue
            
            header_lower = str(header).lower().strip()
            
            for field, keywords in field_keywords.items():
                if any(kw in header_lower for kw in keywords):
                    mapping[i] = field
                    break
        
        return mapping
