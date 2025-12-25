"""
Google Sheets Exporter
======================

Exporta datos a Google Sheets.

NOTA: Este exportador es OPCIONAL y requiere:
- gspread
- google-auth
- Credenciales de servicio de Google

Ver documentacion de gspread para configuracion:
https://docs.gspread.org/en/latest/oauth2.html
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

# Verificar disponibilidad de dependencias
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


class GSheetExporter:
    """
    Exporta datos a Google Sheets.
    
    Requiere credenciales de cuenta de servicio de Google.
    
    NOTA: Si las dependencias no estan instaladas,
    el exportador usara un fallback a CSV local.
    """
    
    # Scopes requeridos para Google Sheets API
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el exportador.
        
        Args:
            config: Configuracion de Google Sheets.
        """
        self.config = config or {}
        
        self.enabled = self.config.get("enabled", False) and GSPREAD_AVAILABLE
        self.credentials_file = self.config.get("credentials_file")
        self.spreadsheet_name = self.config.get("spreadsheet_name", "PDF_Extractions")
        self.worksheet_name = self.config.get("worksheet_name", "Data")
        
        self.client = None
        
        if self.enabled and self.credentials_file:
            self._init_client()
    
    def _init_client(self) -> None:
        """Inicializa el cliente de Google Sheets."""
        try:
            creds_path = Path(self.credentials_file)
            
            if not creds_path.exists():
                logger.warning(f"Credenciales no encontradas: {self.credentials_file}")
                self.enabled = False
                return
            
            credentials = Credentials.from_service_account_file(
                str(creds_path),
                scopes=self.SCOPES
            )
            
            self.client = gspread.authorize(credentials)
            logger.info("Cliente de Google Sheets inicializado")
            
        except Exception as e:
            logger.error(f"Error inicializando Google Sheets: {e}")
            self.enabled = False
    
    def export(
        self,
        data: List[Dict[str, Any]],
        output_dir: Union[str, Path],
        base_name: str
    ) -> Path:
        """
        Exporta datos a Google Sheets.
        
        Si Google Sheets no esta disponible, crea un CSV local.
        
        Args:
            data: Lista de diccionarios con los datos.
            output_dir: Directorio de salida (para fallback CSV).
            base_name: Nombre base del archivo.
            
        Returns:
            Ruta al archivo local (CSV de respaldo) o Path vacio si solo GSheet.
        """
        output_dir = Path(output_dir)
        
        if not self.enabled or not self.client:
            logger.warning("Google Sheets no disponible, exportando a CSV")
            return self._fallback_to_csv(data, output_dir, base_name)
        
        if not data:
            logger.warning("No hay datos para exportar a Google Sheets")
            return output_dir / f"{base_name}_gsheet.csv"
        
        try:
            # Obtener o crear spreadsheet
            spreadsheet = self._get_or_create_spreadsheet()
            
            # Obtener o crear worksheet
            worksheet = self._get_or_create_worksheet(spreadsheet)
            
            # Preparar datos para GSheet
            headers, rows = self._prepare_data(data)
            
            # Limpiar worksheet existente
            worksheet.clear()
            
            # Escribir datos
            all_data = [headers] + rows
            worksheet.update('A1', all_data)
            
            # Aplicar formato basico
            self._apply_formatting(worksheet, len(headers), len(rows))
            
            logger.info(
                f"Datos exportados a Google Sheets: "
                f"{self.spreadsheet_name}/{self.worksheet_name} "
                f"({len(data)} filas)"
            )
            
            # Tambien crear CSV local como respaldo
            csv_path = self._fallback_to_csv(data, output_dir, f"{base_name}_backup")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"Error exportando a Google Sheets: {e}")
            logger.info("Usando fallback a CSV")
            return self._fallback_to_csv(data, output_dir, base_name)
    
    def _get_or_create_spreadsheet(self) -> "gspread.Spreadsheet":
        """Obtiene o crea el spreadsheet."""
        try:
            spreadsheet = self.client.open(self.spreadsheet_name)
            logger.debug(f"Spreadsheet encontrado: {self.spreadsheet_name}")
        except gspread.SpreadsheetNotFound:
            spreadsheet = self.client.create(self.spreadsheet_name)
            logger.info(f"Spreadsheet creado: {self.spreadsheet_name}")
        
        return spreadsheet
    
    def _get_or_create_worksheet(
        self, 
        spreadsheet: "gspread.Spreadsheet"
    ) -> "gspread.Worksheet":
        """Obtiene o crea el worksheet."""
        try:
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            logger.debug(f"Worksheet encontrado: {self.worksheet_name}")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=self.worksheet_name,
                rows=1000,
                cols=26
            )
            logger.info(f"Worksheet creado: {self.worksheet_name}")
        
        return worksheet
    
    def _prepare_data(
        self, 
        data: List[Dict[str, Any]]
    ) -> tuple:
        """
        Prepara datos para Google Sheets.
        
        Returns:
            Tupla (headers, rows).
        """
        if not data:
            return [], []
        
        # Obtener todos los headers
        headers = []
        seen = set()
        for row in data:
            for key in row.keys():
                if key not in seen and not key.startswith("_"):
                    headers.append(key)
                    seen.add(key)
        
        # Convertir filas
        rows = []
        for row in data:
            row_values = []
            for header in headers:
                value = row.get(header)
                row_values.append(self._convert_value(value))
            rows.append(row_values)
        
        return headers, rows
    
    def _convert_value(self, value: Any) -> Any:
        """
        Convierte valores para compatibilidad con Google Sheets.
        
        Args:
            value: Valor a convertir.
            
        Returns:
            Valor convertido.
        """
        if value is None:
            return ""
        
        if isinstance(value, datetime):
            return value.isoformat()
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, (list, dict)):
            import json
            return json.dumps(value, ensure_ascii=False)
        
        return str(value)
    
    def _apply_formatting(
        self, 
        worksheet: "gspread.Worksheet",
        num_cols: int,
        num_rows: int
    ) -> None:
        """Aplica formato basico al worksheet."""
        try:
            # Formatear header (negrita)
            worksheet.format(
                f'A1:{chr(64 + min(num_cols, 26))}1',
                {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                }
            )
            
            # Congelar primera fila
            worksheet.freeze(rows=1)
            
        except Exception as e:
            logger.debug(f"Error aplicando formato: {e}")
    
    def _fallback_to_csv(
        self,
        data: List[Dict[str, Any]],
        output_dir: Path,
        base_name: str
    ) -> Path:
        """Fallback a exportacion CSV local."""
        from .csv_exporter import CSVExporter
        
        csv_exporter = CSVExporter()
        return csv_exporter.export(data, output_dir, base_name)
    
    @property
    def is_available(self) -> bool:
        """Indica si el exportador esta disponible y configurado."""
        return self.enabled and self.client is not None
