"""
Tests for configuration loading (config.py).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logifyx.config import load_config


@pytest.fixture(autouse=True)
def clean_env():
    """Clean up environment variables before/after each test."""
    # Store original values
    original_env = {}
    env_vars = [
        "LOG_LEVEL", "LOG_COLOR", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT",
        "LOG_DIR", "LOG_FILE", "LOG_MODE", "LOG_JSON", "LOG_MASK",
        "LOG_REMOTE", "LOG_KAFKA_SERVERS", "LOG_KAFKA_TOPIC",
        "LOG_SCHEMA_REGISTRY", "LOG_SCHEMA_COMPATIBILITY",
        "LOG_REMOTE_TIMEOUT", "LOG_REMOTE_RETRIES"
    ]
    
    for var in env_vars:
        original_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


class TestLoadConfigDefaults:
    """Tests for default configuration values."""

    def test_default_level(self):
        """Test default log level is INFO."""
        config = load_config()
        assert config["level"] == "INFO"
        
    def test_default_color(self):
        """Test default color is False."""
        config = load_config()
        assert config["color"] is False
        
    def test_default_max_bytes(self):
        """Test default max_bytes is 10MB."""
        config = load_config()
        assert config["max_bytes"] == 10_000_000
        
    def test_default_backup_count(self):
        """Test default backup_count is 5."""
        config = load_config()
        assert config["backup_count"] == 5
        
    def test_default_log_dir(self):
        """Test default log_dir is 'logs'."""
        config = load_config()
        assert config["log_dir"] == "logs"
        
    def test_default_file(self):
        """Test default file is 'app.log'."""
        config = load_config()
        assert config["file"] == "app.log"
        
    def test_default_mode(self):
        """Test default mode is 'dev'."""
        config = load_config()
        assert config["mode"] == "dev"
        
    def test_default_json_mode(self):
        """Test default json_mode is False."""
        config = load_config()
        assert config["json_mode"] is False
        
    def test_default_mask(self):
        """Test default mask is True."""
        config = load_config()
        assert config["mask"] is True
        
    def test_default_remote_url(self):
        """Test default remote_url is None."""
        config = load_config()
        assert config["remote_url"] is None
        
    def test_default_kafka_servers(self):
        """Test default kafka_servers is None."""
        config = load_config()
        assert config["kafka_servers"] is None
        
    def test_default_remote_timeout(self):
        """Test default remote_timeout is 5."""
        config = load_config()
        assert config["remote_timeout"] == 5
        
    def test_default_max_remote_retries(self):
        """Test default max_remote_retries is 3."""
        config = load_config()
        assert config["max_remote_retries"] == 3


class TestLoadConfigEnvOverride:
    """Tests for environment variable overrides."""

    def test_env_level_override(self):
        """Test LOG_LEVEL env var overrides default."""
        os.environ["LOG_LEVEL"] = "DEBUG"
        config = load_config()
        assert config["level"] == "DEBUG"
        
    def test_env_color_override(self):
        """Test LOG_COLOR env var overrides default."""
        os.environ["LOG_COLOR"] = "True"
        config = load_config()
        assert config["color"] is True
        
    def test_env_file_override(self):
        """Test LOG_FILE env var overrides default."""
        os.environ["LOG_FILE"] = "custom.log"
        config = load_config()
        assert config["file"] == "custom.log"
        
    def test_env_dir_override(self):
        """Test LOG_DIR env var overrides default."""
        os.environ["LOG_DIR"] = "/var/log/myapp"
        config = load_config()
        assert config["log_dir"] == "/var/log/myapp"
        
    def test_env_mode_override(self):
        """Test LOG_MODE env var overrides default."""
        os.environ["LOG_MODE"] = "prod"
        config = load_config()
        assert config["mode"] == "prod"
        
    def test_env_json_override(self):
        """Test LOG_JSON env var overrides default."""
        os.environ["LOG_JSON"] = "True"
        config = load_config()
        assert config["json_mode"] is True
        
    def test_env_mask_override(self):
        """Test LOG_MASK env var overrides default."""
        os.environ["LOG_MASK"] = "False"
        config = load_config()
        assert config["mask"] is False
        
    def test_env_remote_override(self):
        """Test LOG_REMOTE env var overrides default."""
        os.environ["LOG_REMOTE"] = "http://logs.example.com/api"
        config = load_config()
        assert config["remote_url"] == "http://logs.example.com/api"
        
    def test_env_kafka_servers_override(self):
        """Test LOG_KAFKA_SERVERS env var overrides default."""
        os.environ["LOG_KAFKA_SERVERS"] = "kafka:9092"
        config = load_config()
        assert config["kafka_servers"] == "kafka:9092"
        
    def test_env_max_bytes_override(self):
        """Test LOG_MAX_BYTES env var overrides default."""
        os.environ["LOG_MAX_BYTES"] = "5000000"
        config = load_config()
        assert config["max_bytes"] == 5000000


class TestConfigStructure:
    """Tests for config structure and types."""

    def test_config_is_dict(self):
        """Test that load_config returns a dict."""
        config = load_config()
        assert isinstance(config, dict)
        
    def test_config_has_all_keys(self):
        """Test that config has all expected keys."""
        config = load_config()
        expected_keys = [
            "level", "color", "max_bytes", "backup_count",
            "log_dir", "file", "mode", "json_mode", "mask",
            "remote_url", "kafka_servers", "kafka_topic",
            "schema_registry_url", "schema_compatibility",
            "remote_timeout", "max_remote_retries", "remote_headers"
        ]
        
        for key in expected_keys:
            assert key in config, f"Missing key: {key}"
            
    def test_boolean_values_are_bool(self):
        """Test that boolean config values are actual bools."""
        config = load_config()
        
        assert isinstance(config["color"], bool)
        assert isinstance(config["json_mode"], bool)
        assert isinstance(config["mask"], bool)
        
    def test_numeric_values_are_int(self):
        """Test that numeric config values are ints."""
        config = load_config()
        
        assert isinstance(config["max_bytes"], int)
        assert isinstance(config["backup_count"], int)
        assert isinstance(config["remote_timeout"], int)
        assert isinstance(config["max_remote_retries"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
