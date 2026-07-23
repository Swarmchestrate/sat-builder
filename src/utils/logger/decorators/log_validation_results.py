"""
Validation Results Logging Decorator

Provides a decorator for automatically logging validation function results
with intelligent handling of boolean returns and exception-based validation.
"""

import functools
from typing import Callable

from .get_logger_for_func import get_logger_for_func


def log_validation_results(logger_name: str = None):
    """
    Decorator to automatically log validation function results.

    Provides comprehensive logging for validation functions with intelligent
    handling of different validation patterns including boolean returns and
    exception-based validation. Logs validation attempts, results, and failures
    with appropriate detail levels.

    Args:
        logger_name: Optional specific logger name to use. If None, uses the
                    function's module name as the logger name.

    Returns:
        Decorator function that wraps validation functions with result logging

    Logging Behavior:
        - Entry: DEBUG level "validating" message
        - Boolean result: DEBUG level "validation passed/failed" based on return value
        - Non-boolean result: DEBUG level "validated" message (assumes success)
        - Exception: WARNING level with exception type and message
        - Exceptions are re-raised after logging

    Examples:
        >>> @log_validation_results()
        ... def validate_email(email: str) -> bool:
        ...     return "@" in email and "." in email
        # Success: "validate_email: validating" → "validate_email: validation passed"
        # Failure: "validate_email: validating" → "validate_email: validation failed"

        >>> @log_validation_results("schema")
        ... def validate_user_data(data: dict):
        ...     if not data.get("name"):
        ...         raise ValueError("Missing required field: name")
        ...     return data  # Returns validated data
        # Success: "validate_user_data: validating" → "validate_user_data: validated"
        # Exception: "validate_user_data: validating" → WARNING: "validation failed with ValueError: Missing required field: name"

        >>> @log_validation_results()
        ... def check_permissions(user, resource) -> bool:
        ...     return user.has_permission(resource)
        # Logs boolean validation result as passed/failed

    Validation Patterns Supported:
        - Boolean validators: Functions returning True/False for valid/invalid
        - Exception validators: Functions that raise exceptions on invalid input
        - Transform validators: Functions that return validated/transformed data
        - Void validators: Functions that validate but return None

    Note:
        This decorator is specifically designed for validation functions.
        For general function logging, use @log_function_calls().
        The WARNING level for exceptions helps distinguish validation failures
        from unexpected errors in log analysis.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_func(logger_name, func)
            try:
                logger.debug(f"{func.__name__}: validating")
                result = func(*args, **kwargs)

                if isinstance(result, bool):
                    status = "passed" if result else "failed"
                    logger.debug(f"{func.__name__}: validation {status}")
                else:
                    logger.debug(f"{func.__name__}: validated")

                return result
            except Exception as e:
                logger.warning(f"{func.__name__}: validation failed with {type(e).__name__}: {str(e)}")
                raise

        return wrapper

    return decorator
