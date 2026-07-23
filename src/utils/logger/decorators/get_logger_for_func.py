"""
Logger Resolution Utility for Decorators

Provides helper functionality to resolve the appropriate logger instance
for decorated functions based on their module context and optional naming.
"""

from typing import Callable

from src.utils.logger.logger import get_logger


def get_logger_for_func(logger_name: str, func: Callable):
    """
    Get the appropriate logger instance for a decorated function.

    Resolves logger names intelligently based on function context, handling
    special cases like __main__ module execution and providing clean logger
    names by stripping common prefixes.

    Args:
        logger_name: Optional specific logger name to use. If provided,
                    returns a logger with this exact name.
        func: The function being decorated, used to extract module information
              for automatic logger naming when logger_name is None.

    Returns:
        Logger instance configured with the appropriate name

    Behavior:
        - If logger_name is provided: Returns logger with that exact name
        - If logger_name is None: Uses function's module name with these rules:
            * Handles __main__ module specially (tries to get real module name)
            * Strips 'src.' prefix for cleaner logger names
            * Falls back to module name if __spec__ is unavailable

    Examples:
        >>> def my_function(): pass
        >>> logger = get_logger_for_func("custom", my_function)
        # Returns logger named "custom"

        >>> def my_function(): pass  # in module src.models.user
        >>> logger = get_logger_for_func(None, my_function)
        # Returns logger named "models.user"

        >>> # When run as script (__main__ module)
        >>> def my_function(): pass
        >>> logger = get_logger_for_func(None, my_function)
        # Returns logger with real module name if available, or "__main__"
    """
    if logger_name is not None:
        return get_logger(logger_name)
    else:
        # Always use the actual function's module, never the calling context
        module_name = func.__module__

        # Handle __main__ module specially - when script is run directly
        if module_name == '__main__':
            # Try to get the real module name from __spec__
            import sys
            if hasattr(sys.modules[module_name], '__spec__') and sys.modules[module_name].__spec__:
                spec_name = sys.modules[module_name].__spec__.name
                if spec_name and spec_name != '__main__':
                    module_name = spec_name

        # Strip 'src.' prefix for cleaner logger names
        if module_name.startswith('src.'):
            module_name = module_name[4:]

        return get_logger(module_name)
