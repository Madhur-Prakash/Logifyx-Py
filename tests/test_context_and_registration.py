"""
Tests for ContextLoggerAdapter and global registration.
"""

import logging
import os
import sys
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logify import Logify, ContextLoggerAdapter, get_logify_logger, setup_logify
from logify.core import _stop_queue_listener


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state before each test."""
    logging.Logger.manager.loggerDict.clear()
    logging.setLoggerClass(logging.Logger)
    _stop_queue_listener()
    yield
    _stop_queue_listener()


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestContextLoggerAdapter:
    """Tests for ContextLoggerAdapter functionality."""

    def test_context_prepended_to_message(self, temp_log_dir):
        """Test that context is prepended to log messages in text mode."""
        log = Logify(
            name="test_context",
            mode="dev",
            log_dir=temp_log_dir,
            file="context.log"
        )
        
        request_log = ContextLoggerAdapter(
            log,
            {"request_id": "abc123", "user_id": 42}
        )
        
        # Capture the message
        messages = []
        original_handle = log.handle
        
        def capture_handle(record):
            messages.append(record.getMessage())
            return original_handle(record)
        
        log.handle = capture_handle
        
        request_log.info("Test message")
        
        assert len(messages) > 0
        assert "request_id=abc123" in messages[0]
        assert "user_id=42" in messages[0]
        assert "Test message" in messages[0]
        
    def test_context_with_multiple_fields(self, temp_log_dir):
        """Test context with multiple fields."""
        log = Logify(
            name="test_multi_context",
            mode="dev",
            log_dir=temp_log_dir,
            file="multi_context.log"
        )
        
        context = {
            "request_id": "req-123",
            "user_id": 100,
            "session_id": "sess-456",
            "ip": "192.168.1.1"
        }
        
        adapter = ContextLoggerAdapter(log, context)
        
        # Test that process method works
        msg, kwargs = adapter.process("Hello", {})
        
        assert "request_id=req-123" in msg
        assert "user_id=100" in msg
        assert "session_id=sess-456" in msg
        assert "ip=192.168.1.1" in msg
        assert "Hello" in msg
        
    def test_empty_context(self, temp_log_dir):
        """Test adapter with empty context."""
        log = Logify(
            name="test_empty_context",
            mode="dev",
            log_dir=temp_log_dir,
            file="empty_context.log"
        )
        
        adapter = ContextLoggerAdapter(log, {})
        
        msg, kwargs = adapter.process("Message", {})
        
        assert msg == "Message"
        
    def test_context_adapter_log_levels(self, temp_log_dir):
        """Test that all log levels work with adapter."""
        log = Logify(
            name="test_adapter_levels",
            mode="dev",
            log_dir=temp_log_dir,
            file="adapter_levels.log"
        )
        
        adapter = ContextLoggerAdapter(log, {"test": "value"})
        
        # These should not raise exceptions
        adapter.debug("Debug msg")
        adapter.info("Info msg")
        adapter.warning("Warning msg")
        adapter.error("Error msg")
        adapter.critical("Critical msg")


class TestGlobalRegistration:
    """Tests for setup_logify and get_logify_logger."""

    def test_setup_logify_sets_logger_class(self):
        """Test that setup_logify sets Logify as the logger class."""
        setup_logify()
        
        # Now logging.getLogger should return Logify instances
        log = logging.getLogger("test_setup")
        
        assert isinstance(log, Logify)
        
    def test_get_logify_logger_requires_setup(self):
        """Test that get_logify_logger raises error without setup."""
        # Don't call setup_logify
        
        with pytest.raises(TypeError) as exc_info:
            get_logify_logger("test_no_setup")
            
        assert "LoggerClass not set to Logify" in str(exc_info.value)
        
    def test_get_logify_logger_returns_logify(self, temp_log_dir):
        """Test that get_logify_logger returns Logify instance."""
        setup_logify()
        
        log = get_logify_logger(
            "test_get_logger",
            mode="dev",
            log_dir=temp_log_dir,
            file="get_logger.log"
        )
        
        assert isinstance(log, Logify)
        assert log.name == "test_get_logger"
        
    def test_get_logify_logger_singleton(self, temp_log_dir):
        """Test that get_logify_logger returns same instance for same name."""
        setup_logify()
        
        log1 = get_logify_logger(
            "test_singleton",
            mode="dev",
            log_dir=temp_log_dir,
            file="singleton.log"
        )
        
        log2 = get_logify_logger("test_singleton")
        
        assert log1 is log2
        
    def test_get_logify_logger_configures_once(self, temp_log_dir):
        """Test that configuration is applied only once."""
        setup_logify()
        
        log1 = get_logify_logger(
            "test_config_once",
            mode="dev",
            log_dir=temp_log_dir,
            file="config_once.log"
        )
        
        handler_count = len(log1.handlers)
        
        # Get again with different config (should be ignored)
        log2 = get_logify_logger(
            "test_config_once",
            mode="prod",  # Different mode
            log_dir=temp_log_dir,
            file="different.log"  # Different file
        )
        
        # Should still have same handlers (not reconfigured)
        assert len(log2.handlers) == handler_count
        
    def test_get_logify_logger_no_kwargs(self):
        """Test get_logify_logger without kwargs doesn't configure."""
        setup_logify()
        
        log = get_logify_logger("test_no_kwargs")
        
        # Should have no handlers (not configured)
        assert len(log.handlers) == 0


class TestMultipleLoggers:
    """Tests for multiple logger instances."""

    def test_multiple_loggers_different_names(self, temp_log_dir):
        """Test creating multiple loggers with different names."""
        log1 = Logify(
            name="logger1",
            mode="dev",
            log_dir=temp_log_dir,
            file="logger1.log"
        )
        
        log2 = Logify(
            name="logger2",
            mode="prod",
            log_dir=temp_log_dir,
            file="logger2.log"
        )
        
        assert log1.name == "logger1"
        assert log2.name == "logger2"
        assert log1 is not log2
        
    def test_hierarchical_logger_names(self, temp_log_dir):
        """Test hierarchical logger names."""
        parent = Logify(
            name="myapp",
            mode="dev",
            log_dir=temp_log_dir,
            file="parent.log"
        )
        
        child = Logify(
            name="myapp.module",
            mode="dev",
            log_dir=temp_log_dir,
            file="child.log"
        )
        
        assert parent.name == "myapp"
        assert child.name == "myapp.module"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
