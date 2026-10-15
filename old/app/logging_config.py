"""Logging configuration for the 18XX game engine.

This module provides structured logging with configurable verbosity levels
and output formats. It supports debug mode for detailed validation output
and performance tracking for complex operations.

Usage:
    from app.logging_config import setup_logging, get_logger

    # Configure logging (typically done once at startup)
    setup_logging(level='INFO', debug_mode=False)

    # Get a logger for your module
    logger = get_logger(__name__)

    # Use the logger
    logger.info("Starting stock round", extra={'player': player.name})
    logger.debug("Validating move", extra={'move_type': move.__class__.__name__})
"""

import logging
import sys
from typing import Optional, Dict, Any
import json
from datetime import datetime


# Global debug mode flag
_DEBUG_MODE = False


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured logs with context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Base log structure
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }

        # Add any extra context provided via 'extra' parameter
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # In debug mode, output as JSON for easy parsing
        if _DEBUG_MODE:
            return json.dumps(log_data)

        # In normal mode, output human-readable format
        timestamp = log_data['timestamp']
        level = log_data['level']
        module = log_data['module']
        message = log_data['message']

        # Add extra context if present
        extra_str = ""
        if hasattr(record, 'extra_data'):
            extra_items = [f"{k}={v}" for k, v in record.extra_data.items()]
            if extra_items:
                extra_str = f" [{', '.join(extra_items)}]"

        return f"{timestamp} [{level:8s}] {module:20s} - {message}{extra_str}"


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that supports context data."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log call to add context data."""
        # Extract 'extra' dict and store it for the formatter
        if 'extra' in kwargs:
            extra_data = kwargs.pop('extra')
            # Store extra data as a record attribute
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['extra_data'] = extra_data
        return msg, kwargs


def setup_logging(
    level: str = 'INFO',
    debug_mode: bool = False,
    log_file: Optional[str] = None
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        debug_mode: Enable debug mode with JSON output and detailed logging
        log_file: Optional file path to write logs to (in addition to console)
    """
    global _DEBUG_MODE
    _DEBUG_MODE = debug_mode

    # Set level to DEBUG if debug_mode is enabled
    if debug_mode:
        level = 'DEBUG'

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Log startup message
    root_logger.info(
        f"Logging configured: level={level}, debug_mode={debug_mode}, log_file={log_file}"
    )


def get_logger(name: str) -> ContextLogger:
    """Get a logger with context support.

    Args:
        name: Logger name (typically __name__)

    Returns:
        ContextLogger instance that supports context data
    """
    base_logger = logging.getLogger(name)
    return ContextLogger(base_logger, {})


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return _DEBUG_MODE


# Performance tracking utilities
class PerformanceTimer:
    """Context manager for tracking operation performance."""

    def __init__(self, logger: logging.Logger, operation: str, **context):
        """Initialize performance timer.

        Args:
            logger: Logger to use for output
            operation: Name of the operation being timed
            **context: Additional context to include in log
        """
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        """Start the timer."""
        self.start_time = datetime.now()
        self.logger.debug(
            f"Starting: {self.operation}",
            extra=self.context
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and log duration."""
        duration = (datetime.now() - self.start_time).total_seconds()

        log_data = {
            'duration_seconds': duration,
            **self.context
        }

        if exc_type is None:
            self.logger.info(
                f"Completed: {self.operation} ({duration:.3f}s)",
                extra=log_data
            )
        else:
            self.logger.error(
                f"Failed: {self.operation} ({duration:.3f}s) - {exc_val}",
                extra=log_data
            )


# Default configuration (can be overridden by calling setup_logging)
if not logging.getLogger().handlers:
    setup_logging(level='WARNING')
