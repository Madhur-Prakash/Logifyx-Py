import os
import yaml
import json
from pathlib import Path
from typing import Optional
from dotenv import dotenv_values

CONFIG_FILE = "logifyx.yaml"
ENV_FILE = ".env"


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


def _as_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_config(
    config_dir: Optional[str] = None,
    env_file: Optional[str] = None,
    yaml_file: Optional[str] = None,
):
    base_dir = _resolve_config_dir(config_dir)

    env_path = _resolve_path(env_file) or (base_dir / ENV_FILE if (base_dir / ENV_FILE).is_file() else None)
    env_values = dotenv_values(env_path) if env_path else {}
    yaml_config = {}

    config_path = _resolve_path(yaml_file) or (base_dir / CONFIG_FILE if (base_dir / CONFIG_FILE).is_file() else None)

    # Auto-load logifyx.yaml if it exists
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

    # Build config with priority: env > yaml > defaults
    # Both env and yaml use uppercase keys (LOG_LEVEL, LOG_FILE, etc.)
    config = {}
    def _resolve_value(key: str, default):
        return os.getenv(key, env_values.get(key, yaml_config.get(key, default)))

    config["level"] = _resolve_value("LOG_LEVEL", "INFO")
    config["color"] = _as_bool(_resolve_value("LOG_COLOR", False), False)
    config["max_bytes"] = int(_resolve_value("LOG_MAX_BYTES", 10_000_000))
    config["backup_count"] = int(_resolve_value("LOG_BACKUP_COUNT", 5))
    config["log_dir"] = _resolve_value("LOG_DIR", "logs")
    config["file"] = _resolve_value("LOG_FILE", "app.log")
    config["mode"] = _resolve_value("LOG_MODE", "dev")
    config["json_mode"] = _as_bool(_resolve_value("LOG_JSON", False), False)
    config["mask"] = _as_bool(_resolve_value("LOG_MASK", True), True)
    config["remote_url"] = _resolve_value("LOG_REMOTE", None)
    
    # Kafka settings
    config["kafka_servers"] = _resolve_value("LOG_KAFKA_SERVERS", None)
    config["kafka_topic"] = _resolve_value("LOG_KAFKA_TOPIC", "logs")
    config["schema_registry_url"] = _resolve_value("LOG_SCHEMA_REGISTRY", None)
    config["schema_compatibility"] = _resolve_value("LOG_SCHEMA_COMPATIBILITY", "BACKWARD")

    # remote request settings
    config["remote_timeout"] = int(_resolve_value("LOG_REMOTE_TIMEOUT", 5))
    config["max_remote_retries"] = int(_resolve_value("LOG_REMOTE_RETRIES", 3))

    # remote headers
    env_headers = os.getenv("LOG_REMOTE_HEADERS", env_values.get("LOG_REMOTE_HEADERS"))

    if env_headers:
        try:
            config["remote_headers"] = json.loads(env_headers)
        except json.JSONDecodeError:
            config["remote_headers"] = {"Content-Type": "application/json"}
    else:
        yaml_headers = yaml_config.get("LOG_REMOTE_HEADERS")
        config["remote_headers"] = (
            yaml_headers if isinstance(yaml_headers, dict)
            else {"Content-Type": "application/json"}
        )
    return config
