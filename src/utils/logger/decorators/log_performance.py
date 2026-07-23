"""
Performance Logging Decorator

Provides a decorator for automatically measuring and logging function
execution times with configurable log levels for performance monitoring.
"""

import functools
import time
from typing import Callable

from .get_logger_for_func import get_logger_for_func


def log_performance(logger_name: str = None, level: str = "debug"):
    """
    Decorator to automatically log function execution time.

    Measures and logs the execution time of decorated functions with
    millisecond precision. Supports configurable log levels to allow
    performance monitoring at different verbosity levels.

    Args:
        logger_name: Optional specific logger name to use. If None, uses the
                    function's module name as the logger name.
        level: Log level for performance messages. Supported levels:
               "debug", "info", "warning", "error". Defaults to "debug".

    Returns:
        Decorator function that wraps functions with execution time logging

    Logging Behavior:
        - Success: Logs execution time with specified level (e.g., "took 0.125s")
        - Exception: Logs execution time before failure with exception type
        - Time precision: 3 decimal places (millisecond accuracy)
        - Exceptions are re-raised after logging

    Examples:
        >>> @log_performance()
        ... def calculate_statistics(dataset):
        ...     return complex_analysis(dataset)
        # Logs at DEBUG: "calculate_statistics: took 2.347s"

        >>> @log_performance("database", "info")
        ... def expensive_query():
        ...     return db.execute_complex_query()
        # Logs at INFO: "expensive_query: took 5.123s"

        >>> @log_performance(level="warning")  
        ... def slow_operation():
        ...     time.sleep(1)
        ...     raise ValueError("Something went wrong")
        # Logs at WARNING: "slow_operation: failed after 1.002s with ValueError"

    Use Cases:
        - Performance monitoring and optimization
        - Identifying slow functions in production
        - Debugging performance regressions  
        - Monitoring database query execution times
        - API endpoint response time tracking

    Note:
        For simple function tracing without timing, use @log_function_calls().
        For I/O operations, consider combining with @log_file_operations().
        Time measurement uses time.time() which is suitable for most use cases
        but may not be monotonic on all systems.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_func(logger_name, func)
            log_method = getattr(logger, level.lower())

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                log_method(f"{func.__name__}: took {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log_method(f"{func.__name__}: failed after {elapsed:.3f}s with {type(e).__name__}")
                raise

        return wrapper

    return decorator
