"""
Function Calls Logging Decorator

Provides a decorator for automatically logging function entry and exit
points with exception handling for comprehensive execution tracing.
"""

import functools
from typing import Callable

from .get_logger_for_func import get_logger_for_func


def log_function_calls(logger_name: str = None):
    """
    Decorator to automatically log function entry and exit.

    Provides comprehensive function execution logging including entry, successful
    completion, and exception handling. Useful for debugging complex call chains
    and monitoring application flow.

    Args:
        logger_name: Optional specific logger name to use. If None, uses the
                    function's module name as the logger name.

    Returns:
        Decorator function that wraps functions with entry/exit logging

    Logging Behavior:
        - Entry: DEBUG level "function started" message
        - Success: DEBUG level "function finished" message
        - Exception: DEBUG level "function failed with ExceptionType" message
        - Exceptions are re-raised after logging

    Examples:
        >>> @log_function_calls()
        ... def calculate_total(items):
        ...     return sum(item.price for item in items)
        # Logs: "calculate_total: function started"
        # Logs: "calculate_total: function finished"

        >>> @log_function_calls("business_logic")
        ... def process_order(order_data):
        ...     if not order_data:
        ...         raise ValueError("Empty order data")
        ...     return create_order(order_data)
        # Success case:
        # Logs: "process_order: function started"
        # Logs: "process_order: function finished"
        #
        # Exception case:
        # Logs: "process_order: function started"
        # Logs: "process_order: function failed with ValueError"

    Use Cases:
        - Debugging complex call chains and execution flow
        - Monitoring function entry/exit patterns
        - Tracking function execution in distributed systems
        - Development and testing trace logging
        - Identifying functions that raise exceptions

    Note:
        This is the most basic execution logging decorator. For performance
        monitoring, use @log_performance(). For specific operation types,
        use specialized decorators like @log_file_operations() or @log_api_calls().
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_func(logger_name, func)
            logger.debug(f"{func.__name__}: function started")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__}: function finished")
                return result
            except Exception as e:
                logger.debug(f"{func.__name__}: function failed with {type(e).__name__}")
                raise

        return wrapper

    return decorator
