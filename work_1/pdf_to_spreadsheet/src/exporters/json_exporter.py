"""
JSON Exporter
=============

Exporta datos a formato JSON.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger


class JSONExporter:
    """
    Exporta datos a archivos JSON.
    
    Soporta:
    - Indentacion configurable
    - Diferentes orientaciones (records, columns)
    - Manejo de tipos especiales (datetime, bytes)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el exportador.
        
        Args:
            config: Configuracion de JSON.
        """
        self.config = config or {}
        
        self.indent = self.config.get("indent", 2)
        self.ensure_ascii = self.config.get("ensure_ascii", False)
        self.orient = self.config.get("orient", "records")  # records, index, columns
    
    def export(
        self,
        data: List[Dict[str, Any]],
        output_dir: Union[str, Path],
        base_name: str
    ) -> Path:
        """
        Exporta datos a un archivo JSON.
        
        Args:
            data: Lista de diccionarios con los datos.
            output_dir: Directorio de salida.
            base_name: Nombre base del archivo (sin extension).
            
        Returns:
            Ruta al archivo generado.
        """
        if not data:
            logger.warning("No hay datos para exportar")
            # Crear archivo JSON vacio
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{base_name}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            
            return output_file
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{base_name}.json"
        
        # Filtrar campos internos si se especifica
        if not self.config.get("include_internal_fields", False):
            data = [
                {k: v for k, v in row.items() if not k.startswith("_")}
                for row in data
            ]
        
        # Convertir segun orientacion
        if self.orient == "records":
            output_data = data
        elif self.orient == "index":
            output_data = {i: row for i, row in enumerate(data)}
        elif self.orient == "columns":
            output_data = self._to_columns(data)
        else:
            output_data = data
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    output_data,
                    f,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                    default=self._json_serializer
                )
            
            logger.info(f"JSON exportado: {output_file} ({len(data)} registros)")
            return output_file
            
        except Exception as e:
            logger.error(f"Error exportando JSON: {e}")
            raise
    
    def _to_columns(self, data: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Convierte lista de diccionarios a formato columnar.
        
        Args:
            data: Lista de diccionarios.
            
        Returns:
            Diccionario con columnas como listas.
        """
        if not data:
            return {}
        
        # Obtener todas las columnas
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        
        # Crear estructura columnar
        columns = {key: [] for key in all_keys}
        
        for row in data:
            for key in all_keys:
                columns[key].append(row.get(key))
        
        return columns
    
    def _json_serializer(self, obj: Any) -> Any:
        """
        Serializador para tipos no soportados por JSON.
        
        Args:
            obj: Objeto a serializar.
            
        Returns:
            Representacion serializable.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        
        return str(obj)
    
    def export_with_metadata(
        self,
        data: List[Dict[str, Any]],
        output_dir: Union[str, Path],
        base_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Exporta datos con metadatos adicionales.
        
        Args:
            data: Lista de diccionarios con los datos.
            output_dir: Directorio de salida.
            base_name: Nombre base del archivo.
            metadata: Metadatos adicionales a incluir.
            
        Returns:
            Ruta al archivo generado.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{base_name}.json"
        
        # Estructura con metadatos
        output_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "record_count": len(data),
                **(metadata or {})
            },
            "data": data
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    output_data,
                    f,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                    default=self._json_serializer
                )
            
            logger.info(f"JSON con metadata exportado: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error exportando JSON: {e}")
            raise
