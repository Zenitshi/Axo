"""
Simple logging utility for Axo application.
Provides rotating file logging to prevent disk space issues.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(logging_config=None):
    """
    Set up logging with rotating file handler.

    Args:
        logging_config: Dictionary with logging configuration
    """
    # Default configuration
    if logging_config is None:
        logging_config = {
            "enabled": False,  # Changed default to False
            "level": "INFO",
            "max_file_size": 10*1024*1024,  # 10MB
            "backup_count": 3
        }

    # Get configuration values
    max_bytes = logging_config.get("max_file_size", 10*1024*1024)
    backup_count = logging_config.get("backup_count", 3)
    log_level_str = logging_config.get("level", "INFO").upper()

    # Convert string level to logging constant
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level = log_level_map.get(log_level_str, logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # If logging is disabled, set up minimal logging
    if not logging_config.get("enabled", True):
        # Set up basic logging but disable file output
        root_logger.setLevel(logging.WARNING)  # Only warnings and errors
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        return

    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Configure logging with rotating file handler
    log_filename = "axo.log"
    log_path = os.path.join(log_dir, log_filename)

    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )

    # Set format for file handler
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    rotating_handler.setFormatter(file_formatter)

    # Create console handler for development/debugging
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger.setLevel(log_level)

    # Add our handlers
    root_logger.addHandler(rotating_handler)
    root_logger.addHandler(console_handler)

    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with rotating file handler. Main log: {log_path}, Level: {log_level_str}")

def get_logger(name: str):
    """Get a logger instance for the given name."""
    return logging.getLogger(name)

# Global logger instance
logger = get_logger(__name__)
