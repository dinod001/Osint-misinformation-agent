import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import params

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

def setup_logger(name: str):
    """
    Sets up a reusable logger that outputs to both a rotating file and the console.
    
    Args:
        name (str): Name of the module (e.g., 'IrrigationCollector')
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(BASE_DIR, params["paths"]["logs_dir"])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Initialize the logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if the logger is already initialized
    if logger.hasHandlers():
        return logger

    # Set base logging level (INFO captures Info, Warning, Error, and Critical)
    logger.setLevel(logging.INFO)

    # Define the log format: [Timestamp] - [Module Name] - [Level] - [Message]
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Rotating File Handler:
    # Max size 5MB per file, keeps up to 5 old log files as backups.
    log_file = os.path.join(log_dir, "osint_misinformation_agent.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5 * 1024 * 1024, 
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # 2. Console Handler:
    # Allows developers to see logs in the terminal in real-time.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Attach both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# logger = setup_logger(__name__)
# logger.info("Logger setup complete")
