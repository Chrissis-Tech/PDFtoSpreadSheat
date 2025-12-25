"""
PDF to Spreadsheet Automation - CLI Entry Point
================================================

Extrae datos estructurados de PDFs y los exporta a CSV, JSON o Google Sheets.

Uso:
    python main.py --input input/ --output output/ --format csv
"""

import sys
import os
from pathlib import Path
from datetime import datetime

import click
from loguru import logger

from src.config import load_config
from src.pipeline import Pipeline


def setup_logging(config: dict, verbose: bool = False) -> None:
    """Configura el sistema de logging."""
    log_config = config.get("logging", {})
    log_dir = Path(config.get("paths", {}).get("logs", "./logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Remover handler por defecto
    logger.remove()
    
    # Nivel de log
    level = "DEBUG" if verbose else log_config.get("level", "INFO")
    log_format = log_config.get("format", "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")
    
    # Log a consola
    if log_config.get("console", True):
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            colorize=True
        )
    
    # Log a archivo
    if log_config.get("file", True):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"run_{timestamp}.log"
        logger.add(
            str(log_file),
            format=log_format,
            level=level,
            rotation=log_config.get("rotation", "10 MB"),
            retention=log_config.get("retention", "7 days")
        )


def print_summary(results: dict) -> None:
    """Imprime el resumen de ejecucion."""
    print("\n" + "=" * 50)
    print("           RESUMEN DE EJECUCION")
    print("=" * 50)
    print(f"  PDFs procesados:    {results.get('total_files', 0):>5}")
    print(f"  Filas extraidas:    {results.get('total_rows', 0):>5}")
    print(f"  Errores:            {results.get('errors', 0):>5}")
    print(f"  Advertencias:       {results.get('warnings', 0):>5}")
    print(f"  Tiempo total:       {results.get('elapsed_time', 0):.2f}s")
    print("=" * 50)
    
    if results.get("output_file"):
        print(f"  Archivo generado: {results['output_file']}")
    
    print("=" * 50 + "\n")


@click.command()
@click.option(
    "--input", "-i",
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Ruta al PDF o directorio con PDFs"
)
@click.option(
    "--output", "-o",
    "output_path",
    required=True,
    type=click.Path(),
    help="Directorio de salida para los archivos generados"
)
@click.option(
    "--format", "-f",
    "output_format",
    type=click.Choice(["csv", "json", "gsheet"], case_sensitive=False),
    default="csv",
    help="Formato de salida (default: csv)"
)
@click.option(
    "--parser", "-p",
    type=click.Choice(["invoice", "report", "auto"], case_sensitive=False),
    default="auto",
    help="Parser a utilizar (default: auto)"
)
@click.option(
    "--config", "-c",
    "config_file",
    type=click.Path(exists=True),
    default="config.yaml",
    help="Archivo de configuracion (default: config.yaml)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Modo verbose (mas detalle en logs)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Ejecutar sin escribir archivos de salida"
)
def main(
    input_path: str,
    output_path: str,
    output_format: str,
    parser: str,
    config_file: str,
    verbose: bool,
    dry_run: bool
) -> None:
    """
    PDF to Spreadsheet Automation
    
    Extrae datos de PDFs y los convierte a formatos estructurados.
    
    Ejemplos:
    
        python main.py --input input/ --output output/ --format csv
        
        python main.py -i factura.pdf -o output/ -f json --verbose
    """
    try:
        # Cargar configuracion
        config = load_config(config_file)
        
        # Configurar logging
        setup_logging(config, verbose)
        
        logger.info("Iniciando PDF to Spreadsheet Automation")
        logger.info(f"Input: {input_path}")
        logger.info(f"Output: {output_path}")
        logger.info(f"Formato: {output_format}")
        
        # Crear directorio de salida
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar pipeline
        pipeline = Pipeline(
            config=config,
            output_format=output_format.lower(),
            parser_type=parser.lower(),
            dry_run=dry_run
        )
        
        # Procesar
        input_path_obj = Path(input_path)
        
        if input_path_obj.is_file():
            results = pipeline.process_file(input_path_obj, output_dir)
        else:
            results = pipeline.process_directory(input_path_obj, output_dir)
        
        # Mostrar resumen
        print_summary(results)
        
        # Exit code basado en errores
        if results.get("errors", 0) > 0:
            logger.warning(f"Proceso completado con {results['errors']} errores")
            sys.exit(1)
        else:
            logger.info("Proceso completado exitosamente")
            sys.exit(0)
            
    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
