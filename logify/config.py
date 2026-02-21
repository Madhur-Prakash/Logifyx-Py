import os
import yaml
import json
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "logify.yaml"


def load_config():
    yaml_config = {}

    # Auto-load logify.yaml if it exists
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            yaml_config = yaml.safe_load(f) or {}

    # Build config with priority: env > yaml > defaults
    # Both env and yaml use uppercase keys (LOG_LEVEL, LOG_FILE, etc.)
    config = {}
    config["level"] = os.getenv("LOG_LEVEL", yaml_config.get("LOG_LEVEL", "INFO"))
    config["color"] = os.getenv("LOG_COLOR", str(yaml_config.get("LOG_COLOR", False))) == "True"
    config["max_bytes"] = int(os.getenv("LOG_MAX_BYTES", yaml_config.get("LOG_MAX_BYTES", 10_000_000)))
    config["backup_count"] = int(os.getenv("LOG_BACKUP_COUNT", yaml_config.get("LOG_BACKUP_COUNT", 5)))
    config["log_dir"] = os.getenv("LOG_DIR", yaml_config.get("LOG_DIR", "logs"))
    config["file"] = os.getenv("LOG_FILE", yaml_config.get("LOG_FILE", "app.log"))
    config["mode"] = os.getenv("LOG_MODE", yaml_config.get("LOG_MODE", "dev"))
    config["json_mode"] = os.getenv("LOG_JSON", str(yaml_config.get("LOG_JSON", False))) == "True"
    config["mask"] = os.getenv("LOG_MASK", str(yaml_config.get("LOG_MASK", True))) == "True"
    config["remote_url"] = os.getenv("LOG_REMOTE", yaml_config.get("LOG_REMOTE"))
    
    # Kafka settings
    config["kafka_servers"] = os.getenv("LOG_KAFKA_SERVERS", yaml_config.get("LOG_KAFKA_SERVERS"))
    config["kafka_topic"] = os.getenv("LOG_KAFKA_TOPIC", yaml_config.get("LOG_KAFKA_TOPIC", "logs"))
    config["schema_registry_url"] = os.getenv("LOG_SCHEMA_REGISTRY", yaml_config.get("LOG_SCHEMA_REGISTRY"))
    config["schema_compatibility"] = os.getenv("LOG_SCHEMA_COMPATIBILITY", yaml_config.get("LOG_SCHEMA_COMPATIBILITY", "BACKWARD"))

    # remote request settings
    config["remote_timeout"] = int(os.getenv("LOG_REMOTE_TIMEOUT", yaml_config.get("LOG_REMOTE_TIMEOUT", 5)))
    config["max_remote_retries"] = int(os.getenv("LOG_REMOTE_RETRIES", yaml_config.get("LOG_REMOTE_RETRIES", 3)))

    # remote headers
    env_headers = os.getenv("LOG_REMOTE_HEADERS", None)

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
