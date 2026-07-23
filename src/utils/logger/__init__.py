"""
Logger Package - Centralized Logging System

Comprehensive logging infrastructure with automatic configuration, intelligent
module detection, and specialized decorators for different operation types.
Provides centralized logging management with multiple output destinations
and structured logging support for modern Python applications.

Core Features:
- Automatic logger configuration with intelligent module detection
- LazyDebugLogger for dynamic module path resolution in debug mode
- Multiple output destinations: console, application logs, error logs, access logs
- Structured logging with JSON format support for log analysis
- Intelligent log filtering and routing based on content and context
- Performance monitoring and function execution tracing decorators
- Specialized logging decorators for different operation patterns

Logging Infrastructure:
- Console output with colored formatting for development
- File-based logging with automatic rotation and retention
- Structured JSON logging for machine-readable analysis  
- Access log separation for HTTP requests and API calls
- Error log isolation for exception tracking and debugging
- Configurable log levels and filtering rules

Basic Usage:
    >>> from src.utils.logger import get_logger
    >>> logger = get_logger()  # Returns LazyDebugLogger for module detection
    >>> logger.info("Application starting...")
    
    >>> # Named logger for specific components
    >>> api_logger = get_logger("api")
    >>> api_logger.info("API server initializing")

Debug Mode and Module Detection:
    >>> from src.utils.logger import enable_debug_mode
    >>> enable_debug_mode()  # Activates automatic module detection
    >>> logger.debug("This will show module path in debug mode")
    >>> # Output: "2024-01-01 12:00:00 - mymodule.submodule - DEBUG - Message"

Function Logging Decorators:
    >>> from src.utils.logger import log_function_calls, log_performance
    >>> 
    >>> @log_function_calls()
    >>> @log_performance()
    >>> def process_data():
    ...     return "processed"
    >>> # Automatically logs function entry, exit, and execution time

Available Logging Decorators:
- @log_function_calls(): Basic function entry/exit logging with exception handling
- @log_performance(): Execution time measurement and performance monitoring  
- @log_cache_operations(): Cache hit/miss operation logging for debugging
- @log_validation_results(): Validation function result logging with status tracking
- @log_api_calls(): API endpoint request/response logging with structured data
- @log_file_operations(): Intelligent file operation detection and logging

Log Output Destinations and Routing:
- Console: Colored output for interactive development and debugging
- app.log: Main application logs containing all messages and events
- error.log: Error-only logs with detailed stack traces and exception context
- access.log: HTTP requests, user activity, and API access (automatically filtered)

Configuration and Environment Variables:
Set logging behavior via environment variables with LOGGING__ prefix:
- LOGGING__LEVEL=DEBUG: Set global log level (DEBUG, INFO, WARNING, ERROR)
- LOGGING__TO_FILE=true: Enable/disable file output destinations
- LOGGING__JSON_FORMAT=false: Toggle structured JSON vs. text formatting
- LOGGING__CONSOLE_LEVEL=INFO: Set console-specific log level
- LOGGING__FILE_LEVEL=DEBUG: Set file-specific log level

Advanced Features:
- Automatic log rotation and archival for long-running applications
- Thread-safe logging operations for concurrent applications
- Memory-efficient logging with configurable buffer sizes
- Integration with monitoring systems via structured log formats
- Custom formatter support for specialized logging requirements

Integration Examples:
    >>> # API endpoint with comprehensive logging
    >>> @log_api_calls("api")
    >>> @log_performance(level="info")
    >>> @log_validation_results()
    >>> def create_user(user_data):
    ...     validate_user_data(user_data)
    ...     return save_user_to_database(user_data)
    
    >>> # File processing with operation detection
    >>> @log_file_operations()
    >>> @log_performance("data_processing")
    >>> def process_config_file(filename):
    ...     with open(filename) as f:
    ...         return json.load(f)
    >>> # Automatically detects and logs JSON loading operation

This logging package provides a complete solution for application logging
needs, from simple debug messages to comprehensive operational monitoring
and performance analysis in production environments.
"""

from .decorators import (
    log_function_calls,
    log_performance,
    log_cache_operations,
    log_validation_results,
    log_api_calls,
    log_file_operations
)
from .logger import get_logger, enable_debug_mode

__all__ = [
    "get_logger",
    "enable_debug_mode",
    "log_function_calls",
    "log_performance",
    "log_cache_operations",
    "log_validation_results",
    "log_api_calls",
    "log_file_operations"
]
