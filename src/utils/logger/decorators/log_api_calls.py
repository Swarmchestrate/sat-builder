"""
API Calls Logging Decorator

Provides a decorator for automatically logging API endpoint calls with
request and response information, including structured logging data
for access log analysis.
"""

import functools
from typing import Callable

from .get_logger_for_func import get_logger_for_func


def log_api_calls(logger_name: str = None):
    """
    Decorator to automatically log API endpoint calls with request info.

    Logs API endpoint invocations and responses with structured data that
    automatically routes to access logs via extra fields. Provides consistent
    logging format for API monitoring and debugging.

    Args:
        logger_name: Optional specific logger name to use. If None, uses the
                    function's module name as the logger name.

    Returns:
        Decorator function that wraps API endpoint functions with call logging

    Logging Behavior:
        - Entry: INFO level with endpoint path and handler name
        - Success: INFO level with completion message  
        - Failure: ERROR level with exception type
        - Includes structured data (endpoint, handler) for access log routing

    Examples:
        >>> @log_api_calls()
        ... def get_user(user_id: int):
        ...     return {"id": user_id, "name": "John"}
        # Logs: "API endpoint get_user called" (with extra data)
        # Logs: "API endpoint get_user responded"

        >>> @log_api_calls("api")
        ... def create_post(data):
        ...     raise ValueError("Invalid data")
        # Logs: "API endpoint create_post called"
        # Logs: "API endpoint create_post failed: ValueError"

    Note:
        The extra fields (endpoint, handler) are automatically picked up
        by the logging system for routing to access logs, enabling separate
        tracking of API usage patterns.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_func(logger_name, func)
            logger.info(f"API endpoint {func.__name__} called", extra={
                "endpoint": f"/{func.__name__}",
                "handler": func.__name__
            })

            try:
                result = func(*args, **kwargs)
                logger.info(f"API endpoint {func.__name__} responded")
                return result
            except Exception as e:
                logger.error(f"API endpoint {func.__name__} failed: {type(e).__name__}")
                raise

        return wrapper

    return decorator
