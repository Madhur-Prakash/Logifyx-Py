import logging
import json
import os
from .config import load_config
from .presets import MODES
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


class Logify:

    def __init__(
        self,
        name="app",
        mode=None,
        level=None,
        json=None,
        remote_url=None,
        log_dir=None,
        mask=True,
        color=None,
        backup_count=None,
        max_bytes=None,
        file=None
    ):

        self.name = name

        self.config = load_config()  # auto-loads logify.yaml + env

        # update with preset if provided (only if preset is valid, otherwise ignore)
        if mode and mode in MODES:
            self.config.update(MODES[mode])
            self.config["mode"] = mode  # set mode to match the preset

        if log_dir is not None:
            self.config["log_dir"] = log_dir

        
        if remote_url:
            self.config["remote_url"] = remote_url

        if backup_count:
            self.config["backup_count"] = backup_count

        if max_bytes:
            self.config["max_bytes"] = max_bytes

        if file:
            self.config["file"] = file
        
        if color:
            self.config["color"] = color

        if level:
            self.config["level"] = level

        if json is not None:
            self.config["json"] = json

                # Resolve conflicts
        if self.config.get("json") and self.config.get("color"):
            # JSON mode disables color
            self.config["json"] = False # set json to False if both are True, as both cannot be True at the same time


        self.config["mask"] = mask
        self.logger = self._build()


    def _build(self):
        logger = logging.getLogger(self.name)

        if logger.handlers:
            return logger

        logger.setLevel(self.config["level"])

        for handler in get_handlers(self.config):

            # Console → allow color (but not file handlers which inherit from StreamHandler)
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                formatter = get_formatter(
                    self.config.get("json"),
                    self.config.get("color")
                )

            # File / Remote → no color
            else:
                formatter = get_formatter(
                    self.config.get("json"),
                    False
                )

            handler.setLevel(self.config["level"])
            handler.setFormatter(formatter)

            if self.config.get("mask"):
                handler.addFilter(MaskFilter())

            logger.addHandler(handler)

        return logger


    def get_logger(self):
        return self.logger
