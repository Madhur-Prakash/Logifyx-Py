import logging

from .config import load_config
from .presets import PRESETS
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


class Logify:

    def __init__(
        self,
        name="app",
        config_file=None,
        preset=None,
        level=None,
        json=None,
        mask=True
    ):

        self.name = name

        self.config = load_config(config_file)

        if preset and preset in PRESETS:
            self.config.update(PRESETS[preset])

        if level:
            self.config["level"] = level

        if json is not None:
            self.config["json"] = json

        self.config["mask"] = mask

        self.logger = self._build()

    def _build(self):

        logger = logging.getLogger(self.name)

        if logger.handlers:
            return logger

        logger.setLevel(self.config["level"])

        formatter = get_formatter(
            self.config.get("json"),
            self.config.get("color")
        )

        for handler in get_handlers(self.config):

            handler.setLevel(self.config["level"])
            handler.setFormatter(formatter)

            if self.config.get("mask"):
                handler.addFilter(MaskFilter())

            logger.addHandler(handler)

        return logger

    def get_logger(self):
        return self.logger
