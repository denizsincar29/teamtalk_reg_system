"""Logging configuration for the TeamTalk Registration System.

This module sets up logging with separate files for:
- All logs: teamtalk.log
- Critical errors and exceptions: teamtalk_errors.log
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Log directory
LOG_DIR = Path(__file__).parent.parent / "logs"

# Log file names
MAIN_LOG_FILE = LOG_DIR / "teamtalk.log"
ERROR_LOG_FILE = LOG_DIR / "teamtalk_errors.log"

# Max log file size (10 MB)
MAX_LOG_SIZE = 10 * 1024 * 1024
# Number of backup files to keep
BACKUP_COUNT = 5


def setup_logging() -> logging.Logger:
    """Set up logging configuration with separate error log file.
    
    Returns:
        The configured root logger.
    """
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(exist_ok=True)
    
    # Create root logger
    logger = logging.getLogger("teamtalk")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # Main log file handler (DEBUG and above)
    main_file_handler = RotatingFileHandler(
        MAIN_LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    main_file_handler.setLevel(logging.DEBUG)
    main_file_handler.setFormatter(log_format)
    logger.addHandler(main_file_handler)
    
    # Error log file handler (ERROR and above)
    error_file_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(log_format)
    logger.addHandler(error_file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger with the given name.
    
    Args:
        name: The name for the child logger (e.g., 'admin', 'bot').
        
    Returns:
        A child logger.
    """
    return logging.getLogger(f"teamtalk.{name}")


# Initialize logging on module import
logger = setup_logging()
