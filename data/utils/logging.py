"""
Logging utilities for mod update checker.

This module provides functions for setting up and configuring logging
for the application, including console and file handlers.
"""

import os
import logging
import datetime
from typing import Optional
from pathlib import Path


# Default logging settings
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIRECTORY = "logs"


def setup_logging(
    log_dir: str = DEFAULT_LOG_DIRECTORY,
    log_level: int = DEFAULT_LOG_LEVEL,
    debug_mode: bool = False,
    console_output: bool = True
) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_dir: Directory to store log files
        log_level: Default logging level (overridden by debug_mode if True)
        debug_mode: Enable debug logging
        console_output: Enable console output
    """
    # Set root logger level
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set appropriate log level
    level = logging.DEBUG if debug_mode else log_level
    root_logger.setLevel(level)
    
    # Create formatters
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT)
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)
    
    # Set up file logging
    try:
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate log filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"mod_updater_{timestamp}.log")
        
        # Add file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
        
        logging.info(f"Logging to {log_file}")
    except (IOError, OSError) as e:
        logging.error(f"Failed to set up file logging: {str(e)}")
        logging.warning("Continuing with console logging only")
    
    # Log initial message
    if debug_mode:
        logging.debug("Debug logging enabled")
    
    logging.info(f"Logging initialized at level: {logging.getLevelName(level)}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name, typically __name__ of the calling module
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: int) -> None:
    """
    Set the log level for all handlers.
    
    Args:
        level: Logging level to set
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    for handler in root_logger.handlers:
        handler.setLevel(level)
    
    logging.info(f"Log level set to: {logging.getLevelName(level)}")


def get_log_file_path() -> Optional[str]:
    """
    Get the path to the current log file, if any.
    
    Returns:
        Path to the log file or None if no file handler is configured
    """
    root_logger = logging.getLogger()
    
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    
    return None

