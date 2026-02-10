import logging
from logging.handlers import RotatingFileHandler
from .remote import RemoteHandler


def get_handlers(config):

    handlers = []

    file_handler = RotatingFileHandler(
        config["file"],
        maxBytes=10_000_000,
        backupCount=5
    )

    handlers.append(file_handler)

    console = logging.StreamHandler()
    handlers.append(console)

    if config.get("remote_url"):
        handlers.append(RemoteHandler(config["remote_url"]))

    return handlers
