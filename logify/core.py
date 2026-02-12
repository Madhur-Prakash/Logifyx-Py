import logging
from typing import Optional

from .config import load_config
from .presets import MODES
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


class Logify:

    def __new__(
        cls,
        name: str = "app",
        mode: Optional[str] = None,
        level: Optional[int] = None,
        json_mode: Optional[bool] = None,
        remote_url: Optional[str] = None,
        log_dir: Optional[str] = None,
        mask: bool = True,
        color: Optional[bool] = None,
        backup_count: Optional[int] = None,
        max_bytes: Optional[int] = None,
        file: Optional[str] = None,
        kafka_servers: Optional[str] = None,
        kafka_topic: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        schema_compatibility: Optional[str] = None,
        remote_timeout: Optional[int] = None,
        max_remote_retries: Optional[int] = None,
        remote_headers: Optional[dict] = None,
    ) -> logging.Logger:

        # Load config
        config = load_config()

        # Apply preset
        if mode and mode in MODES:
            config.update(MODES[mode])
            config["mode"] = mode

        # Apply overrides
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
            "remote_timeout": remote_timeout,
            "max_remote_retries": max_remote_retries,
            "remote_headers": remote_headers,
        }

        for key, value in overrides.items():
            if value is not None:
                config[key] = value

        if config.get("json_mode") and config.get("color"):
            config["json_mode"] = False

        config["mask"] = mask

        # 🔥 Call builder method
        return cls._build(name, config)

    @staticmethod
    def _build(name: str, config: dict) -> logging.Logger:
        """
        Builds and configures the logger.
        """

        logger = logging.getLogger(name)

        if logger.handlers:
            return logger

        logger.propagate = False
        logging.raiseExceptions = (False if config.get("mode") == "prod" else True)

        logger.setLevel(config["level"])

        for handler in get_handlers(config):

            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                formatter = get_formatter(
                    config.get("json_mode"),
                    config.get("color"),
                )
            else:
                formatter = get_formatter(
                    config.get("json_mode"),
                    False,
                )

            handler.setLevel(config["level"])
            handler.setFormatter(formatter)

            if config.get("mask"):
                handler.addFilter(MaskFilter())

            logger.addHandler(handler)

        return logger
