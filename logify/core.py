import logging
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
        json_mode=None,
        remote_url=None,
        log_dir=None,
        mask=True,
        color=None,
        backup_count=None,
        max_bytes=None,
        file=None,
        kafka_servers=None,
        kafka_topic=None,
        schema_registry_url=None,
        schema_compatibility=None
    ):

        self.name = name

        self.config = load_config()  # auto-loads logify.yaml + env

        # update with preset if provided (only if preset is valid, otherwise ignore)
        if mode and mode in MODES:
            self.config.update(MODES[mode])
            self.config["mode"] = mode

        overrides = {
            "log_dir": log_dir,
            "remote_url": remote_url,
            "backup_count": backup_count,
            "max_bytes": max_bytes,
            "file": file,
            "color": color,
            "level": level,
            "json_mode": json_mode,
            "kafka_servers": kafka_servers,
            "kafka_topic": kafka_topic,
            "schema_registry_url": schema_registry_url,
            "schema_compatibility": schema_compatibility,
        }

        for key, value in overrides.items():
            if value is not None:
                self.config[key] = value

        # Resolve conflicts
        if self.config.get("json_mode") and self.config.get("color"):
            # JSON mode disables color
            self.config["json_mode"] = False # set json_mode to False if both are True, as both cannot be True at the same time


        self.config["mask"] = mask
        self.logger = self._build()


    def _build(self):
        logger = logging.getLogger(self.name)

        if logger.handlers:
            return logger
        
        logger.propagate = False # prevent duplicate logs
        logging.raiseExceptions = False if self.config.get("mode") == "prod" else True # in prod, don't raise exceptions for logging errors (like file permission issues), just fail silently. In dev, raise them to alert the developer.

        logger.setLevel(self.config["level"])

        for handler in get_handlers(self.config):

            # Console → allow color (but not file handlers which inherit from StreamHandler)
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                formatter = get_formatter(
                    self.config.get("json_mode"),
                    self.config.get("color")
                )

            # File / Remote → no color
            else:
                formatter = get_formatter(
                    self.config.get("json_mode"),
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
