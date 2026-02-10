import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(config_file=None):
    config = {}

    if config_file and os.path.exists(config_file):
        with open(config_file) as f:
            config = yaml.safe_load(f)

    config["level"] = os.getenv("LOG_LEVEL", config.get("level", "INFO"))
    config["color"] = os.getenv("LOG_COLOR", str(config.get("color", False))) == "True"
    config["max_bytes"] = int(os.getenv("LOG_MAX_BYTES", config.get("max_bytes", 10_000_000)))
    config["backup_count"] = int(os.getenv("LOG_BACKUP_COUNT", config.get("backup_count", 5)))
    config["log_dir"] = os.getenv("LOG_DIR", config.get("log_dir", "logs"))
    config["file"] = os.getenv("LOG_FILE", config.get("file", "app.log"))
    config["mode"] = os.getenv("LOG_MODE", config.get("mode", "dev"))
    config["json"] = os.getenv("LOG_JSON", str(config.get("json", False))) == "True"
    config["mask"] = os.getenv("LOG_MASK", str(config.get("mask", True))) == "True"
    config["remote_url"] = os.getenv("LOG_REMOTE", config.get("remote_url"))

    return config
