"""
Custom Logging Handlers

This module provides specialized logging handlers that extend the standard Python
logging capabilities with features for operational requirements.

Key Features:
- Enhanced rotating file handler with automatic headers
- Asynchronous file handler for high-throughput scenarios
- Memory handler for testing and debugging
- Filtered file handler for custom log routing
"""

import logging
import os
import queue
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from src.models.settings import get_service_settings


class LogRotatingFileHandlerWithHeader(RotatingFileHandler):
    """
    Enhanced rotating file handler that adds informative headers to log files.

    Automatically adds headers to new log files and after rotation, providing
    context about when logging sessions started and system information.
    """

    def __init__(
            self,
            filename: Union[str, Path],
            mode: str = 'a',
            maxBytes: int = 0,
            backupCount: int = 0,
            encoding: Optional[str] = None,
            delay: bool = False,
            custom_header: Optional[str] = None
    ):
        """Initialize the enhanced rotating file handler."""
        super().__init__(str(filename), mode, maxBytes, backupCount, encoding, delay)
        self.header_written = False
        self.custom_header = custom_header
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record, ensuring header is written for new files."""
        # Always emit the record first
        super().emit(record)

        # Now handle header writing if needed (after emit)
        with self._lock:
            if not self.header_written and self.stream:
                try:
                    self._write_header()
                    self.header_written = True
                except Exception:
                    pass

    def doRollover(self) -> None:
        """Perform log file rotation and reset header tracking."""
        super().doRollover()
        self.header_written = False

    def _write_header(self) -> None:
        """Write an informative header to the log file."""
        if not self.stream:
            return

        try:
            if self.custom_header:
                header = self.custom_header
            else:
                header = self._generate_standard_header()

            self.stream.write(header)
            self.stream.flush()

        except Exception:
            # Silently handle header writing errors
            pass

    def _generate_standard_header(self) -> str:
        """Generate a standard informative header for log files."""
        separator = "=" * 80
        timestamp = datetime.now().isoformat()

        try:
            hostname = os.environ.get('HOSTNAME', 'unknown')
            user = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
            pid = os.getpid()
        except Exception:
            hostname = user = 'unknown'
            pid = 0

        service_name = get_service_settings().name
        header = f"\n{separator}\n"
        header += f"{service_name} - Log Session Started\n"
        header += f"Timestamp: {timestamp}\n"
        header += f"Host: {hostname}\n"
        header += f"User: {user}\n"
        header += f"Process ID: {pid}\n"
        header += f"Log File: {self.baseFilename}\n"
        header += separator + "\n\n"

        return header


class LogAsyncFileHandler(logging.Handler):
    """
    Asynchronous file handler for high-performance, non-blocking logging.

    Queues log messages in memory and writes them to disk asynchronously,
    preventing logging operations from blocking the main application threads.
    """

    def __init__(
            self,
            filename: Union[str, Path],
            maxsize: int = 1000,
            flush_interval: float = 1.0,
            encoding: str = 'utf-8'
    ):
        """Initialize the asynchronous file handler."""
        super().__init__()
        self.filename = Path(filename)
        self.maxsize = maxsize
        self.flush_interval = flush_interval
        self.encoding = encoding

        # Thread-safe queue for log messages
        self.message_queue = queue.Queue(maxsize=maxsize * 2)

        # Background thread control
        self._stop_event = threading.Event()
        self._flush_thread = None
        self._start_background_flush()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record asynchronously by adding it to the queue."""
        try:
            msg = self.format(record)

            try:
                self.message_queue.put_nowait(msg)
            except queue.Full:
                self._force_flush()
                try:
                    self.message_queue.put_nowait(msg)
                except queue.Full:
                    # Drop message to prevent blocking
                    pass

        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        """Flush all queued messages to disk immediately."""
        self._force_flush()

    def close(self) -> None:
        """Close the handler and clean up resources."""
        self._stop_event.set()

        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)

        self._force_flush()
        super().close()

    def _start_background_flush(self) -> None:
        """Start the background thread for periodic flushing."""
        self._flush_thread = threading.Thread(
            target=self._background_flush_worker,
            name=f"AsyncFileHandler-{self.filename.name}",
            daemon=True
        )
        self._flush_thread.start()

    def _background_flush_worker(self) -> None:
        """Background thread worker that periodically flushes queued messages."""
        while not self._stop_event.is_set():
            try:
                if self._stop_event.wait(self.flush_interval):
                    break

                self._flush_batch()

            except Exception:
                pass

        self._flush_batch()

    def _flush_batch(self) -> None:
        """Flush a batch of messages from the queue to disk."""
        if self.message_queue.empty():
            return

        messages = []
        try:
            while True:
                try:
                    message = self.message_queue.get_nowait()
                    messages.append(message)
                except queue.Empty:
                    break
        except Exception:
            return

        if messages:
            self._write_messages(messages)

    def _force_flush(self) -> None:
        """Force an immediate flush of all queued messages."""
        self._flush_batch()

    def _write_messages(self, messages: list) -> None:
        """Write a list of messages to the log file."""
        try:
            self.filename.parent.mkdir(parents=True, exist_ok=True)

            with open(self.filename, 'a', encoding=self.encoding) as f:
                for message in messages:
                    f.write(message + '\n')
                f.flush()

        except Exception:
            pass


class LogMemoryHandler(logging.Handler):
    """
    In-memory log handler for testing and debugging scenarios.

    Stores log records in memory rather than writing them to disk or console,
    making it useful for testing logging behavior or capturing logs for analysis.
    """

    def __init__(self, capacity: int = 1000):
        """Initialize the memory handler."""
        super().__init__()
        self.capacity = capacity
        self.records = []
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        """Store a log record in memory."""
        with self._lock:
            self.records.append(record)

            if len(self.records) > self.capacity:
                self.records.pop(0)

    def get_records(self, level: Optional[int] = None) -> list:
        """Get stored log records, optionally filtered by level."""
        with self._lock:
            if level is None:
                return self.records.copy()
            else:
                return [r for r in self.records if r.levelno >= level]

    def clear(self) -> None:
        """Clear all stored log records."""
        with self._lock:
            self.records.clear()

    def get_messages(self, level: Optional[int] = None) -> list:
        """Get formatted log messages, optionally filtered by level."""
        records = self.get_records(level)
        return [self.format(record) for record in records]

    def __len__(self) -> int:
        """Return the number of stored records."""
        return len(self.records)


class LogFilteredFileHandler(LogRotatingFileHandlerWithHeader):
    """
    File handler that applies custom filtering to log records.

    Extends the enhanced rotating file handler to support custom filtering
    logic for sophisticated log routing based on record content or metadata.
    """

    def __init__(self, *args, filter_func=None, **kwargs):
        """Initialize the filtered file handler."""
        super().__init__(*args, **kwargs)
        self.filter_func = filter_func

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record only if it passes the filter."""
        # Apply filter first - return early if filtered out
        if self.filter_func:
            try:
                if not self.filter_func(record):
                    return
            except Exception:
                # If filter function raises exception, skip the record
                return

        # If it passes the filter, use parent's emit method
        super().emit(record)
