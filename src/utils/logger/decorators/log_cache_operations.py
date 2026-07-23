"""
Cache Operations Logging Decorator

Provides a decorator for automatically logging cache-related operations
to help monitor cache usage patterns and debug caching behavior.
"""

import functools
from typing import Callable

from .get_logger_for_func import get_logger_for_func


def log_cache_operations(logger_name: str = None):
    """
    Decorator to automatically log cache hit/miss operations.

    Logs cache access patterns for functions that implement module-level
    caching, global caches, or other caching mechanisms. Useful for monitoring
    cache effectiveness and debugging cache-related issues.

    Args:
        logger_name: Optional specific logger name to use. If None, uses the
                    function's module name as the logger name.

    Returns:
        Decorator function that wraps cached functions with operation logging

    Logging Behavior:
        - Entry: DEBUG level "checking cache" message
        - Exit: DEBUG level "cache checked" message (regardless of hit/miss)
        - No exception handling (cache operations typically don't fail)

    Examples:
        >>> @log_cache_operations()
        ... def get_user_data(user_id: int):
        ...     if user_id in _cache:
        ...         return _cache[user_id]  # Cache hit
        ...     data = expensive_db_call(user_id)
        ...     _cache[user_id] = data
        ...     return data
        # Logs: "get_user_data: checking cache"
        # Logs: "get_user_data: cache checked"

        >>> @log_cache_operations("user_cache")
        ... def load_user_profile(user_id: int):
        ...     return lru_cache_function(user_id)
        # Uses "user_cache" logger for cache operation messages

    Note:
        This decorator is designed for functions that handle their own caching
        logic internally. It doesn't distinguish between cache hits and misses -
        that determination should be logged within the function itself if needed.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_func(logger_name, func)
            logger.debug(f"{func.__name__}: checking cache")

            result = func(*args, **kwargs)

            logger.debug(f"{func.__name__}: cache checked")
            return result

        return wrapper

    return decorator
