"""
Folder Watcher
==============

Monitors a directory for new PDF files and processes them automatically.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from loguru import logger

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog not installed. Folder watching will not be available.")

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.pipeline import Pipeline


class PDFHandler(FileSystemEventHandler):
    """Handles PDF file creation events."""
    
    def __init__(
        self,
        output_dir: str,
        config_path: str = "config.yaml",
        output_format: str = "csv",
        parser_type: Optional[str] = None,
        cooldown: int = 2
    ):
        """
        Initialize the PDF handler.
        
        Args:
            output_dir: Directory to save processed files.
            config_path: Path to configuration file.
            output_format: Output format (csv, json, xlsx).
            parser_type: Parser to use (None for auto-detect).
            cooldown: Seconds to wait before processing (allows file to finish copying).
        """
        super().__init__()
        self.output_dir = output_dir
        self.config_path = config_path
        self.output_format = output_format
        self.parser_type = parser_type
        self.cooldown = cooldown
        
        # Track processed files to avoid duplicates
        self.processed_files = set()
        
        # Load config
        self.config = load_config(config_path)
        
        logger.info(f"PDF Handler initialized. Output: {output_dir}, Format: {output_format}")
    
    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process PDF files
        if file_path.suffix.lower() != '.pdf':
            return
        
        # Skip already processed files
        if str(file_path) in self.processed_files:
            return
        
        logger.info(f"New PDF detected: {file_path.name}")
        
        # Wait for file to finish copying
        time.sleep(self.cooldown)
        
        # Process the file
        self.process_file(file_path)
    
    def process_file(self, file_path: Path):
        """Process a single PDF file."""
        try:
            logger.info(f"Processing: {file_path.name}")
            
            # Create pipeline
            pipeline = Pipeline(
                config=self.config,
                output_format=self.output_format,
                parser_type=self.parser_type,
                dry_run=False
            )
            
            # Process file
            result = pipeline.process_file(str(file_path), self.output_dir)
            
            # Mark as processed
            self.processed_files.add(str(file_path))
            
            # Log results
            logger.success(
                f"Completed: {file_path.name} - "
                f"{result.get('total_rows', 0)} rows extracted"
            )
            
            if result.get('output_file'):
                logger.info(f"Output: {result['output_file']}")
            
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")


def watch_folder(
    input_dir: str,
    output_dir: str,
    config_path: str = "config.yaml",
    output_format: str = "csv",
    parser_type: Optional[str] = None,
    recursive: bool = False
):
    """
    Watch a folder for new PDF files and process them automatically.
    
    Args:
        input_dir: Directory to watch for PDFs.
        output_dir: Directory to save processed files.
        config_path: Path to configuration file.
        output_format: Output format (csv, json, xlsx).
        parser_type: Parser to use (None for auto-detect).
        recursive: Watch subdirectories as well.
    """
    if not WATCHDOG_AVAILABLE:
        raise ImportError("watchdog is required. Install with: pip install watchdog")
    
    # Ensure directories exist
    Path(input_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create handler and observer
    handler = PDFHandler(
        output_dir=output_dir,
        config_path=config_path,
        output_format=output_format,
        parser_type=parser_type
    )
    
    observer = Observer()
    observer.schedule(handler, input_dir, recursive=recursive)
    observer.start()
    
    print()
    print("=" * 50)
    print("  PDF Folder Watcher")
    print("=" * 50)
    print()
    print(f"  Watching:  {input_dir}")
    print(f"  Output:    {output_dir}")
    print(f"  Format:    {output_format}")
    print(f"  Recursive: {recursive}")
    print()
    print("  Drop PDF files into the watched folder to process them.")
    print("  Press Ctrl+C to stop.")
    print()
    print("-" * 50)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    
    observer.join()
    print("Watcher stopped.")


def main():
    """CLI entry point for folder watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Watch a folder for new PDFs and process them automatically."
    )
    
    parser.add_argument(
        "-i", "--input",
        default="./watch",
        help="Directory to watch for PDFs (default: ./watch)"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Directory to save processed files (default: ./output)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["csv", "json", "xlsx"],
        default="csv",
        help="Output format (default: csv)"
    )
    
    parser.add_argument(
        "-p", "--parser",
        choices=["invoice", "report", "financial_report"],
        default=None,
        help="Parser to use (default: auto-detect)"
    )
    
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Watch subdirectories recursively"
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    watch_folder(
        input_dir=args.input,
        output_dir=args.output,
        config_path=args.config,
        output_format=args.format,
        parser_type=args.parser,
        recursive=args.recursive
    )


if __name__ == "__main__":
    main()
