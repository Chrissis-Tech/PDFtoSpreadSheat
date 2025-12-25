"""
OCR Extractor
=============

Extrae texto de PDFs escaneados usando OCR (Tesseract).
"""

from pathlib import Path
from typing import Optional, Union

from loguru import logger

# Verificar disponibilidad de dependencias opcionales
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class OCRExtractor:
    """
    Extrae texto de PDFs escaneados usando Tesseract OCR.
    
    NOTA: Este extractor es OPCIONAL y requiere:
    - pytesseract (pip install pytesseract)
    - Pillow (pip install Pillow)
    - pdf2image (pip install pdf2image)
    - Tesseract instalado en el sistema
    
    Si las dependencias no estan disponibles, los metodos
    retornaran strings vacios con advertencias.
    """
    
    def __init__(
        self,
        language: str = "spa+eng",
        dpi: int = 300,
        max_pages: int = 50
    ):
        """
        Inicializa el extractor OCR.
        
        Args:
            language: Idioma(s) para OCR (formato Tesseract).
            dpi: DPI para conversion de PDF a imagen.
            max_pages: Maximo de paginas a procesar con OCR.
        """
        self.language = language
        self.dpi = dpi
        self.max_pages = max_pages
        
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Verifica y registra el estado de las dependencias."""
        if not TESSERACT_AVAILABLE:
            logger.warning(
                "pytesseract no disponible. "
                "Instala con: pip install pytesseract Pillow"
            )
        
        if not PDF2IMAGE_AVAILABLE:
            logger.warning(
                "pdf2image no disponible. "
                "Instala con: pip install pdf2image"
            )
    
    @property
    def is_available(self) -> bool:
        """Indica si el OCR esta disponible."""
        return TESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE
    
    def extract(self, file_path: Union[str, Path]) -> str:
        """
        Extrae texto de un PDF usando OCR.
        
        Args:
            file_path: Ruta al archivo PDF.
            
        Returns:
            Texto extraido por OCR.
        """
        if not self.is_available:
            logger.warning("OCR no disponible - dependencias faltantes")
            return ""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        try:
            return self._extract_with_pdf2image(file_path)
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            
            # Fallback: intentar renderizar con pdfplumber
            if PDFPLUMBER_AVAILABLE:
                return self._extract_with_pdfplumber_render(file_path)
            
            return ""
    
    def _extract_with_pdf2image(self, file_path: Path) -> str:
        """Extrae texto convirtiendo PDF a imagenes con pdf2image."""
        text_parts = []
        
        # Convertir PDF a imagenes
        logger.debug(f"Convirtiendo PDF a imagenes (DPI: {self.dpi})")
        
        images = pdf2image.convert_from_path(
            str(file_path),
            dpi=self.dpi,
            first_page=1,
            last_page=self.max_pages
        )
        
        logger.debug(f"Procesando {len(images)} paginas con OCR")
        
        for i, image in enumerate(images):
            try:
                # Aplicar OCR a la imagen
                page_text = pytesseract.image_to_string(
                    image,
                    lang=self.language,
                    config='--psm 1'  # Automatic page segmentation with OSD
                )
                
                if page_text and page_text.strip():
                    text_parts.append(page_text)
                
                if (i + 1) % 5 == 0:
                    logger.debug(f"OCR: {i + 1}/{len(images)} paginas procesadas")
                    
            except Exception as e:
                logger.warning(f"Error OCR en pagina {i + 1}: {e}")
                continue
        
        return "\n\n".join(text_parts)
    
    def _extract_with_pdfplumber_render(self, file_path: Path) -> str:
        """
        Fallback: renderizar paginas con pdfplumber y aplicar OCR.
        
        Menos eficiente que pdf2image pero no requiere poppler.
        """
        if not PDFPLUMBER_AVAILABLE or not TESSERACT_AVAILABLE:
            return ""
        
        text_parts = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                pages_to_process = min(len(pdf.pages), self.max_pages)
                
                for i, page in enumerate(pdf.pages[:pages_to_process]):
                    try:
                        # Renderizar pagina a imagen
                        image = page.to_image(resolution=self.dpi)
                        pil_image = image.original
                        
                        # Aplicar OCR
                        page_text = pytesseract.image_to_string(
                            pil_image,
                            lang=self.language
                        )
                        
                        if page_text and page_text.strip():
                            text_parts.append(page_text)
                            
                    except Exception as e:
                        logger.debug(f"Error procesando pagina {i + 1}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error con pdfplumber render: {e}")
        
        return "\n\n".join(text_parts)
    
    def extract_page(
        self,
        file_path: Union[str, Path],
        page_number: int
    ) -> str:
        """
        Extrae texto de una pagina especifica usando OCR.
        
        Args:
            file_path: Ruta al archivo PDF.
            page_number: Numero de pagina (1-indexed para pdf2image).
            
        Returns:
            Texto de la pagina.
        """
        if not self.is_available:
            return ""
        
        file_path = Path(file_path)
        
        try:
            images = pdf2image.convert_from_path(
                str(file_path),
                dpi=self.dpi,
                first_page=page_number + 1,
                last_page=page_number + 1
            )
            
            if images:
                return pytesseract.image_to_string(
                    images[0],
                    lang=self.language
                )
        
        except Exception as e:
            logger.debug(f"Error OCR en pagina {page_number}: {e}")
        
        return ""
    
    def preprocess_image(self, image: "Image.Image") -> "Image.Image":
        """
        Preprocesa una imagen para mejorar resultados de OCR.
        
        Args:
            image: Imagen PIL.
            
        Returns:
            Imagen preprocesada.
        """
        if not TESSERACT_AVAILABLE:
            return image
        
        try:
            # Convertir a escala de grises
            if image.mode != 'L':
                image = image.convert('L')
            
            # Aqui se podrian agregar mas pasos:
            # - Binarizacion
            # - Eliminacion de ruido
            # - Correccion de inclinacion
            
            return image
            
        except Exception as e:
            logger.debug(f"Error en preprocesamiento: {e}")
            return image
