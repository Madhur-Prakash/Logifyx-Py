import os
import yaml
import json
from pathlib import Path
from typing import Optional
from dotenv import dotenv_values
from .output import DEFAULT_OUTPUT, normalize_output

CONFIG_FILE = "logifyx.yaml"
ENV_FILE = ".env"

# Secondary spellings accepted for a setting, checked after the canonical key.
# Logifyx's own convention is the LOG_* prefix; the LOGIFYX_* forms are
# accepted too so the variables read unambiguously in a shared environment
# where LOG_LEVEL may already belong to another tool.
_KEY_ALIASES = {
    "LOG_LEVEL":  ("LOGIFYX_LEVEL",),
    "LOG_OUTPUT": ("LOGIFYX_OUTPUT",),
    "LOG_FILE":   ("LOGIFYX_LOG_FILE",),
    "LOG_DIR":    ("LOGIFYX_LOG_DIR",),
}

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"}
_VALID_COMPATIBILITY = {
    "BACKWARD", "BACKWARD_TRANSITIVE",
    "FORWARD",  "FORWARD_TRANSITIVE",
    "FULL",     "FULL_TRANSITIVE",
    "NONE",
}


def _resolve_path(path: Optional[str]) -> Optional[Path]:
    if not path:
        return None
    resolved = Path(path).expanduser()
    return resolved if resolved.is_file() else None


def _resolve_config_dir(config_dir: Optional[str]) -> Path:
    if config_dir:
        candidate = Path(config_dir).expanduser()
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return Path.cwd().resolve()


def _as_bool(key: str, value, default: bool) -> bool:
    """Parse a bool from env/yaml. Only accepts True/False or the strings 'true'/'false'."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    # env vars are always strings — only accept the literal words "true" / "false"
    if isinstance(value, str):
        s = value.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    raise ValueError(
        f"{key} must be true or false, got {value!r} ({type(value).__name__})"
    )


def _as_int(key: str, value, default: int, min_val: int = 0) -> int:
    """Parse an int from env/yaml. Raises on non-numeric or out-of-range values."""
    if value is None:
        return default
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"{key} must be an integer, got {value!r} ({type(value).__name__})"
        )
    if result < min_val:
        raise ValueError(
            f"{key} must be >= {min_val}, got {result!r}"
        )
    return result


def load_config(
    config_dir: Optional[str] = None,
    env_file: Optional[str] = None,
    yaml_file: Optional[str] = None,
):
    base_dir = _resolve_config_dir(config_dir)

    env_path = _resolve_path(env_file) or (base_dir / ENV_FILE if (base_dir / ENV_FILE).is_file() else None)
    env_values = dotenv_values(env_path) if env_path else {}
    yaml_config: dict = {}

    config_path = _resolve_path(yaml_file) or (base_dir / CONFIG_FILE if (base_dir / CONFIG_FILE).is_file() else None)

    # Auto-load logifyx.yaml if it exists
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

    # Build config with priority: env > yaml > defaults
    # Both env and yaml use uppercase keys (LOG_LEVEL, LOG_FILE, etc.)
    config = {}
    def _resolve_value(key: str, default):
        # Per key name: process env > .env file > logifyx.yaml. The canonical
        # LOG_* name is consulted first, then any LOGIFYX_* alias for it.
        for candidate in (key,) + _KEY_ALIASES.get(key, ()):
            if candidate in os.environ:
                return os.environ[candidate]
            if candidate in env_values:
                return env_values[candidate]
            if candidate in yaml_config:
                return yaml_config[candidate]
        return default

    def _was_provided(key: str) -> bool:
        """True when the key (or one of its aliases) is set anywhere."""
        return any(
            candidate in os.environ
            or candidate in env_values
            or candidate in yaml_config
            for candidate in (key,) + _KEY_ALIASES.get(key, ())
        )

    # level
    level = _resolve_value("LOG_LEVEL", "INFO")
    if isinstance(level, str) and level.upper() not in _VALID_LEVELS:
        raise ValueError(
            f"LOG_LEVEL must be one of {sorted(_VALID_LEVELS)}, got {level!r}"
        )
    config["level"] = level.upper() if isinstance(level, str) else level

    # bools
    config["color"]     = _as_bool("LOG_COLOR", _resolve_value("LOG_COLOR", True),   True)
    config["json_mode"] = _as_bool("LOG_JSON",  _resolve_value("LOG_JSON",  False),  False)
    config["mask"]      = _as_bool("LOG_MASK",  _resolve_value("LOG_MASK",  True),   True)

    # ints
    config["max_bytes"]         = _as_int("LOG_MAX_BYTES",    _resolve_value("LOG_MAX_BYTES",    10_000_000), 10_000_000, min_val=1)
    config["backup_count"]      = _as_int("LOG_BACKUP_COUNT", _resolve_value("LOG_BACKUP_COUNT", 5),          5,          min_val=0)
    config["remote_timeout"]    = _as_int("LOG_REMOTE_TIMEOUT", _resolve_value("LOG_REMOTE_TIMEOUT", 5),      5,          min_val=1)
    config["max_remote_retries"] = _as_int("LOG_REMOTE_RETRIES", _resolve_value("LOG_REMOTE_RETRIES", 3),     3,          min_val=0)

    # output destination — console / file / both / none
    config["output"] = normalize_output(
        _resolve_value("LOG_OUTPUT", DEFAULT_OUTPUT), source="LOG_OUTPUT"
    )

    # strings
    config["log_dir"]            = _resolve_value("LOG_DIR",            "logs")
    config["log_file"]           = _resolve_value("LOG_FILE", "app.log")
    config["remote_url"]         = _resolve_value("LOG_REMOTE", None)
    config["kafka_servers"]      = _resolve_value("LOG_KAFKA_SERVERS", None)
    config["kafka_topic"]        = _resolve_value("LOG_KAFKA_TOPIC",    "logs")
    config["schema_registry_url"] = _resolve_value("LOG_SCHEMA_REGISTRY", None)

    # schema_compatibility
    compatibility = _resolve_value("LOG_SCHEMA_COMPATIBILITY", "BACKWARD")
    if isinstance(compatibility, str):
        compatibility = compatibility.upper()
    if compatibility not in _VALID_COMPATIBILITY:
        raise ValueError(
            f"LOG_SCHEMA_COMPATIBILITY must be one of {sorted(_VALID_COMPATIBILITY)}, "
            f"got {compatibility!r}"
        )
    config["schema_compatibility"] = compatibility

    # file default tracking — when nothing names the log file, the logger name
    # supplies it (see Logifyx.configure), so record whether it was set anywhere.
    config["_file_is_default"] = not _was_provided("LOG_FILE")

    # remote_headers — JSON string from env, dict from yaml
    env_headers = os.getenv("LOG_REMOTE_HEADERS", env_values.get("LOG_REMOTE_HEADERS"))
    if env_headers:
        try:
            parsed = json.loads(env_headers)
        except json.JSONDecodeError:
            raise ValueError(
                f"LOG_REMOTE_HEADERS must be a valid JSON object, got {env_headers!r}"
            )
        if not isinstance(parsed, dict):
            raise ValueError(
                f"LOG_REMOTE_HEADERS must be a JSON object (dict), got {type(parsed).__name__}"
            )
        config["remote_headers"] = parsed
    else:
        yaml_headers = yaml_config.get("LOG_REMOTE_HEADERS")
        if yaml_headers is not None and not isinstance(yaml_headers, dict):
            raise ValueError(
                f"LOG_REMOTE_HEADERS in logifyx.yaml must be a mapping, got {type(yaml_headers).__name__}"
            )
        config["remote_headers"] = yaml_headers if isinstance(yaml_headers, dict) else {"Content-Type": "application/json"}

    return config
