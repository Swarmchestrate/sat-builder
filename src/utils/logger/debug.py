"""
Debug Logger Implementation

Provides LazyDebugLogger class for robust automatic module detection and debug-aware
logging functionality. This module handles dynamic logger selection based on debug
mode state and calling context using improved frame inspection techniques.

Key Features:
- Pattern-based frame detection (more robust than hardcoded strings)
- Configurable module and function patterns for extensibility
- Improved call stack traversal with reasonable depth limits
- Robust fallback mechanisms for edge cases
"""
import inspect
import logging
import os
from pathlib import Path

from src.models.settings import get_logger_settings

# Global flag to track debug mode state across all LazyDebugLogger instances
_debug_mode_active = False

# Define logger module patterns to skip - more flexible than hardcoded strings
# These patterns identify internal logging system modules that should be skipped
# during frame inspection to find the actual calling module
_LOGGER_MODULE_PATTERNS = {
    'logger', 'debug', 'decorators'  # Skip any module containing these keywords
}

# Define function name patterns that belong to the logging system
# These function names indicate internal logging operations that should be
# skipped when searching for the actual calling function
_LOGGER_FUNCTION_PATTERNS = {
    '_get_real_logger', '__getattr__', 'wrapper', 'decorator'  # Skip these function names
}


class LazyDebugLogger:
    """
    Lazy debug-aware logger that automatically detects calling module using robust frame inspection.

    This logger delays the decision of which actual logger to use until a logging method
    is called. In debug mode, it creates module-specific loggers for better debugging
    granularity. In non-debug mode, it uses a standard base logger for performance.

    The improved frame inspection uses pattern-based detection instead of hardcoded
    strings, making it more resilient to code refactoring and structural changes.

    Attributes:
        base_name: Base name for the logger (typically service identifier)
        _real_logger: Cached standard logger instance for non-debug mode
        _cached_module_name: Cached module name to avoid repeated frame inspection

    Example:
        >>> logger = LazyDebugLogger("myapp")
        >>> logger.info("This will auto-detect calling module in debug mode")
    """

    def __init__(self, base_name: str):
        """
        Initialize lazy debug logger.

        Args:
            base_name: Base name for logger, typically the service identifier.
                      Used as fallback logger name and prefix for module-specific loggers.
        """
        self.base_name = base_name
        self._real_logger = None  # Cached logger for non-debug mode
        self._cached_module_name = None  # Cache to avoid repeated frame inspection

    def _is_logger_frame(self, frame) -> bool:
        """
        Check if a frame belongs to the logging system itself using pattern matching.

        Uses configurable patterns to identify internal logging frames that should
        be skipped during module detection. This approach is more robust than
        hardcoded string matching and survives code refactoring.

        Args:
            frame: Frame object to check from the call stack

        Returns:
            bool: True if this is an internal logging frame that should be skipped

        Example:
            >>> frame = inspect.currentframe()
            >>> logger._is_logger_frame(frame)  # Returns True for logger internals
        """
        if not frame:
            return True  # Invalid frames are considered logger frames (skip them)

        # Check filename patterns - extract just the filename without path
        filename = frame.f_code.co_filename.lower()
        filename_path = Path(filename).name  # More robust than string operations

        # Skip frames from modules matching our logger patterns
        if any(pattern in filename_path for pattern in _LOGGER_MODULE_PATTERNS):
            return True

        # Check function name patterns - skip decorator wrappers and logger internals
        func_name = frame.f_code.co_name
        if func_name in _LOGGER_FUNCTION_PATTERNS:
            return True

        return False  # This frame is not part of the logging system

    def _get_module_name(self):
        """
        Extract the calling module name using robust frame inspection.

        Walks up the call stack to find the first frame that doesn't belong to the
        logging system itself. Uses pattern-based detection for reliability and
        caches the result to avoid repeated expensive frame inspection.

        Returns:
            str or None: Module name with common prefixes stripped for cleaner
                        logger names, or None if detection fails

        Algorithm:
            1. Return cached result if available (performance optimization)
            2. Walk up call stack, skipping logging system frames
            3. Extract module name from first non-logging frame
            4. Handle special cases like __main__ modules
            5. Strip common prefixes for cleaner names
            6. Cache and return result

        Example:
            >>> logger._get_module_name()
            'models.user.service'  # Detected from src.models.user.service
        """
        # Performance optimization: return cached result if available
        if self._cached_module_name:
            return self._cached_module_name

        try:
            frame = inspect.currentframe()
            max_depth = 20  # Reasonable limit to prevent infinite loops in edge cases

            # Walk up the call stack to find actual caller
            for depth in range(max_depth):
                frame = frame.f_back if frame else None

                if not frame:
                    break  # Reached top of call stack

                # Skip internal logger frames using robust pattern matching
                if self._is_logger_frame(frame):
                    continue  # Keep looking for non-logger frame

                # Found a non-logger frame - extract module information
                module_name = frame.f_globals.get('__name__', '')

                # Handle __main__ module specially (scripts run directly)
                if module_name == '__main__':
                    spec = frame.f_globals.get('__spec__')
                    if spec and spec.name:
                        module_name = spec.name  # Use actual module name if available

                # Strip common prefixes for cleaner logger names
                # This makes logger names more readable: 'user.service' vs 'src.models.user.service'
                for prefix in ['src.', '__main__.']:
                    if module_name.startswith(prefix):
                        module_name = module_name[len(prefix):]
                        break

                # Cache and return if we found a valid module name
                if module_name and module_name != '__main__':
                    self._cached_module_name = module_name
                    return module_name

        except Exception:
            # Fallback silently if frame inspection fails for any reason
            # This ensures logging continues to work even in edge cases
            pass

        return None  # Could not determine module name

    def _get_real_logger(self):
        """
        Get the appropriate logger instance based on current debug state.

        In debug mode, attempts to create a module-specific logger using frame
        inspection for granular debugging. In non-debug mode, returns a cached
        base logger for optimal performance.

        Returns:
            logging.Logger: Appropriate logger instance for the current context.
                           Either module-specific (debug) or base logger (production).

        Debug Mode Behavior:
            - Detects calling module and creates logger like 'myapp.user.service'
            - Provides granular control over logging from different modules
            - Enables easier debugging by showing exact source of log messages

        Non-Debug Mode Behavior:
            - Returns cached base logger for performance
            - All messages use the same logger name (e.g., 'myapp')
            - Minimal overhead for production use
        """
        # Check if debug mode is enabled through any configuration method
        debug_enabled = (_debug_mode_active or  # Explicit debug mode activation
                         get_logger_settings().level.upper() == 'DEBUG' or  # Config file setting
                         os.getenv('LOGGING__LEVEL', '').upper() == 'DEBUG')  # Environment variable

        if debug_enabled:
            # In debug mode, try to get module-specific logger for granular control
            module_name = self._get_module_name()
            if module_name:
                # Create hierarchical logger name: base_name.module.path
                return logging.getLogger(f"{self.base_name}.{module_name}")

        # Fallback to base logger (cached for performance in production)
        if not self._real_logger:
            self._real_logger = logging.getLogger(self.base_name)
        return self._real_logger

    def __getattr__(self, name):
        """
        Delegate attribute access to the appropriate logger instance.

        This method enables the LazyDebugLogger to behave exactly like a standard
        logging.Logger by forwarding all method calls and attribute access to the
        real logger. The magic happens transparently - users call logger.info(),
        logger.debug(), etc., and this method ensures the call reaches the right
        logger instance.

        Args:
            name: Attribute or method name being accessed (e.g., 'info', 'debug', 'error')

        Returns:
            Any: The requested attribute from the real logger instance

        Example:
            >>> logger = LazyDebugLogger("myapp")
            >>> logger.info("Hello")  # Calls __getattr__('info') -> real_logger.info("Hello")
            >>> logger.handlers      # Calls __getattr__('handlers') -> real_logger.handlers
        """
        return getattr(self._get_real_logger(), name)


def set_debug_mode_active(value: bool):
    """
    Set the global debug mode state for all LazyDebugLogger instances.

    Controls whether LazyDebugLogger instances should use module-specific loggers
    (with automatic module detection) or fall back to base loggers. This setting
    affects all existing and future LazyDebugLogger instances globally.

    Args:
        value: True to enable debug mode (module detection), False to disable

    Effects:
        - When True: All LazyDebugLoggers will attempt module detection
        - When False: All LazyDebugLoggers will use base logger for performance

    Example:
        >>> set_debug_mode_active(True)   # Enable module detection
        >>> logger.debug("This will show module path")
        >>> set_debug_mode_active(False)  # Disable for production
        >>> logger.debug("This uses base logger only")

    Note:
        This can be called at runtime to dynamically enable/disable debug features
        based on application needs or external triggers.
    """
    global _debug_mode_active
    _debug_mode_active = value
