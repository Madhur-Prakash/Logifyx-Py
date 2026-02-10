import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from .remote import RemoteHandler
import os


def get_handlers(config):

    try:
        log_dir = config['log_dir']
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        raise RuntimeError(f"Cannot create log directory: {log_dir}")

    handlers = []

    file_handler = ConcurrentRotatingFileHandler(
        os.path.join(log_dir, config["file"]),
        maxBytes=config["max_bytes"],
        backupCount=config["backup_count"]
    )

    handlers.append(file_handler)

    console = logging.StreamHandler()
    handlers.append(console)

    if config.get("remote_url"):
        handlers.append(RemoteHandler(config["remote_url"]))

    return handlers
