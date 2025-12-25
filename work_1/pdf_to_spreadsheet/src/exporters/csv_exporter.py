"""
CSV Exporter
============

Exporta datos a formato CSV.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger


class CSVExporter:
    """
    Exporta datos a archivos CSV.
    
    Soporta:
    - Delimitador configurable
    - Encoding configurable
    - Headers automaticos
    - Manejo de valores especiales
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el exportador.
        
        Args:
            config: Configuracion de CSV.
        """
        self.config = config or {}
        
        self.delimiter = self.config.get("delimiter", ",")
        self.encoding = self.config.get("encoding", "utf-8")
        self.include_header = self.config.get("include_header", True)
        
        # Configuracion de quoting
        quoting_map = {
            "minimal": csv.QUOTE_MINIMAL,
            "all": csv.QUOTE_ALL,
            "none": csv.QUOTE_NONE,
            "nonnumeric": csv.QUOTE_NONNUMERIC
        }
        quoting_str = self.config.get("quoting", "minimal")
        self.quoting = quoting_map.get(quoting_str, csv.QUOTE_MINIMAL)
    
    def export(
        self,
        data: List[Dict[str, Any]],
        output_dir: Union[str, Path],
        base_name: str
    ) -> Path:
        """
        Exporta datos a un archivo CSV.
        
        Args:
            data: Lista de diccionarios con los datos.
            output_dir: Directorio de salida.
            base_name: Nombre base del archivo (sin extension).
            
        Returns:
            Ruta al archivo generado.
        """
        if not data:
            logger.warning("No hay datos para exportar")
            return Path(output_dir) / f"{base_name}.csv"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{base_name}.csv"
        
        # Obtener todos los headers (union de todas las claves)
        headers = self._get_all_headers(data)
        
        # Filtrar headers internos (empiezan con _)
        if not self.config.get("include_internal_fields", False):
            headers = [h for h in headers if not h.startswith("_")]
        
        try:
            with open(output_file, 'w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=headers,
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                    extrasaction='ignore'
                )
                
                if self.include_header:
                    writer.writeheader()
                
                for row in data:
                    # Convertir valores especiales
                    clean_row = self._clean_row(row, headers)
                    writer.writerow(clean_row)
            
            logger.info(f"CSV exportado: {output_file} ({len(data)} filas)")
            return output_file
            
        except Exception as e:
            logger.error(f"Error exportando CSV: {e}")
            raise
    
    def _get_all_headers(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Obtiene la lista de todos los headers presentes en los datos.
        
        Mantiene el orden de aparicion.
        """
        headers = []
        seen = set()
        
        for row in data:
            for key in row.keys():
                if key not in seen:
                    headers.append(key)
                    seen.add(key)
        
        return headers
    
    def _clean_row(
        self, 
        row: Dict[str, Any], 
        headers: List[str]
    ) -> Dict[str, str]:
        """
        Limpia y convierte valores de una fila para CSV.
        
        Args:
            row: Diccionario con datos originales.
            headers: Lista de headers a incluir.
            
        Returns:
            Diccionario con valores convertidos a string.
        """
        clean = {}
        
        for header in headers:
            value = row.get(header)
            
            if value is None:
                clean[header] = ""
            elif isinstance(value, bool):
                clean[header] = "true" if value else "false"
            elif isinstance(value, (list, dict)):
                # Serializar estructuras complejas
                import json
                clean[header] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, datetime):
                clean[header] = value.isoformat()
            elif isinstance(value, float):
                # Evitar notacion cientifica para numeros grandes
                if abs(value) > 1e10 or (abs(value) < 1e-4 and value != 0):
                    clean[header] = f"{value:.2f}"
                else:
                    clean[header] = str(value)
            else:
                clean[header] = str(value)
        
        return clean
    
    def export_multiple(
        self,
        datasets: Dict[str, List[Dict[str, Any]]],
        output_dir: Union[str, Path]
    ) -> Dict[str, Path]:
        """
        Exporta multiples datasets a archivos CSV separados.
        
        Args:
            datasets: Diccionario {nombre: datos}.
            output_dir: Directorio de salida.
            
        Returns:
            Diccionario {nombre: ruta_archivo}.
        """
        output_files = {}
        
        for name, data in datasets.items():
            output_file = self.export(data, output_dir, name)
            output_files[name] = output_file
        
        return output_files
