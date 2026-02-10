import logging
from pythonjsonlogger import jsonlogger
import colorlog


def get_formatter(json_mode=False, color=False):

    if json_mode:
        return jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )

    fmt = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

    if color:
        return colorlog.ColoredFormatter(
            "%(log_color)s" + fmt,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red"
            }
        )

    return logging.Formatter(fmt)
