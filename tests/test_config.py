"""
Tests for configuration loading (config.py).
"""

import os
import sys
import warnings

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
        "LOG_DIR", "LOG_FILE", "LOG_OUTPUT", "LOG_JSON", "LOG_MASK",
        "LOG_REMOTE", "LOG_KAFKA_SERVERS", "LOG_KAFKA_TOPIC",
        "LOG_SCHEMA_REGISTRY", "LOG_SCHEMA_COMPATIBILITY",
        "LOG_REMOTE_TIMEOUT", "LOG_REMOTE_RETRIES", "LOG_REMOTE_HEADERS",
        # LOGIFYX_* aliases must be cleared too, or a value set by one test
        # leaks into every later test in the session.
        "LOGIFYX_LEVEL", "LOGIFYX_OUTPUT", "LOGIFYX_LOG_FILE",
        "LOGIFYX_LOG_DIR",
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
        """Unset log_file falls back to app.log inside log_dir."""
        from logifyx.output import resolve_log_target

        config = load_config()
        assert config["log_file"] == "app.log"
        # _file_is_default records that nothing *named* the file, which is what
        # lets each logger substitute "<name>.log" for the placeholder.
        assert config["_file_is_default"] is True
        assert resolve_log_target(config["log_dir"], config["log_file"]) == (
            "logs",
            "app.log",
        )

    def test_default_output(self):
        """Test default output is 'both' (console + file)."""
        config = load_config()
        assert config["output"] == "both"

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


class TestLoadConfigPaths:
    """Tests for explicit config file path loading."""

    def test_load_config_uses_current_working_directory_by_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        (tmp_path / ".env").write_text(
            "LOG_LEVEL=WARNING\nLOG_FILE=cwd-env.log\n",
            encoding="utf-8",
        )
        (tmp_path / "logifyx.yaml").write_text(
            "LOG_LEVEL: DEBUG\nLOG_DIR: cwd-logs\n",
            encoding="utf-8",
        )

        config = load_config()

        assert config["level"] == "WARNING"
        assert config["log_file"] == "cwd-env.log"
        assert config["log_dir"] == "cwd-logs"

    def test_load_config_uses_explicit_config_dir(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / ".env").write_text(
            "LOG_LEVEL=WARNING\nLOG_FILE=from-config-dir.log\n",
            encoding="utf-8",
        )
        (config_dir / "logifyx.yaml").write_text(
            "LOG_LEVEL: DEBUG\nLOG_DIR: config-logs\n",
            encoding="utf-8",
        )

        monkeypatch.chdir(tmp_path)

        config = load_config(config_dir=str(config_dir))

        assert config["level"] == "WARNING"
        assert config["log_file"] == "from-config-dir.log"
        assert config["log_dir"] == "config-logs"

    def test_load_config_uses_explicit_files(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "base"
        config_dir.mkdir()
        env_file = tmp_path / "custom.env"
        yaml_file = tmp_path / "custom.yaml"
        env_file.write_text("LOG_LEVEL=ERROR\nLOG_FILE=from-env.log\n", encoding="utf-8")
        yaml_file.write_text("LOG_LEVEL: INFO\nLOG_DIR: yaml-logs\n", encoding="utf-8")

        monkeypatch.chdir(config_dir)

        config = load_config(env_file=str(env_file), yaml_file=str(yaml_file))

        assert config["level"] == "ERROR"
        assert config["log_file"] == "from-env.log"
        assert config["log_dir"] == "yaml-logs"


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
        assert config["log_file"] == "custom.log"

    def test_env_dir_override(self):
        """Test LOG_DIR env var overrides default."""
        os.environ["LOG_DIR"] = "/var/log/myapp"
        config = load_config()
        assert config["log_dir"] == "/var/log/myapp"

    def test_env_output_override(self):
        """Test LOG_OUTPUT env var overrides default."""
        os.environ["LOG_OUTPUT"] = "file"
        config = load_config()
        assert config["output"] == "file"

    def test_env_output_alias(self):
        """Test LOGIFYX_OUTPUT is accepted as an alias for LOG_OUTPUT."""
        os.environ["LOGIFYX_OUTPUT"] = "console"
        config = load_config()
        assert config["output"] == "console"

    def test_invalid_env_output_raises(self):
        """Test an unknown LOG_OUTPUT value is rejected."""
        os.environ["LOG_OUTPUT"] = "nonsense"
        with pytest.raises(ValueError):
            load_config()

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
            "log_dir", "log_file", "output", "json_mode", "mask",
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


class TestMisconfiguredPathsWarn:
    """An explicitly supplied config path that does not exist must not pass silently."""

    @pytest.fixture(autouse=True)
    def _forget_previous_warnings(self):
        from logifyx.config import _clear_path_warnings
        _clear_path_warnings()
        yield
        _clear_path_warnings()

    def test_missing_config_dir_warns_and_falls_back(self, tmp_path):
        missing = str(tmp_path / "does-not-exist")

        with pytest.warns(RuntimeWarning, match="config_dir"):
            config = load_config(config_dir=missing)

        # Still usable — the fallback is to the working directory.
        assert config["level"]

    def test_missing_env_file_warns(self, tmp_path):
        with pytest.warns(RuntimeWarning, match="env_file"):
            load_config(env_file=str(tmp_path / "nope.env"))

    def test_missing_yaml_file_warns(self, tmp_path):
        with pytest.warns(RuntimeWarning, match="yaml_file"):
            load_config(yaml_file=str(tmp_path / "nope.yaml"))

    def test_config_dir_pointing_at_a_file_warns(self, tmp_path):
        not_a_dir = tmp_path / "a-file.txt"
        not_a_dir.write_text("x", encoding="utf-8")

        with pytest.warns(RuntimeWarning, match="not an existing directory"):
            load_config(config_dir=str(not_a_dir))

    def test_warning_names_the_bad_value(self, tmp_path):
        missing = str(tmp_path / "typo-dir")

        with pytest.warns(RuntimeWarning) as caught:
            load_config(config_dir=missing)

        message = str(caught[0].message)
        assert "typo-dir" in message
        assert "will NOT be applied" in message

    def test_valid_paths_do_not_warn(self, tmp_path):
        (tmp_path / "logifyx.yaml").write_text("LOG_LEVEL: WARNING\n", encoding="utf-8")
        (tmp_path / ".env").write_text("LOG_MASK=true\n", encoding="utf-8")

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            config = load_config(config_dir=str(tmp_path))

        assert config["level"] == "WARNING"

    def test_default_lookup_never_warns(self, tmp_path, monkeypatch):
        """Omitting the paths entirely is the normal zero-config case."""
        monkeypatch.chdir(tmp_path)

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            load_config()

    def test_absent_config_files_do_not_warn(self, tmp_path):
        """An existing dir with no .env/logifyx.yaml in it is fine, not a mistake."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            load_config(config_dir=str(tmp_path))

    def test_same_bad_path_warns_only_once(self, tmp_path):
        """load_config runs once per logger; one typo must not spam the console."""
        missing = str(tmp_path / "typo")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for _ in range(5):
                load_config(config_dir=missing)

        runtime = [w for w in caught if w.category is RuntimeWarning]
        assert len(runtime) == 1

    def test_different_bad_paths_each_warn(self, tmp_path):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            load_config(config_dir=str(tmp_path / "typo-a"))
            load_config(config_dir=str(tmp_path / "typo-b"))

        runtime = [w for w in caught if w.category is RuntimeWarning]
        assert len(runtime) == 2

    def test_warning_points_at_the_caller_not_logifyx(self, tmp_path):
        """The typo is in the caller's code, so that is the line to blame."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            load_config(config_dir=str(tmp_path / "typo"))       # <- this line

        blamed = os.path.abspath(caught[0].filename)
        assert blamed == os.path.abspath(__file__), blamed
        assert "logifyx" not in os.path.basename(blamed)

    def test_reset_logging_re_enables_the_warning(self, tmp_path):
        from logifyx import reset_logging

        missing = str(tmp_path / "typo")

        with warnings.catch_warnings(record=True) as first:
            warnings.simplefilter("always")
            load_config(config_dir=missing)
        assert len([w for w in first if w.category is RuntimeWarning]) == 1

        reset_logging()

        with warnings.catch_warnings(record=True) as second:
            warnings.simplefilter("always")
            load_config(config_dir=missing)
        assert len([w for w in second if w.category is RuntimeWarning]) == 1
