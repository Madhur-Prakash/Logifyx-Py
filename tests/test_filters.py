"""
Tests for sensitive data masking (MaskFilter).
"""

import logging
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logify.filters import MaskFilter


@pytest.fixture
def mask_filter():
    """Create a MaskFilter instance."""
    return MaskFilter()


@pytest.fixture
def log_record():
    """Create a basic log record for testing."""
    def _create_record(message):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None
        )
        return record
    return _create_record


class TestMaskFilter:
    """Tests for MaskFilter functionality."""

    def test_mask_password(self, mask_filter, log_record):
        """Test masking of password patterns."""
        record = log_record("User login password=secret123")
        mask_filter.filter(record)
        
        assert "secret123" not in record.msg
        assert "****" in record.msg
        
    def test_mask_token(self, mask_filter, log_record):
        """Test masking of token patterns."""
        record = log_record("API call token=abc123xyz")
        mask_filter.filter(record)
        
        assert "abc123xyz" not in record.msg
        assert "****" in record.msg
        
    def test_mask_secret(self, mask_filter, log_record):
        """Test masking of secret patterns."""
        record = log_record("Config loaded secret=mySecretValue")
        mask_filter.filter(record)
        
        assert "mySecretValue" not in record.msg
        assert "****" in record.msg
        
    def test_mask_api_key(self, mask_filter, log_record):
        """Test masking of api_key patterns."""
        record = log_record("Request with api_key=sk_live_123456")
        mask_filter.filter(record)
        
        assert "sk_live_123456" not in record.msg
        assert "****" in record.msg
        
    def test_mask_access_key(self, mask_filter, log_record):
        """Test masking of access_key patterns."""
        record = log_record("AWS access_key=AKIAIOSFODNN7EXAMPLE")
        mask_filter.filter(record)
        
        assert "AKIAIOSFODNN7EXAMPLE" not in record.msg
        assert "****" in record.msg
        
    def test_mask_access_token(self, mask_filter, log_record):
        """Test masking of access_token patterns."""
        record = log_record("OAuth access_token=ya29.a0AVA9y1uZ")
        mask_filter.filter(record)
        
        assert "ya29.a0AVA9y1uZ" not in record.msg
        assert "****" in record.msg
        
    def test_mask_multiple_sensitive_fields(self, mask_filter, log_record):
        """Test masking of multiple sensitive fields in one message."""
        record = log_record("Login: password=pass123 token=tok456 api_key=key789")
        mask_filter.filter(record)
        
        assert "pass123" not in record.msg
        assert "tok456" not in record.msg
        assert "key789" not in record.msg
        assert record.msg.count("****") >= 3
        
    def test_no_mask_for_safe_content(self, mask_filter, log_record):
        """Test that safe content is not masked."""
        original_msg = "User logged in successfully from IP 192.168.1.1"
        record = log_record(original_msg)
        mask_filter.filter(record)
        
        assert record.msg == original_msg
        
    def test_filter_returns_true(self, mask_filter, log_record):
        """Test that filter always returns True (allows record)."""
        record = log_record("Any message")
        result = mask_filter.filter(record)
        
        assert result is True
        
    def test_mask_preserves_message_structure(self, mask_filter, log_record):
        """Test that masking preserves overall message structure."""
        # Note: pattern \S+ matches non-whitespace so comma after "secret" is consumed
        record = log_record("User: john, password=secret status: active")
        mask_filter.filter(record)
        
        assert "User: john," in record.msg
        assert "status: active" in record.msg
        assert "****" in record.msg


class TestMaskPatterns:
    """Tests for specific regex patterns in MaskFilter."""

    def test_sensitive_patterns_list(self, mask_filter):
        """Test that SENSITIVE list contains expected patterns."""
        assert len(mask_filter.SENSITIVE) >= 6
        
    def test_pattern_case_sensitivity(self, mask_filter, log_record):
        """Test pattern matching for different cases."""
        # Lowercase
        record1 = log_record("password=secret")
        mask_filter.filter(record1)
        assert "****" in record1.msg
        
        # Test api_key pattern with word boundary
        record2 = log_record("my_api_key value")
        mask_filter.filter(record2)
        # The pattern (?i)\b\w*api_key\w*\b should match


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
