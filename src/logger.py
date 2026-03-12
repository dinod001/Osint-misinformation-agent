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
    
    # Detect if running on Vercel (read-only filesystem)
    IS_VERCEL = os.environ.get("VERCEL") == "1"
    
    # Initialize the logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if the logger is already initialized
    if logger.hasHandlers():
        return logger

    # Set base logging level
    logger.setLevel(logging.INFO)

    # Define the log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Console Handler (Always enabled)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (Only if NOT on Vercel)
    if not IS_VERCEL:
        try:
            log_dir = os.path.join(BASE_DIR, params["paths"]["logs_dir"])
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            log_file = os.path.join(log_dir, "osint_misinformation_agent.log")
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=5 * 1024 * 1024, 
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback if directory creation fails for any other reason
            print(f"Warning: Could not setup file logging: {e}")

    return logger

# logger = setup_logger(__name__)
# logger.info("Logger setup complete")
