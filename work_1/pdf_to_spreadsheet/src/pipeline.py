"""
Main Pipeline
=============

Orquesta el proceso completo de extraccion de datos de PDFs.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from .parsers import get_parser, detect_parser_type
from .extractors.text_extractor import TextExtractor
from .extractors.table_extractor import TableExtractor
from .extractors.ocr_extractor import OCRExtractor
from .normalizer import DataNormalizer
from .validator import DataValidator
from .exporters.csv_exporter import CSVExporter
from .exporters.json_exporter import JSONExporter
from .exporters.gsheet_exporter import GSheetExporter


class Pipeline:
    """
    Pipeline principal para procesar PDFs.
    
    Orquesta el flujo completo:
    1. Extraccion de datos (texto/tablas/OCR)
    2. Parsing segun tipo de documento
    3. Normalizacion
    4. Validacion
    5. Exportacion
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        output_format: str = "csv",
        parser_type: str = "auto",
        dry_run: bool = False
    ):
        """
        Inicializa el pipeline.
        
        Args:
            config: Configuracion del sistema.
            output_format: Formato de salida (csv, json, gsheet).
            parser_type: Tipo de parser a usar (auto, invoice, report).
            dry_run: Si es True, no escribe archivos de salida.
        """
        self.config = config
        self.output_format = output_format
        self.parser_type = parser_type
        self.dry_run = dry_run
        
        # Inicializar componentes
        self._init_extractors()
        self._init_normalizer()
        self._init_validator()
        self._init_exporter()
        
        # Contadores
        self.stats = {
            "total_files": 0,
            "successful_files": 0,
            "total_rows": 0,
            "errors": 0,
            "warnings": 0
        }
    
    def _init_extractors(self) -> None:
        """Inicializa los extractores de datos."""
        extraction_config = self.config.get("extraction", {})
        
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        
        # OCR solo si esta habilitado
        if extraction_config.get("ocr_fallback", True):
            self.ocr_extractor = OCRExtractor(
                language=extraction_config.get("ocr_language", "spa+eng"),
                dpi=extraction_config.get("ocr_dpi", 300)
            )
        else:
            self.ocr_extractor = None
    
    def _init_normalizer(self) -> None:
        """Inicializa el normalizador de datos."""
        norm_config = self.config.get("normalization", {})
        self.normalizer = DataNormalizer(norm_config)
    
    def _init_validator(self) -> None:
        """Inicializa el validador de datos."""
        val_config = self.config.get("validation", {})
        self.validator = DataValidator(val_config)
    
    def _init_exporter(self) -> None:
        """Inicializa el exportador segun el formato."""
        output_config = self.config.get("output", {})
        
        exporters = {
            "csv": CSVExporter,
            "json": JSONExporter,
            "gsheet": GSheetExporter
        }
        
        exporter_class = exporters.get(self.output_format, CSVExporter)
        format_config = output_config.get(self.output_format, {})
        self.exporter = exporter_class(format_config)
    
    def process_file(
        self,
        file_path: Union[str, Path],
        output_dir: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Procesa un archivo PDF individual.
        
        Args:
            file_path: Ruta al archivo PDF.
            output_dir: Directorio de salida.
            
        Returns:
            Diccionario con resultados del procesamiento.
        """
        start_time = time.time()
        file_path = Path(file_path)
        output_dir = Path(output_dir)
        
        logger.info(f"Procesando: {file_path.name}")
        
        self.stats["total_files"] += 1
        all_data = []
        
        try:
            # 1. Extraccion
            extracted = self._extract_data(file_path)
            
            if not extracted.get("text") and not extracted.get("tables"):
                logger.warning(f"No se pudo extraer datos de {file_path.name}")
                self.stats["warnings"] += 1
                return self._build_results(start_time, output_dir)
            
            # 2. Parsing
            parser = self._get_parser(extracted)
            parsed_data = parser.parse(extracted)
            
            if not parsed_data:
                logger.warning(f"Parser no retorno datos para {file_path.name}")
                self.stats["warnings"] += 1
                return self._build_results(start_time, output_dir)
            
            # 3. Normalizacion
            normalized_data = self.normalizer.normalize(parsed_data)
            
            # 4. Validacion
            validated_data, validation_errors = self.validator.validate(
                normalized_data, 
                parser.get_validation_rules()
            )
            
            if validation_errors:
                for error in validation_errors:
                    logger.warning(f"Validacion: {error}")
                self.stats["warnings"] += len(validation_errors)
            
            # 5. Deduplicacion
            dedup_config = self.config.get("deduplication", {})
            if dedup_config.get("enabled", True):
                validated_data = self._deduplicate(validated_data, dedup_config)
            
            all_data = validated_data
            self.stats["total_rows"] += len(all_data)
            self.stats["successful_files"] += 1
            
            # 6. Exportacion
            output_file = None
            if not self.dry_run and all_data:
                output_file = self._export_data(all_data, output_dir, file_path.stem)
                logger.info(f"Exportado a: {output_file}")
            
        except Exception as e:
            logger.error(f"Error procesando {file_path.name}: {e}")
            self.stats["errors"] += 1
            output_file = None
        
        return self._build_results(start_time, output_dir, output_file)
    
    def process_directory(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Procesa todos los PDFs en un directorio.
        
        Args:
            input_dir: Directorio con PDFs.
            output_dir: Directorio de salida.
            
        Returns:
            Diccionario con resultados del procesamiento.
        """
        start_time = time.time()
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        # Encontrar todos los PDFs
        pdf_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))
        
        if not pdf_files:
            logger.warning(f"No se encontraron PDFs en {input_dir}")
            return self._build_results(start_time, output_dir)
        
        logger.info(f"Encontrados {len(pdf_files)} archivos PDF")
        
        all_data = []
        
        for pdf_file in pdf_files:
            try:
                # Procesar cada archivo
                extracted = self._extract_data(pdf_file)
                
                if not extracted.get("text") and not extracted.get("tables"):
                    logger.warning(f"No se pudo extraer datos de {pdf_file.name}")
                    self.stats["warnings"] += 1
                    self.stats["total_files"] += 1
                    continue
                
                parser = self._get_parser(extracted)
                parsed_data = parser.parse(extracted)
                
                if parsed_data:
                    normalized_data = self.normalizer.normalize(parsed_data)
                    validated_data, validation_errors = self.validator.validate(
                        normalized_data,
                        parser.get_validation_rules()
                    )
                    
                    if validation_errors:
                        for error in validation_errors:
                            logger.warning(f"Validacion [{pdf_file.name}]: {error}")
                        self.stats["warnings"] += len(validation_errors)
                    
                    # Agregar nombre de archivo fuente
                    for row in validated_data:
                        row["_source_file"] = pdf_file.name
                    
                    all_data.extend(validated_data)
                    self.stats["total_rows"] += len(validated_data)
                    self.stats["successful_files"] += 1
                
                self.stats["total_files"] += 1
                
            except Exception as e:
                logger.error(f"Error procesando {pdf_file.name}: {e}")
                self.stats["errors"] += 1
                self.stats["total_files"] += 1
        
        # Deduplicar todo el dataset
        dedup_config = self.config.get("deduplication", {})
        if dedup_config.get("enabled", True) and all_data:
            original_count = len(all_data)
            all_data = self._deduplicate(all_data, dedup_config)
            removed = original_count - len(all_data)
            if removed > 0:
                logger.info(f"Deduplicacion: eliminadas {removed} filas duplicadas")
        
        # Exportar todo junto
        if not self.dry_run and all_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self._export_data(all_data, output_dir, f"resultado_{timestamp}")
            logger.info(f"Exportado a: {output_file}")
        
        return self._build_results(start_time, output_dir)
    
    def _extract_data(self, file_path: Path) -> Dict[str, Any]:
        """Extrae datos del PDF usando la estrategia configurada."""
        extraction_config = self.config.get("extraction", {})
        strategy = extraction_config.get("strategy", "auto")
        prefer_tables = extraction_config.get("prefer_tables", True)
        
        result = {
            "text": "",
            "tables": [],
            "metadata": {
                "file_name": file_path.name,
                "extraction_method": None
            }
        }
        
        # Intentar extraccion de texto
        text = self.text_extractor.extract(file_path)
        result["text"] = text
        
        # Intentar extraccion de tablas si se prefiere
        if prefer_tables or strategy == "table_first":
            tables = self.table_extractor.extract(file_path)
            result["tables"] = tables
            if tables:
                result["metadata"]["extraction_method"] = "tables"
        
        # Si no hay texto ni tablas, intentar OCR
        if not text and not result["tables"]:
            if self.ocr_extractor and extraction_config.get("ocr_fallback", True):
                logger.info(f"Usando OCR para {file_path.name}")
                text = self.ocr_extractor.extract(file_path)
                result["text"] = text
                result["metadata"]["extraction_method"] = "ocr"
        
        if not result["metadata"]["extraction_method"]:
            result["metadata"]["extraction_method"] = "text"
        
        return result
    
    def _get_parser(self, extracted: Dict[str, Any]) -> Any:
        """Obtiene el parser apropiado para los datos extraidos."""
        if self.parser_type == "auto":
            parser_type = detect_parser_type(extracted, self.config)
        else:
            parser_type = self.parser_type
        
        parser_config = self.config.get("parsers", {}).get(parser_type, {})
        return get_parser(parser_type, parser_config)
    
    def _deduplicate(
        self,
        data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Elimina filas duplicadas del dataset."""
        if not data:
            return data
        
        key_columns = config.get("key_columns", [])
        keep = config.get("keep", "first")
        
        seen = set()
        result = []
        
        for row in data:
            # Crear clave para comparacion
            if key_columns:
                key = tuple(row.get(col) for col in key_columns)
            else:
                # Usar todas las columnas excepto _source_file
                key = tuple(
                    (k, v) for k, v in sorted(row.items()) 
                    if not k.startswith("_")
                )
            
            if key not in seen:
                seen.add(key)
                result.append(row)
            elif keep == "last":
                # Reemplazar con el ultimo
                for i, r in enumerate(result):
                    if key_columns:
                        r_key = tuple(r.get(col) for col in key_columns)
                    else:
                        r_key = tuple(
                            (k, v) for k, v in sorted(r.items())
                            if not k.startswith("_")
                        )
                    if r_key == key:
                        result[i] = row
                        break
        
        return result
    
    def _export_data(
        self,
        data: List[Dict[str, Any]],
        output_dir: Path,
        base_name: str
    ) -> Path:
        """Exporta los datos al formato configurado."""
        return self.exporter.export(data, output_dir, base_name)
    
    def _build_results(
        self, 
        start_time: float, 
        output_dir: Path,
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Construye el diccionario de resultados."""
        elapsed_time = time.time() - start_time
        
        results = {
            **self.stats,
            "elapsed_time": elapsed_time,
            "output_dir": str(output_dir)
        }
        
        # Use provided output_file if available
        if output_file:
            results["output_file"] = str(output_file)
        else:
            # Fallback: search for most recent file with correct extension
            if self.output_format == "csv":
                ext = ".csv"
            elif self.output_format == "json":
                ext = ".json"
            else:
                ext = ""
            
            if ext:
                output_files = list(output_dir.glob(f"*{ext}"))
                if output_files:
                    results["output_file"] = str(max(output_files, key=lambda p: p.stat().st_mtime))
        
        return results

