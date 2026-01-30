"""
Utility functions for enhanced logging with automatic exception traceback.

This module provides a custom logging formatter that automatically includes
exception traceback information when logging ERROR or CRITICAL level messages,
even without explicitly passing exc_info=True.
"""
import logging
import sys
import traceback
from typing import Optional


class AutoTracebackFormatter(logging.Formatter):
    """
    Custom formatter that automatically includes exception traceback for ERROR and CRITICAL logs.

    This formatter enhances the standard logging behavior by:
    1. Automatically detecting if there's an active exception (even when exc_info is not passed)
    2. Including full traceback for ERROR and CRITICAL level logs
    3. Optionally forcing exc_info=True for specified log levels

    Usage:
        # In main.py or logging setup:
        from utils.logging_utils import AutoTracebackFormatter

        formatter = AutoTracebackFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(formatter)
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = '%',
        force_exc_info_for_levels: Optional[list] = None,
        always_include_traceback: bool = True
    ):
        """
        Initialize the AutoTracebackFormatter.

        Args:
            fmt: Log message format string
            datefmt: Date format string
            style: Formatter style (%, {, or $)
            force_exc_info_for_levels: List of level names that should always include exc_info
                                         (default: ['ERROR', 'CRITICAL'])
            always_include_traceback: If True, automatically include traceback when an exception
                                       is active for ERROR/CRITICAL logs
        """
        super().__init__(fmt, datefmt, style)
        self.force_exc_info_for_levels = force_exc_info_for_levels or ['ERROR', 'CRITICAL']
        self.always_include_traceback = always_include_traceback

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record, automatically adding exception info if needed.

        This method is called for each log record. It enhances the standard behavior
        by automatically detecting if there's an active exception when logging
        ERROR or CRITICAL messages, and including the full traceback.
        """
        # Check if we should force exc_info for this log level
        should_add_exc_info = (
            record.levelno >= logging.ERROR and  # ERROR or CRITICAL
            self.always_include_traceback and
            record.exc_info is None and  # Not already set
            sys.exc_info() != (None, None, None)  # There's an active exception
        )

        if should_add_exc_info:
            # Automatically capture exception info
            record.exc_info = sys.exc_info()
            # Also add exc_text to the record for formatted output
            record.exc_text = self._formatException(record.exc_info)

        # Call the parent format method
        return super().format(record)

    def _formatException(self, exc_info) -> str:
        """
        Format the exception info into a string.

        Args:
            exc_info: Exception tuple from sys.exc_info()

        Returns:
            Formatted exception traceback string
        """
        if not exc_info or exc_info == (None, None, None):
            return ''

        # Format the exception using standard traceback formatting
        tb_list = traceback.format_exception(*exc_info)
        return ''.join(tb_list)


def setup_enhanced_logging(
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    fmt: Optional[str] = None
) -> logging.Logger:
    """
    Setup enhanced logging with automatic traceback for errors.

    This is a drop-in replacement for the standard logging setup that automatically
    includes exception traceback information for ERROR and CRITICAL level logs.

    Args:
        log_file: Path to log file (if None, only console logging)
        level: Root logger level (default: DEBUG)
        fmt: Custom format string (if None, uses default)

    Returns:
        The configured root logger

    Example:
        >>> from utils.logging_utils import setup_enhanced_logging
        >>> logger = setup_enhanced_logging("app.log")
        >>> logger.info("Application started")
        >>>
        >>> # Exception logging - traceback automatically included!
        >>> try:
        ...     1 / 0
        ... except Exception:
        ...     logger.error("Division failed")  # Traceback automatically included!
    """
    # Default format if not provided
    if fmt is None:
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'

    # Create the custom formatter
    formatter = AutoTracebackFormatter(fmt)

    handlers = []

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # Add file handler if path provided
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    for handler in handlers:
        root_logger.addHandler(handler)

    return root_logger


class ExceptionCaptureAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically captures exception info for ERROR/CRITICAL logs.

    This adapter wraps a logger and automatically ensures that exception information
    is captured when logging ERROR or CRITICAL messages within an exception context.

    Example:
        >>> from utils.logging_utils import ExceptionCaptureAdapter
        >>> logger = ExceptionCaptureAdapter(logging.getLogger(__name__))
        >>>
        >>> # In exception handler
        >>> try:
        ...     risky_operation()
        ... except Exception:
        ...     logger.error("Operation failed")  # Traceback automatically captured!
    """

    def __init__(self, logger: logging.Logger, extra: Optional[dict] = None):
        """
        Initialize the adapter.

        Args:
            logger: The underlying logger to wrap
            extra: Extra context to add to all log records
        """
        super().__init__(logger, extra or {})
        self.logger = logger

    def process(self, msg: any, kwargs: dict) -> tuple:
        """
        Process the log message before passing to the underlying logger.

        This method intercepts logging calls and automatically adds exc_info=True
        for ERROR and CRITICAL level messages when called within an exception context.
        """
        # Check if this is an error/critical log
        if kwargs.get('stacklevel', 1) > 0:
            # Get the log level from kwargs or default to INFO
            level = kwargs.get('level', logging.INFO)
            level_value = level if isinstance(level, int) else logging.getLevelName(level)

            # If ERROR/CRITICAL and exc_info not set, and there's an active exception
            if (
                level_value >= logging.ERROR and
                'exc_info' not in kwargs and
                sys.exc_info() != (None, None, None)
            ):
                kwargs['exc_info'] = True

        return msg, kwargs


def get_exception_capture_logger(name: str) -> logging.Logger:
    """
    Get a logger with automatic exception capture for ERROR/CRITICAL logs.

    This is a convenience function that returns a logger wrapped with
    ExceptionCaptureAdapter for easy exception traceback logging.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        A logger adapter that automatically captures exception tracebacks

    Example:
        >>> from utils.logging_utils import get_exception_capture_logger
        >>>
        >>> logger = get_exception_capture_logger(__name__)
        >>> try:
        ...     1 / 0
        ... except Exception:
        ...     logger.error("Math error")  # Traceback automatically included!
    """
    base_logger = logging.getLogger(name)
    return ExceptionCaptureAdapter(base_logger)
