"""
Integration tests for Logify - end-to-end scenarios.
"""

import logging
import os
import sys
import shutil
import tempfile
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logify import Logify, ContextLoggerAdapter, get_logify_logger, setup_logify


class TestEndToEndLogging:
    """End-to-end integration tests."""

    def test_full_logging_workflow(self, temp_log_dir):
        """Test a complete logging workflow."""
        # Create logger
        log = Logify(
            name="integration_test",
            mode="dev",
            log_dir=temp_log_dir,
            file="integration.log",
            mask=True,
            color=False
        )
        
        # Log messages at all levels
        log.debug("Debug: Starting operation")
        log.info("Info: Operation in progress")
        log.warning("Warning: Resource usage high")
        log.error("Error: Operation failed")
        log.critical("Critical: System failure")
        
        # Log with sensitive data (should be masked)
        log.info("User login with password=secret123")
        
        # Force flush
        for handler in log.handlers:
            handler.flush()
        
        # Verify log file exists and contains messages
        log_file = os.path.join(temp_log_dir, "integration.log")
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            content = f.read()
            
        assert "Starting operation" in content
        assert "Operation in progress" in content
        assert "Resource usage high" in content
        assert "Operation failed" in content
        assert "System failure" in content
        
        # Verify password was masked
        assert "secret123" not in content
        assert "****" in content
        
    def test_context_injection_workflow(self, temp_log_dir):
        """Test context injection with adapter."""
        log = Logify(
            name="context_integration",
            mode="dev",
            log_dir=temp_log_dir,
            file="context_int.log"
        )
        
        # Simulate request handling with context
        request_id = "req-12345"
        user_id = 42
        
        request_log = ContextLoggerAdapter(
            log,
            {"request_id": request_id, "user_id": user_id}
        )
        
        request_log.info("Request received")
        request_log.info("Processing request")
        request_log.info("Request completed")
        
        # Force flush
        for handler in log.handlers:
            handler.flush()
        
        # Verify context in log file
        log_file = os.path.join(temp_log_dir, "context_int.log")
        with open(log_file, 'r') as f:
            content = f.read()
            
        assert "request_id=req-12345" in content
        assert "user_id=42" in content
        
    def test_global_registration_workflow(self, temp_log_dir):
        """Test global registration workflow."""
        # Setup Logify globally
        setup_logify()
        
        # Get multiple loggers
        auth_log = get_logify_logger(
            "auth_service",
            mode="dev",
            log_dir=temp_log_dir,
            file="auth.log"
        )
        
        api_log = get_logify_logger(
            "api_service",
            mode="dev",
            log_dir=temp_log_dir,
            file="api.log"
        )
        
        # Log from different services
        auth_log.info("User authenticated")
        api_log.info("API request processed")
        
        # Verify both are Logify instances
        assert isinstance(auth_log, Logify)
        assert isinstance(api_log, Logify)
        
        # Verify logs written
        for handler in auth_log.handlers:
            handler.flush()
        for handler in api_log.handlers:
            handler.flush()
            
        assert os.path.exists(os.path.join(temp_log_dir, "auth.log"))
        assert os.path.exists(os.path.join(temp_log_dir, "api.log"))
        
    def test_preset_modes_real_output(self, temp_log_dir):
        """Test preset modes with real output."""
        # Dev mode
        dev_log = Logify(
            name="dev_test",
            mode="dev",
            log_dir=temp_log_dir,
            file="dev_mode.log"
        )
        
        dev_log.debug("Debug in dev mode")
        dev_log.info("Info in dev mode")
        
        # Simple mode
        simple_log = Logify(
            name="simple_test",
            mode="simple",
            log_dir=temp_log_dir,
            file="simple_mode.log"
        )
        
        simple_log.info("Info in simple mode")
        
        # Flush
        for handler in dev_log.handlers:
            handler.flush()
        for handler in simple_log.handlers:
            handler.flush()
        
        # Dev mode should have debug message (level=DEBUG)
        with open(os.path.join(temp_log_dir, "dev_mode.log"), 'r') as f:
            dev_content = f.read()
        assert "Debug in dev mode" in dev_content
        
    def test_reload_functionality(self, temp_log_dir):
        """Test reload clears and rebuilds handlers."""
        log = Logify(
            name="reload_test",
            mode="dev",
            log_dir=temp_log_dir,
            file="reload.log"
        )
        
        initial_handlers = len(log.handlers)
        log.info("Before reload")
        
        # Reload
        log.reload()
        
        # Should have same number of handlers
        assert len(log.handlers) == initial_handlers
        
        log.info("After reload")
        
        # Verify both messages logged
        for handler in log.handlers:
            handler.flush()
            
        with open(os.path.join(temp_log_dir, "reload.log"), 'r') as f:
            content = f.read()
            
        assert "Before reload" in content
        assert "After reload" in content


class TestErrorScenarios:
    """Tests for error handling scenarios."""

    def test_invalid_mode_ignored(self, temp_log_dir):
        """Test that invalid mode is ignored gracefully."""
        # Should not raise exception
        log = Logify(
            name="invalid_mode_test",
            mode="nonexistent_mode",
            log_dir=temp_log_dir,
            file="invalid_mode.log"
        )
        
        assert log is not None
        log.info("This should still work")
        
    def test_exception_logging(self, temp_log_dir):
        """Test logging exceptions."""
        log = Logify(
            name="exception_test",
            mode="dev",
            log_dir=temp_log_dir,
            file="exception.log"
        )
        
        try:
            raise ValueError("Test exception")
        except Exception:
            log.exception("Caught an exception")
            
        for handler in log.handlers:
            handler.flush()
            
        with open(os.path.join(temp_log_dir, "exception.log"), 'r') as f:
            content = f.read()
            
        assert "Caught an exception" in content
        assert "ValueError" in content
        assert "Test exception" in content


class TestConcurrentLogging:
    """Tests for concurrent logging scenarios."""

    def test_multiple_loggers_same_file(self, temp_log_dir):
        """Test multiple loggers writing to same file."""
        log1 = Logify(
            name="concurrent1",
            mode="dev",
            log_dir=temp_log_dir,
            file="concurrent.log"
        )
        
        log2 = Logify(
            name="concurrent2",
            mode="dev",
            log_dir=temp_log_dir,
            file="concurrent.log"
        )
        
        # Interleaved logging
        log1.info("Message from logger 1")
        log2.info("Message from logger 2")
        log1.info("Another from logger 1")
        log2.info("Another from logger 2")
        
        for handler in log1.handlers:
            handler.flush()
        for handler in log2.handlers:
            handler.flush()
            
        with open(os.path.join(temp_log_dir, "concurrent.log"), 'r') as f:
            content = f.read()
            
        assert "Message from logger 1" in content
        assert "Message from logger 2" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
