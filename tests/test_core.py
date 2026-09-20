"""
Tests for the core Logifyx class functionality.
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

from logifyx import Logifyx, ContextLoggerAdapter, get_logify_logger, setup_logify
from logifyx.core import _sentinel, _stop_queue_listener


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state before each test."""
    for logger in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()
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
    """Tests for direct Logifyx instantiation."""

    def test_basic_instantiation(self, temp_log_dir):
        """Test basic Logifyx instantiation with minimal config."""
        log = Logifyx(
            name="test_basic",
            log_dir=temp_log_dir,
            log_file="test.log"
        )

        assert log.name == "test_basic"
        assert len(log.handlers) > 0

    def test_instantiation_with_all_params(self, temp_log_dir):
        """Test Logifyx instantiation with all parameters."""
        log = Logifyx(
            name="test_full",
            json_mode=False,
            log_dir=temp_log_dir,
            log_file="full_test.log",
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
        log1 = Logifyx(
            name="test_singleton",
            log_dir=temp_log_dir,
            log_file="singleton.log"
        )

        handler_count = len(log1.handlers)

        # Create another instance with same name
        log2 = Logifyx(
            name="test_singleton",
            log_dir=temp_log_dir,
            log_file="singleton.log"
        )

        # Should still have same number of handlers (not doubled)
        assert len(log2.handlers) == handler_count

    def test_logging_methods_work(self, temp_log_dir):
        """Test that all logging methods work."""
        log = Logifyx(
            name="test_methods",
            log_dir=temp_log_dir,
            log_file="methods.log"
        )

        # These should not raise exceptions
        log.debug("Debug message")
        log.info("Info message")
        log.warning("Warning message")
        log.error("Error message")
        log.critical("Critical message")

    def test_explicit_config_paths_are_used(self, temp_log_dir):
        """Test that explicit config paths are honored in direct code usage."""
        env_path = os.path.join(temp_log_dir, ".env")
        yaml_path = os.path.join(temp_log_dir, "logifyx.yaml")

        with open(env_path, "w") as f:
            f.write("LOG_LEVEL=WARNING\nLOG_FILE=from-env.log\n")

        with open(yaml_path, "w") as f:
            f.write("LOG_LEVEL: INFO\nLOG_DIR: from-yaml-dir\n")

        log = Logifyx(
            name="test_explicit_paths",
            config_dir=temp_log_dir,
            env_file=env_path,
            yaml_file=yaml_path,
        )

        assert log.config["level"] == "WARNING"
        assert log.config["log_file"] == "from-env.log"
        assert log.config["log_dir"] == "from-yaml-dir"


class TestExplicitSettings:
    """Settings are supplied explicitly per logger, not via preset modes."""

    def test_debug_colored_text(self, temp_log_dir):
        """Verbose local setup: DEBUG level, color on, plain text."""
        log = Logifyx(
            name="test_verbose",
            level="DEBUG",
            color=True,
            json_mode=False,
            log_dir=temp_log_dir,
            log_file="verbose.log"
        )

        assert log.config["level"] == "DEBUG"
        assert log.config["color"] is True
        assert log.config["json_mode"] is False

    def test_info_plain_text(self, temp_log_dir):
        """Production-style setup: INFO level, no color."""
        log = Logifyx(
            name="test_plain",
            level="INFO",
            color=False,
            log_dir=temp_log_dir,
            log_file="plain.log"
        )

        assert log.config["level"] == "INFO"
        assert log.config["color"] is False

    def test_json_wins_over_color(self, temp_log_dir):
        """json_mode and color are mutually exclusive."""
        log = Logifyx(
            name="test_json_only",
            level="INFO",
            color=False,
            json_mode=True,
            log_dir=temp_log_dir,
            log_file="json_only.log"
        )

        assert log.config["json_mode"] is True
        assert log.config["color"] is False


class TestLogifyReload:
    """Tests for reload functionality."""

    def test_reload_clears_handlers(self, temp_log_dir):
        """Test that reload clears existing handlers."""
        log = Logifyx(
            name="test_reload",
            log_dir=temp_log_dir,
            log_file="reload.log"
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
        """Test that zero-config instantiation still configures the logger."""
        log = Logifyx(name="test_no_config")

        assert hasattr(log, "config")
        assert log.handlers

    def test_zero_config_logs_info(self, temp_log_dir):
        """Test that INFO logs are emitted without passing color or other kwargs."""
        log = Logifyx(name="test_zero_config", log_dir=temp_log_dir, log_file="zero.log")

        log.info("Zero-config info message")

        for handler in log.handlers:
            handler.flush()

        full_path = os.path.join(temp_log_dir, "zero.log")
        with open(full_path, "r") as f:
            content = f.read()

        assert "Zero-config info message" in content

        for handler in log.handlers[:]:
            log.removeHandler(handler)
            handler.close()

    def test_default_file_uses_logger_name(self, temp_log_dir):
        """Test that the default log file follows the logger name when not set explicitly."""
        log = Logifyx(name="billing-service", log_dir=temp_log_dir)

        log.info("Name-based log file test")

        for handler in log.handlers:
            handler.flush()

        expected_file = os.path.join(temp_log_dir, "billing-service.log")
        assert log.config["log_file"] == "billing-service.log"
        assert os.path.exists(expected_file)

        for handler in log.handlers[:]:
            log.removeHandler(handler)
            handler.close()


class TestFileLogging:
    """Tests for file logging functionality."""

    def test_log_file_created(self, temp_log_dir):
        """Test that log file is created."""
        log_file = "created.log"
        log = Logifyx(
            name="test_file_create",
            log_dir=temp_log_dir,
            log_file=log_file
        )

        log.info("Test message")

        # Check file exists
        full_path = os.path.join(temp_log_dir, log_file)
        assert os.path.exists(full_path)

    def test_log_content_written(self, temp_log_dir):
        """Test that log content is written to file."""
        log_file = "content.log"
        log = Logifyx(
            name="test_content",
            log_dir=temp_log_dir,
            log_file=log_file
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
        log = Logifyx(
            name="test_conflict",
            json_mode=True,
            color=True,
            log_dir=temp_log_dir,
            log_file="conflict.log"
        )

        # json_mode should be False due to conflict resolution
        assert log.config["json_mode"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
