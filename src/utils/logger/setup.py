"""
Logging Setup and Configuration

Core logging setup functionality that configures handlers, formatters,
and log destinations based on LoggingSettings configuration.

Features:
- Multiple log destinations (console, file, error, access logs)
- File rotation with size limits and backup counts
- Flexible formatting (text or JSON)
- Colored console output for development
- Directory auto-creation for log files
- Filtered access log handler for intelligent log routing
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .formatter import LogColoredFormatter, LogJSONFormatter
from .handlers import LogRotatingFileHandlerWithHeader, LogFilteredFileHandler

if TYPE_CHECKING:
    from src.models.settings import LoggingSettings


def setup_logger(config: 'LoggingSettings', service_id: str = "my_app") -> logging.Logger:
    """
    Set up and configure the application logger with handlers and formatters.

    Args:
        config: LoggingSettings instance with all logging configuration
        service_id: Root logger name (from service settings)

    Returns:
        logging.Logger: Fully configured logger instance

    Raises:
        OSError: If log directories cannot be created
        ValueError: If log level is invalid
    """
    logger = logging.getLogger(service_id)

    # Prevent duplicate configuration if logger already has handlers
    if logger.handlers:
        return logger

    # Convert string log level to logging module constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = level_map.get(config.level.upper(), logging.INFO)

    # Configure the root logger
    logger.setLevel(log_level)
    logger.propagate = False

    # Console handler setup
    if config.to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if config.use_colors:
            console_formatter = LogColoredFormatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            console_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler setup
    if config.to_file:
        main_log_path = Path(config.file_path)
        main_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Main log file handler
        main_file_handler = LogRotatingFileHandlerWithHeader(
            filename=main_log_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count
        )
        main_file_handler.setLevel(log_level)

        if config.json_format:
            main_file_formatter = LogJSONFormatter()
        else:
            main_file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        main_file_handler.setFormatter(main_file_formatter)
        logger.addHandler(main_file_handler)

        # Separate error log handler
        if config.separate_error_log:
            error_log_path = Path(config.error_file_path)
            error_log_path.parent.mkdir(parents=True, exist_ok=True)

            error_file_handler = LogRotatingFileHandlerWithHeader(
                filename=error_log_path,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count
            )
            error_file_handler.setLevel(logging.ERROR)

            if config.json_format:
                error_file_formatter = LogJSONFormatter()
            else:
                error_file_formatter = logging.Formatter(
                    fmt="%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )

            error_file_handler.setFormatter(error_file_formatter)
            logger.addHandler(error_file_handler)

        # Separate access log handler with intelligent filtering
        if config.separate_access_log:
            access_log_path = Path(config.access_file_path)
            access_log_path.parent.mkdir(parents=True, exist_ok=True)

            # Filter function to identify access-related log messages
            def access_filter(record):
                """Filter function to identify access-related log messages."""
                # Check if message contains access keywords
                message = record.getMessage().lower()
                access_keywords = [
                    'access:', 'request', 'response', 'http', 'api', 'login', 'logout',
                    'download', 'upload', 'authentication', 'authorization', 'session',
                    'get ', 'post ', 'put ', 'delete ', 'patch ', 'head ', 'options'
                ]
                has_access_keywords = any(keyword in message for keyword in access_keywords)

                # Check if record has access-related extra fields
                access_fields = [
                    'method', 'endpoint', 'status_code', 'response_time_ms', 'user_id',
                    'ip_address', 'user_agent', 'session_id', 'event'
                ]
                has_access_fields = any(hasattr(record, field) for field in access_fields)

                return has_access_keywords or has_access_fields

            access_file_handler = LogFilteredFileHandler(
                filename=access_log_path,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count,
                filter_func=access_filter
            )
            access_file_handler.setLevel(logging.INFO)

            if config.json_format:
                access_file_formatter = LogJSONFormatter()
            else:
                access_file_formatter = logging.Formatter(
                    fmt="%(asctime)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )

            access_file_handler.setFormatter(access_file_formatter)
            logger.addHandler(access_file_handler)

    return logger
