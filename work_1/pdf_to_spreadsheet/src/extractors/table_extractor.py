"""
Table Extractor
===============

Extrae tablas estructuradas de documentos PDF.
"""

from pathlib import Path
from typing import Any, List, Optional, Union

from loguru import logger

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False


class TableExtractor:
    """
    Extrae tablas de PDFs usando pdfplumber o tabula-py.
    
    Cada tabla se retorna como una lista de filas,
    donde cada fila es una lista de celdas.
    """
    
    def __init__(
        self,
        max_pages: int = 100,
        min_rows: int = 2,
        min_cols: int = 2
    ):
        """
        Inicializa el extractor.
        
        Args:
            max_pages: Numero maximo de paginas a procesar.
            min_rows: Minimo de filas para considerar una tabla valida.
            min_cols: Minimo de columnas para considerar una tabla valida.
        """
        self.max_pages = max_pages
        self.min_rows = min_rows
        self.min_cols = min_cols
        
        if not PDFPLUMBER_AVAILABLE and not TABULA_AVAILABLE:
            logger.warning(
                "Ninguna libreria de extraccion de tablas disponible. "
                "Instala pdfplumber o tabula-py."
            )
    
    def extract(
        self, 
        file_path: Union[str, Path]
    ) -> List[List[List[Optional[str]]]]:
        """
        Extrae todas las tablas de un PDF.
        
        Args:
            file_path: Ruta al archivo PDF.
            
        Returns:
            Lista de tablas. Cada tabla es una lista de filas,
            y cada fila es una lista de celdas (strings o None).
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        tables = []
        
        # Intentar con pdfplumber primero
        if PDFPLUMBER_AVAILABLE:
            tables = self._extract_with_pdfplumber(file_path)
        
        # Si no hay tablas, intentar con tabula
        if not tables and TABULA_AVAILABLE:
            tables = self._extract_with_tabula(file_path)
        
        # Filtrar tablas muy pequenas
        tables = self._filter_tables(tables)
        
        logger.debug(f"Extraidas {len(tables)} tablas de {file_path.name}")
        
        return tables
    
    def _extract_with_pdfplumber(
        self, 
        file_path: Path
    ) -> List[List[List[Optional[str]]]]:
        """Extrae tablas usando pdfplumber."""
        all_tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                pages_to_process = min(len(pdf.pages), self.max_pages)
                
                for page_num, page in enumerate(pdf.pages[:pages_to_process]):
                    # Configuracion de extraccion de tablas
                    table_settings = {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                    }
                    
                    # Intentar extraer tablas con diferentes estrategias
                    page_tables = page.extract_tables(table_settings)
                    
                    if not page_tables:
                        # Intentar con estrategia de texto
                        table_settings["vertical_strategy"] = "text"
                        table_settings["horizontal_strategy"] = "text"
                        page_tables = page.extract_tables(table_settings)
                    
                    for table in page_tables:
                        if table:
                            # Convertir None a string vacio y limpiar
                            cleaned_table = self._clean_table(table)
                            if cleaned_table:
                                all_tables.append(cleaned_table)
                    
                    if (page_num + 1) % 10 == 0:
                        logger.debug(f"Procesadas {page_num + 1}/{pages_to_process} paginas")
        
        except Exception as e:
            logger.debug(f"Error con pdfplumber tables: {e}")
        
        return all_tables
    
    def _extract_with_tabula(
        self, 
        file_path: Path
    ) -> List[List[List[Optional[str]]]]:
        """Extrae tablas usando tabula-py."""
        all_tables = []
        
        try:
            # tabula retorna DataFrames
            dfs = tabula.read_pdf(
                str(file_path),
                pages="all",
                multiple_tables=True,
                silent=True
            )
            
            for df in dfs:
                if df is not None and not df.empty:
                    # Convertir DataFrame a lista de listas
                    table = [df.columns.tolist()]  # Headers
                    table.extend(df.values.tolist())  # Data
                    
                    cleaned_table = self._clean_table(table)
                    if cleaned_table:
                        all_tables.append(cleaned_table)
        
        except Exception as e:
            logger.debug(f"Error con tabula: {e}")
        
        return all_tables
    
    def _clean_table(
        self, 
        table: List[List[Any]]
    ) -> Optional[List[List[Optional[str]]]]:
        """
        Limpia y valida una tabla.
        
        Args:
            table: Tabla cruda.
            
        Returns:
            Tabla limpia o None si no es valida.
        """
        if not table:
            return None
        
        cleaned = []
        
        for row in table:
            if not row:
                continue
            
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append(None)
                else:
                    # Convertir a string y limpiar
                    cell_str = str(cell).strip()
                    # Manejar valores NaN de pandas
                    if cell_str.lower() in ['nan', 'none', '']:
                        cleaned_row.append(None)
                    else:
                        # Limpiar saltos de linea dentro de celdas
                        cell_str = ' '.join(cell_str.split())
                        cleaned_row.append(cell_str)
            
            cleaned.append(cleaned_row)
        
        # Validar tamano minimo
        if len(cleaned) < self.min_rows:
            return None
        
        # Verificar que hay suficientes columnas
        max_cols = max(len(row) for row in cleaned) if cleaned else 0
        if max_cols < self.min_cols:
            return None
        
        # Normalizar numero de columnas
        for row in cleaned:
            while len(row) < max_cols:
                row.append(None)
        
        return cleaned
    
    def _filter_tables(
        self, 
        tables: List[List[List[Optional[str]]]]
    ) -> List[List[List[Optional[str]]]]:
        """
        Filtra tablas que no cumplen criterios minimos.
        
        Args:
            tables: Lista de tablas.
            
        Returns:
            Lista filtrada.
        """
        filtered = []
        
        for table in tables:
            if not table:
                continue
            
            # Contar filas con contenido real
            non_empty_rows = sum(
                1 for row in table 
                if any(cell for cell in row if cell)
            )
            
            if non_empty_rows >= self.min_rows:
                filtered.append(table)
        
        return filtered
    
    def extract_from_page(
        self, 
        file_path: Union[str, Path],
        page_number: int
    ) -> List[List[List[Optional[str]]]]:
        """
        Extrae tablas de una pagina especifica.
        
        Args:
            file_path: Ruta al archivo PDF.
            page_number: Numero de pagina (0-indexed).
            
        Returns:
            Lista de tablas de esa pagina.
        """
        file_path = Path(file_path)
        tables = []
        
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(file_path) as pdf:
                    if page_number < len(pdf.pages):
                        page = pdf.pages[page_number]
                        page_tables = page.extract_tables()
                        
                        for table in page_tables:
                            cleaned = self._clean_table(table)
                            if cleaned:
                                tables.append(cleaned)
            except Exception as e:
                logger.debug(f"Error extrayendo tablas de pagina {page_number}: {e}")
        
        return tables
