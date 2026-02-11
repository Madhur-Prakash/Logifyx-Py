import os
import yaml
from dotenv import load_dotenv

load_dotenv()

RUNTIME_CONFIG_FILE = ".logify.runtime.json"
CONFIG_FILE = "logify.yaml"


def load_config():
    config = {}

    # Auto-load logify.yaml if it exists
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f) or {}

    config["level"] = os.getenv("LOG_LEVEL", config.get("LOG_LEVEL", "INFO"))
    config["color"] = os.getenv("LOG_COLOR", str(config.get("LOG_COLOR", False))) == "True"
    config["max_bytes"] = int(os.getenv("LOG_MAX_BYTES", config.get("LOG_MAX_BYTES", 10_000_000)))
    config["backup_count"] = int(os.getenv("LOG_BACKUP_COUNT", config.get("LOG_BACKUP_COUNT", 5)))
    config["log_dir"] = os.getenv("LOG_DIR", config.get("LOG_DIR", "logs"))
    config["file"] = os.getenv("LOG_FILE", config.get("LOG_FILE", "app.log"))
    config["mode"] = os.getenv("LOG_MODE", config.get("LOG_MODE", "dev"))
    config["json"] = os.getenv("LOG_JSON", str(config.get("LOG_JSON", False))) == "True"
    config["mask"] = os.getenv("LOG_MASK", str(config.get("LOG_MASK", True))) == "True"
    config["remote_url"] = os.getenv("LOG_REMOTE", config.get("LOG_REMOTE"))
    return config
