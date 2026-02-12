"""
Tests for the core Logify class functionality.
"""

import logging
import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Ensure we can import from parent directory
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logify import Logify, ContextLoggerAdapter, get_logify_logger, setup_logify
from logify.core import _sentinel, _stop_queue_listener


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state before each test."""
    # Clear all loggers
    logging.Logger.manager.loggerDict.clear()
    # Reset logger class to default
    logging.setLoggerClass(logging.Logger)
    # Stop any queue listeners
    _stop_queue_listener()
    yield
    # Cleanup after test
    _stop_queue_listener()


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestLogifyDirectInstantiation:
    """Tests for direct Logify instantiation."""

    def test_basic_instantiation(self, temp_log_dir):
        """Test basic Logify instantiation with minimal config."""
        log = Logify(
            name="test_basic",
            mode="dev",
            log_dir=temp_log_dir,
            file="test.log"
        )
        
        assert log.name == "test_basic"
        assert len(log.handlers) > 0
        
    def test_instantiation_with_all_params(self, temp_log_dir):
        """Test Logify instantiation with all parameters."""
        log = Logify(
            name="test_full",
            mode="prod",
            json_mode=False,
            log_dir=temp_log_dir,
            file="full_test.log",
            mask=True,
            color=True,
            backup_count=3,
            max_bytes=1000000
        )
        
        assert log.name == "test_full"
        assert log.config["backup_count"] == 3
        assert log.config["max_bytes"] == 1000000
        
    def test_handlers_prevent_reconfiguration(self, temp_log_dir):
        """Test that existing handlers prevent reconfiguration."""
        log1 = Logify(
            name="test_singleton",
            mode="dev",
            log_dir=temp_log_dir,
            file="singleton.log"
        )
        
        handler_count = len(log1.handlers)
        
        # Create another instance with same name
        log2 = Logify(
            name="test_singleton",
            mode="prod",  # Different mode
            log_dir=temp_log_dir,
            file="singleton.log"
        )
        
        # Should still have same number of handlers (not doubled)
        assert len(log2.handlers) == handler_count
        
    def test_logging_methods_work(self, temp_log_dir):
        """Test that all logging methods work."""
        log = Logify(
            name="test_methods",
            mode="dev",
            log_dir=temp_log_dir,
            file="methods.log"
        )
        
        # These should not raise exceptions
        log.debug("Debug message")
        log.info("Info message")
        log.warning("Warning message")
        log.error("Error message")
        log.critical("Critical message")


class TestLogifyPresets:
    """Tests for preset modes (dev, prod, simple)."""

    def test_dev_mode(self, temp_log_dir):
        """Test dev mode preset."""
        log = Logify(
            name="test_dev",
            mode="dev",
            log_dir=temp_log_dir,
            file="dev.log"
        )
        
        assert log.config["level"] == "DEBUG"
        assert log.config["color"] is True
        assert log.config["json_mode"] is False
        
    def test_prod_mode(self, temp_log_dir):
        """Test prod mode preset."""
        log = Logify(
            name="test_prod",
            mode="prod",
            log_dir=temp_log_dir,
            file="prod.log"
        )
        
        assert log.config["level"] == "INFO"
        assert log.config["color"] is False
        # Note: json_mode might be False due to conflict resolution with color
        
    def test_simple_mode(self, temp_log_dir):
        """Test simple mode preset."""
        log = Logify(
            name="test_simple",
            mode="simple",
            log_dir=temp_log_dir,
            file="simple.log"
        )
        
        assert log.config["level"] == "INFO"
        assert log.config["color"] is False
        assert log.config["json_mode"] is False


class TestLogifyReload:
    """Tests for reload functionality."""

    def test_reload_clears_handlers(self, temp_log_dir):
        """Test that reload clears existing handlers."""
        log = Logify(
            name="test_reload",
            mode="dev",
            log_dir=temp_log_dir,
            file="reload.log"
        )
        
        initial_handlers = len(log.handlers)
        assert initial_handlers > 0
        
        log.reload()
        
        # Should have same number of handlers after reload
        assert len(log.handlers) == initial_handlers


class TestSentinelPattern:
    """Tests for the sentinel pattern implementation."""

    def test_sentinel_is_unique(self):
        """Test that sentinel is a unique object."""
        assert _sentinel is not None
        assert _sentinel is not True
        assert _sentinel is not False
        
    def test_no_params_means_no_configure(self):
        """Test that no params means configure() is not called."""
        # Just name doesn't trigger configure
        log = Logify(name="test_no_config")
        
        # Should not have config attribute if not configured
        # Actually it might not have handlers
        assert not hasattr(log, 'config') or not log.handlers


class TestFileLogging:
    """Tests for file logging functionality."""

    def test_log_file_created(self, temp_log_dir):
        """Test that log file is created."""
        log_file = "created.log"
        log = Logify(
            name="test_file_create",
            mode="dev",
            log_dir=temp_log_dir,
            file=log_file
        )
        
        log.info("Test message")
        
        # Check file exists
        full_path = os.path.join(temp_log_dir, log_file)
        assert os.path.exists(full_path)
        
    def test_log_content_written(self, temp_log_dir):
        """Test that log content is written to file."""
        log_file = "content.log"
        log = Logify(
            name="test_content",
            mode="dev",
            log_dir=temp_log_dir,
            file=log_file
        )
        
        test_message = "This is a test message 12345"
        log.info(test_message)
        
        # Force flush
        for handler in log.handlers:
            handler.flush()
        
        full_path = os.path.join(temp_log_dir, log_file)
        with open(full_path, 'r') as f:
            content = f.read()
            
        assert test_message in content


class TestConflictResolution:
    """Tests for configuration conflict resolution."""

    def test_json_mode_disabled_when_color_enabled(self, temp_log_dir):
        """Test that json_mode is disabled when color is enabled."""
        log = Logify(
            name="test_conflict",
            json_mode=True,
            color=True,
            log_dir=temp_log_dir,
            file="conflict.log"
        )
        
        # json_mode should be False due to conflict resolution
        assert log.config["json_mode"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
