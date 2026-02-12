import logging
from typing import Optional
import threading
from .config import load_config
from .presets import MODES
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


class Logify(logging.Logger):

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
        schema_compatibility=None,
        remote_timeout=None,
        max_remote_retries=None,
        remote_headers=None
    ):

        # Create reload lock FIRST
        self._reload_lock = threading.RLock()  # RLock safer than Lock

        # Load base config
        self.config = load_config()

        # Apply preset
        if mode and mode in MODES:
            self.config.update(MODES[mode])
            self.config["mode"] = mode

        overrides = {
            "log_dir": log_dir,
            "remote_url": remote_url,
            "backup_count": backup_count,
            "max_bytes": max_bytes,
            "file": file,
            "mask": mask,
            "color": color,
            "level": level,
            "json_mode": json_mode,
            "kafka_servers": kafka_servers,
            "kafka_topic": kafka_topic,
            "schema_registry_url": schema_registry_url,
            "schema_compatibility": schema_compatibility,
            "remote_timeout": remote_timeout,
            "max_remote_retries": max_remote_retries,
            "remote_headers": remote_headers
        }

        # Apply overrides
        for key, value in overrides.items():
            if value is not None:
                self.config[key] = value

        # Conflict resolution
        if self.config.get("json_mode") and self.config.get("color"):
            # JSON mode disables color
            self.config["json_mode"] = False # set json_mode to False if both are True, as both cannot be True at the same time

        final_level = self.config.get("level", logging.INFO)

        super().__init__(name, final_level)

        if logging.getLogger(self.name).handlers:
            return

        self.propagate = False # prevent duplicate logs
        logging.raiseExceptions = False if self.config.get("mode") == "prod" else True # in prod, don't raise exceptions for logging errors (like file permission issues), just fail silently. In dev, raise them to alert the developer.

        self._build()

    def _build(self) -> None:

        for handler in get_handlers(self.config):

            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                formatter = get_formatter(
                    self.config.get("json_mode"),
                    self.config.get("color"),
                )
            else:
                formatter = get_formatter(
                    self.config.get("json_mode"),
                    False,
                )

            handler.setLevel(self.level)
            handler.setFormatter(formatter)

            if self.config.get("mask"):
                handler.addFilter(MaskFilter())

            self.addHandler(handler)

    def reload(self):
        with self._reload_lock:
            # Remove existing handlers safely
            for handler in self.handlers[:]:
                self.removeHandler(handler)
                handler.close()

            # Update logger level
            self.setLevel(self.config.get("level", logging.INFO))

            # Reapply propagation & exception behavior
            self.propagate = False
            logging.raiseExceptions = (False if self.config.get("mode") == "prod" else True)

            # Rebuild handlers
            self._build()


    def reload_from_file(self):
        with self._reload_lock:
            self.config = load_config()
            self.reload()

