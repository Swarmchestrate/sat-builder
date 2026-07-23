"""
File Operations Logging Decorator

Provides a decorator that automatically detects and logs various file operations
including JSON, YAML, CSV, Pandas data operations, XML processing, and general
file I/O operations through static source code analysis.
"""

import functools
import inspect
from functools import lru_cache
from typing import Callable, List

from .get_logger_for_func import get_logger_for_func


@lru_cache(maxsize=128)
def _get_operation_types(func_module: str, func_name: str) -> List[str]:
    """
    Cache operation type detection - returns list since function can do multiple operations.

    Analyzes function source code to identify file operation patterns and caches
    the results for performance. Supports detection of multiple operation types
    within a single function.

    Args:
        func_module: Module name where the function is defined
        func_name: Name of the function to analyze

    Returns:
        List of operation type strings (e.g., ["saving JSON", "writing file"])
        Falls back to ["file operation"] if no specific operations are detected

    Examples:
        >>> _get_operation_types("mymodule", "save_config")
        ["saving JSON", "writing file"]
        >>> _get_operation_types("mymodule", "process_data")
        ["loading CSV", "saving data"]
    """
    operations = []
    try:
        # Get function from module and name
        import importlib
        module = importlib.import_module(func_module)
        func = getattr(module, func_name)
        source = inspect.getsource(func)

        # JSON operations
        if any(pattern in source for pattern in ['json.dump(', 'json.dumps(']):
            operations.append("dumping JSON")
        if any(pattern in source for pattern in ['json.load(', 'json.loads(']):
            operations.append("loading JSON")

        # YAML operations
        if any(pattern in source for pattern in ['yaml.dump(', 'yaml.safe_dump(', 'yaml.dump_all(']):
            operations.append("saving YAML")
        if any(pattern in source for pattern in ['yaml.load(', 'yaml.safe_load(', 'yaml.full_load(', 'yaml.load_all(']):
            operations.append("loading YAML")

        # Pickle operations
        if 'pickle.dump(' in source:
            operations.append("saving pickle")
        if 'pickle.load(' in source:
            operations.append("loading pickle")

        # CSV operations
        if any(pattern in source for pattern in ['csv.writer(', 'csv.DictWriter(']):
            operations.append("writing CSV")
        if any(pattern in source for pattern in ['csv.reader(', 'csv.DictReader(']):
            operations.append("reading CSV")

        # Pandas operations
        if any(pattern in source for pattern in ['.to_csv(', '.to_excel(', '.to_json(', '.to_parquet(', '.to_pickle(']):
            operations.append("saving data")
        if any(pattern in source for pattern in
               ['pd.read_csv(', 'pd.read_excel(', 'pd.read_json(', 'pd.read_parquet(', 'pd.read_pickle(']):
            operations.append("loading data")

        # XML operations
        if any(pattern in source for pattern in ['xml.etree', 'lxml', 'BeautifulSoup']):
            operations.append("XML processing")

        # Config operations
        if any(pattern in source for pattern in ['configparser', 'ConfigParser', '.ini']):
            operations.append("config file")

        # File operations (check last to avoid overriding specific types)
        if 'with open(' in source:
            if any(mode in source for mode in ['"w"', "'w'", 'mode="w"', "mode='w'"]):
                operations.append("writing file")
            if any(mode in source for mode in ['"r"', "'r'", 'mode="r"', "mode='r'"]):
                operations.append("reading file")
            if any(mode in source for mode in ['"a"', "'a'", 'mode="a"', "mode='a'"]):
                operations.append("appending file")

    except Exception:
        # Silently handle any import, inspection, or analysis errors
        pass

    return operations if operations else ["file operation"]


def log_file_operations(logger_name: str = None):
    """
    Decorator to automatically log file operations with intelligent operation detection.

    Uses static source code analysis to identify the types of file operations
    performed by the decorated function and logs appropriate messages. Supports
    detection of multiple operation types within a single function.

    Detected operation types include:
    - JSON operations (save/load)
    - YAML operations (save/load)
    - Pickle operations (save/load)
    - CSV operations (read/write)
    - Pandas data operations (save/load)
    - XML processing
    - Config file operations
    - General file I/O (read/write/append)

    Args:
        logger_name: Optional specific logger name to use. If None, uses the
                    function's module name as the logger name.

    Returns:
        Decorator function that wraps the target function with file operation logging

    Examples:
        >>> @log_file_operations()
        ... def save_config(data, filename):
        ...     with open(filename, 'w') as f:
        ...         json.dump(data, f)
        # Logs: "save_config: saving JSON + writing file"

        >>> @log_file_operations("config")
        ... def load_settings():
        ...     return yaml.safe_load(open('settings.yml'))
        # Logs: "load_settings: loading YAML + reading file"
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger_for_func(logger_name, func)

            operations = _get_operation_types(func.__module__, func.__name__)
            operation_text = " + ".join(operations)

            logger.debug(f"{func.__name__}: {operation_text}")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__}: {operation_text} completed")
                return result
            except Exception as e:
                logger.debug(f"{func.__name__}: {operation_text} failed with {type(e).__name__}")
                raise

        return wrapper

    return decorator
