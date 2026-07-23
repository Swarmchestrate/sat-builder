"""
Logger Utilities

Main logger configuration and initialization module providing centralized
logging functionality with automatic module detection and debug mode support.
Integrates with application settings for consistent logging across the project.
"""
import logging
from typing import Optional, Union

from src.models.settings import get_logger_settings, get_service_settings
from .debug import LazyDebugLogger, set_debug_mode_active
from .setup import setup_logger

# Global flag to track logger initialization state
_logger_initialized = False


def get_logger(name: Optional[str] = None) -> Union[logging.Logger, LazyDebugLogger]:
    """
    Get a logger instance with an optional name specification.

    Returns either a standard logger (when the name is provided) or a LazyDebugLogger
    (when no name is provided) that automatically detects the calling module
    in debug mode for enhanced debugging capabilities.

    Args:
        name: Optional specific logger name. If provided, returns a standard
              logger with the format "{service_id}.{name}". If None, returns
              a LazyDebugLogger for automatic module detection.

    Returns:
        Union[logging.Logger, LazyDebugLogger]: Logger instance configured
        according to application settings.

    Example:
        >>> logger = get_logger() # Returns LazyDebugLogger
        >>> named_logger = get_logger("api") # Returns standard logger
    """
    global _logger_initialized

    # Get service identifier from application settings
    service_id = get_service_settings().id

    # Initialize logger configuration on first use
    if not _logger_initialized:
        config = get_logger_settings()
        setup_logger(config, service_id)

        # Enable debug mode if configured
        if config.level.upper() == 'DEBUG':
            set_debug_mode_active(True)

        _logger_initialized = True

    # Return appropriate logger type based on name parameter
    if name:
        # Return standard logger with specific name
        return logging.getLogger(f"{service_id}.{name}")
    else:
        # Return lazy logger with automatic module detection
        return LazyDebugLogger(service_id)


def enable_debug_mode() -> logging.Logger:
    """
    Enable debug mode for the logging system.

    Activates debug-level logging across all handlers (except error-only handlers)
    and enables the debug mode flag for LazyDebugLogger instances to provide
    enhanced module-specific logging.

    Returns:
        logging.Logger: The main service logger configured for debug level.

    Example:
        >>> debug_logger = enable_debug_mode()
        >>> debug_logger.debug("Debug mode now active")
    """
    # Activate debug mode flag for LazyDebugLogger instances
    set_debug_mode_active(True)

    # Get main service logger
    service_id = get_service_settings().id
    logger = logging.getLogger(service_id)

    # Set debug level on main logger
    logger.setLevel(logging.DEBUG)

    # Update all handlers to debug level (except error-only handlers)
    for handler in logger.handlers:
        # Skip error-only log files to maintain separate error logging
        if 'error.log' not in str(getattr(handler, 'baseFilename', '')):
            handler.setLevel(logging.DEBUG)

    return logger
