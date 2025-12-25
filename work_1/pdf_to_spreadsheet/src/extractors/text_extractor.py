"""
Text Extractor
==============

Extrae texto plano de documentos PDF.
"""

from pathlib import Path
from typing import Optional, Union

from loguru import logger

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


class TextExtractor:
    """
    Extrae texto de PDFs usando pdfplumber o PyPDF2.
    
    Prioriza pdfplumber por mejor precision, con PyPDF2 como fallback.
    """
    
    def __init__(self, max_pages: int = 100):
        """
        Inicializa el extractor.
        
        Args:
            max_pages: Numero maximo de paginas a procesar.
        """
        self.max_pages = max_pages
        
        if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
            raise ImportError(
                "Se requiere pdfplumber o PyPDF2. "
                "Instala con: pip install pdfplumber PyPDF2"
            )
    
    def extract(self, file_path: Union[str, Path]) -> str:
        """
        Extrae todo el texto de un PDF.
        
        Args:
            file_path: Ruta al archivo PDF.
            
        Returns:
            Texto extraido del documento.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        if not file_path.suffix.lower() == ".pdf":
            raise ValueError(f"El archivo no es un PDF: {file_path}")
        
        # Intentar con pdfplumber primero
        if PDFPLUMBER_AVAILABLE:
            text = self._extract_with_pdfplumber(file_path)
            if text and text.strip():
                return text
        
        # Fallback a PyPDF2
        if PYPDF2_AVAILABLE:
            text = self._extract_with_pypdf2(file_path)
            if text and text.strip():
                return text
        
        logger.warning(f"No se pudo extraer texto de {file_path.name}")
        return ""
    
    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extrae texto usando pdfplumber."""
        try:
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                pages_to_process = min(len(pdf.pages), self.max_pages)
                
                for i, page in enumerate(pdf.pages[:pages_to_process]):
                    page_text = page.extract_text()
                    
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Log progreso para documentos grandes
                    if (i + 1) % 10 == 0:
                        logger.debug(f"Procesadas {i + 1}/{pages_to_process} paginas")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.debug(f"Error con pdfplumber: {e}")
            return ""
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extrae texto usando PyPDF2."""
        try:
            text_parts = []
            
            reader = PdfReader(str(file_path))
            pages_to_process = min(len(reader.pages), self.max_pages)
            
            for i in range(pages_to_process):
                page = reader.pages[i]
                page_text = page.extract_text()
                
                if page_text:
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.debug(f"Error con PyPDF2: {e}")
            return ""
    
    def extract_page(
        self, 
        file_path: Union[str, Path], 
        page_number: int
    ) -> str:
        """
        Extrae texto de una pagina especifica.
        
        Args:
            file_path: Ruta al archivo PDF.
            page_number: Numero de pagina (0-indexed).
            
        Returns:
            Texto de la pagina.
        """
        file_path = Path(file_path)
        
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(file_path) as pdf:
                    if page_number < len(pdf.pages):
                        return pdf.pages[page_number].extract_text() or ""
            except Exception as e:
                logger.debug(f"Error extrayendo pagina {page_number}: {e}")
        
        if PYPDF2_AVAILABLE:
            try:
                reader = PdfReader(str(file_path))
                if page_number < len(reader.pages):
                    return reader.pages[page_number].extract_text() or ""
            except Exception as e:
                logger.debug(f"Error extrayendo pagina {page_number}: {e}")
        
        return ""
    
    def get_page_count(self, file_path: Union[str, Path]) -> int:
        """
        Obtiene el numero de paginas del PDF.
        
        Args:
            file_path: Ruta al archivo PDF.
            
        Returns:
            Numero de paginas.
        """
        file_path = Path(file_path)
        
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(file_path) as pdf:
                    return len(pdf.pages)
            except Exception:
                pass
        
        if PYPDF2_AVAILABLE:
            try:
                reader = PdfReader(str(file_path))
                return len(reader.pages)
            except Exception:
                pass
        
        return 0
