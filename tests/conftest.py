"""
Pytest configuration and shared fixtures.
"""

import logging
import os
import shutil
import sys
import tempfile
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logify.core import _stop_queue_listener


@pytest.fixture(autouse=True)
def reset_logging_state():
    """
    Reset logging state before each test.
    This ensures tests don't interfere with each other.
    """
    # Store original logger class
    original_class = logging.getLoggerClass()
    
    # Clear all custom loggers
    logging.Logger.manager.loggerDict.clear()
    
    # Reset to default logger class
    logging.setLoggerClass(logging.Logger)
    
    # Stop any queue listeners
    _stop_queue_listener()
    
    yield
    
    # Cleanup after test
    _stop_queue_listener()
    logging.Logger.manager.loggerDict.clear()
    logging.setLoggerClass(original_class)


@pytest.fixture
def temp_log_dir():
    """
    Create a temporary directory for log files.
    Automatically cleaned up after test.
    """
    temp_dir = tempfile.mkdtemp(prefix="logify_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def log_record_factory():
    """
    Factory fixture for creating log records.
    """
    def _create_record(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        func="test_func"
    ):
        return logging.LogRecord(
            name=name,
            level=level,
            pathname=pathname,
            lineno=lineno,
            msg=msg,
            args=(),
            exc_info=None,
            func=func
        )
    return _create_record


@pytest.fixture
def clean_env():
    """
    Clean up LOG_* environment variables.
    """
    env_vars = [
        "LOG_LEVEL", "LOG_COLOR", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT",
        "LOG_DIR", "LOG_FILE", "LOG_MODE", "LOG_JSON", "LOG_MASK",
        "LOG_REMOTE", "LOG_KAFKA_SERVERS", "LOG_KAFKA_TOPIC",
        "LOG_SCHEMA_REGISTRY", "LOG_SCHEMA_COMPATIBILITY",
        "LOG_REMOTE_TIMEOUT", "LOG_REMOTE_RETRIES"
    ]
    
    # Store and clear
    original = {}
    for var in env_vars:
        original[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore
    for var, value in original.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]
