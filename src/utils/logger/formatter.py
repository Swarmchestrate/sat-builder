"""
Custom Log Formatters

This module provides log formatters for different logging scenarios.
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict


class LogColoredFormatter(logging.Formatter):
    """
    Colored console log formatter for enhanced development experience.

    Adds ANSI color codes to log messages based on their severity level.
    Colors automatically disabled when output is redirected or terminal
    doesn't support ANSI colors.
    """

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'  # Reset
    }

    def __init__(self, fmt: str, datefmt: str, use_colors: bool = True):
        """Initialize the colored formatter."""
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and self._terminal_supports_colors()

    def _terminal_supports_colors(self) -> bool:
        """Detect if the current terminal supports ANSI colors."""
        import sys
        import os

        if not hasattr(sys.stderr, 'isatty') or not sys.stderr.isatty():
            return False

        term = os.environ.get('TERM', '')
        if term in ('dumb', 'unknown'):
            return False

        if 'color' in term or term in ('xterm', 'xterm-256color', 'screen'):
            return True

        return True

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with appropriate colors."""
        if not self.use_colors:
            return super().format(record)

        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        original_levelname = record.levelname
        record.levelname = f"{color}{record.levelname}{reset}"

        try:
            formatted_message = super().format(record)
        finally:
            record.levelname = original_levelname

        return formatted_message


class LogJSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging and log aggregation.

    Converts log records into structured JSON format for production logging.
    """

    def __init__(self, include_extra_fields: bool = True):
        """Initialize the JSON formatter."""
        super().__init__()
        self.include_extra_fields = include_extra_fields

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as structured JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add process information if available
        if hasattr(record, 'process') and record.process:
            log_data["process"] = record.process

        if hasattr(record, 'processName') and record.processName:
            log_data["process_name"] = record.processName

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self._format_exception_info(record.exc_info)

        # Add stack information if available
        if hasattr(record, 'stack_info') and record.stack_info:
            log_data["stack_info"] = record.stack_info

        # Include extra fields if enabled
        if self.include_extra_fields:
            extra_fields = self._extract_extra_fields(record)
            if extra_fields:
                log_data["extra"] = extra_fields

        return json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))

    def _format_exception_info(self, exc_info) -> Dict[str, Any]:
        """Format exception information into a structured dictionary."""
        exc_type, exc_value, exc_traceback = exc_info

        return {
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": str(exc_value) if exc_value else "",
            "module": exc_type.__module__ if exc_type else "",
            "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback)
        }

    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract custom fields from log record."""
        standard_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'message', 'taskName'
        }

        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith('_'):
                extra_fields[key] = value

        return extra_fields
