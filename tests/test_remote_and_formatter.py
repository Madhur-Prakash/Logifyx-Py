"""
Tests for RemoteHandler and formatter.
"""

import logging
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logify.remote import RemoteHandler
from logify.formatter import get_formatter


class TestRemoteHandler:
    """Tests for RemoteHandler functionality."""

    def test_initialization(self):
        """Test RemoteHandler initialization."""
        handler = RemoteHandler(
            url="http://example.com/logs",
            timeout=5,
            max_failures=5,
            headers={"X-API-Key": "test"}
        )
        
        assert handler.url == "http://example.com/logs"
        assert handler.timeout == 5
        assert handler.max_failures == 5
        assert handler.headers == {"X-API-Key": "test"}
        assert handler.disabled is False
        
    def test_default_headers(self):
        """Test default headers are empty dict."""
        handler = RemoteHandler(url="http://example.com/logs")
        
        assert handler.headers == {}
        
    def test_disabled_property_thread_safe(self):
        """Test disabled property is thread-safe."""
        handler = RemoteHandler(url="http://example.com/logs")
        
        assert handler.disabled is False
        
        handler.disabled = True
        assert handler.disabled is True
        
        handler.disabled = False
        assert handler.disabled is False
        
    @patch('logify.remote.requests.post')
    def test_successful_emit(self, mock_post):
        """Test successful log emission."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        handler = RemoteHandler(url="http://example.com/logs")
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Verify requests.post was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        assert call_args.kwargs["json"]["level"] == "INFO"
        assert call_args.kwargs["json"]["logger"] == "test"
        
    @patch('logify.remote.requests.post')
    def test_emit_when_disabled(self, mock_post):
        """Test that emit does nothing when disabled."""
        handler = RemoteHandler(url="http://example.com/logs")
        handler.disabled = True
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # requests.post should not be called
        mock_post.assert_not_called()
        
    @patch('logify.remote.requests.post')
    def test_failure_tracking(self, mock_post):
        """Test that failures are tracked and handler disables after max."""
        mock_post.side_effect = Exception("Connection failed")
        
        handler = RemoteHandler(
            url="http://example.com/logs",
            max_failures=3
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Emit 3 times (should disable after 3rd failure)
        handler.emit(record)
        handler.emit(record)
        handler.emit(record)
        
        assert handler.disabled is True
        
    @patch('logify.remote.requests.post')
    def test_failure_counter_resets_on_success(self, mock_post):
        """Test that failure counter resets on successful send."""
        handler = RemoteHandler(
            url="http://example.com/logs",
            max_failures=3
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # First call fails
        mock_post.side_effect = Exception("Connection failed")
        handler.emit(record)
        
        # Second call succeeds
        mock_post.side_effect = None
        mock_post.return_value = MagicMock()
        handler.emit(record)
        
        # Failure counter should be reset to 0
        assert handler._failures == 0
        assert handler.disabled is False


class TestFormatter:
    """Tests for get_formatter function."""

    def test_default_formatter(self):
        """Test default plain text formatter."""
        formatter = get_formatter(json_mode=False, color=False)
        
        assert isinstance(formatter, logging.Formatter)
        assert "%(asctime)s" in formatter._fmt
        assert "%(name)s" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt
        
    def test_json_formatter(self):
        """Test JSON formatter."""
        formatter = get_formatter(json_mode=True, color=False)
        
        # Should be JsonFormatter
        assert formatter.__class__.__name__ == "JsonFormatter"
        
    def test_color_formatter(self):
        """Test colored formatter."""
        formatter = get_formatter(json_mode=False, color=True)
        
        # Should be ColoredFormatter
        assert formatter.__class__.__name__ == "ColoredFormatter"
        
    def test_format_output(self):
        """Test actual formatting output."""
        formatter = get_formatter(json_mode=False, color=False)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        
        assert "test" in output
        assert "INFO" in output
        assert "Test message" in output
        assert "42" in output  # Line number


class TestHandlerPayload:
    """Tests for RemoteHandler payload structure."""

    @patch('logify.remote.requests.post')
    def test_payload_structure(self, mock_post):
        """Test the structure of the log payload."""
        mock_post.return_value = MagicMock()
        
        handler = RemoteHandler(url="http://example.com/logs")
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        record = logging.LogRecord(
            name="myapp",
            level=logging.ERROR,
            pathname="/app/main.py",
            lineno=100,
            msg="Error occurred",
            args=(),
            exc_info=None,
            func="handle_request"
        )
        
        handler.emit(record)
        
        payload = mock_post.call_args.kwargs["json"]
        
        assert payload["level"] == "ERROR"
        assert "Error occurred" in payload["message"]
        assert payload["logger"] == "myapp"
        assert "timestamp" in payload
        assert payload["file"] == "/app/main.py"
        assert payload["line"] == 100
        assert payload["func"] == "handle_request"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
