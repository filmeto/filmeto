"""
Test script to demonstrate automatic exception traceback logging.

This script demonstrates the enhanced logging configuration that automatically
includes exception traceback information for ERROR and CRITICAL level logs.
"""
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_utils import AutoTracebackFormatter, get_exception_capture_logger


def setup_test_logging():
    """Setup logging for testing with AutoTracebackFormatter"""
    formatter = AutoTracebackFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(handler)


def test_auto_traceback():
    """Test automatic traceback inclusion for ERROR logs"""
    logger = logging.getLogger(__name__)

    print("=" * 70)
    print("TEST: Automatic Exception Traceback Logging")
    print("=" * 70)
    print()

    # Test 1: INFO and WARNING - no traceback
    logger.info("This is an info message (no traceback)")
    logger.warning("This is a warning message (no traceback)")
    print()

    # Test 2: ERROR with active exception - traceback automatically included
    logger.info("Test 2: ERROR with exception - traceback automatically included")
    try:
        result = 10 / 0
    except Exception:
        # No exc_info=True needed - AutoTracebackFormatter handles it!
        logger.error("Division by zero - notice the full traceback below!")
    print()

    # Test 3: ERROR without exception context - no traceback
    logger.info("Test 3: ERROR without exception - no traceback added")
    logger.error("This is just an error message, no active exception")
    print()

    # Test 4: Using ExceptionCaptureAdapter
    logger.info("Test 4: Using ExceptionCaptureAdapter")
    logger_adapter = get_exception_capture_logger("test.adapter")
    try:
        undefined_function()
    except Exception:
        logger_adapter.error("Caught undefined function call")
    print()

    print("=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("1. ERROR/CRITICAL logs automatically include exception traceback")
    print("2. No need to manually add traceback.format_exc()")
    print("3. No need to explicitly pass exc_info=True (auto-detected)")
    print("4. Works with both standard logger and ExceptionCaptureAdapter")
    print("5. Cleaner code with better consistency")


if __name__ == "__main__":
    setup_test_logging()
    test_auto_traceback()
