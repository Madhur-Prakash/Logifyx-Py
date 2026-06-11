import logging
from pythonjsonlogger import jsonlogger
import colorlog

class LogifyxFormatter(logging.Formatter):
    def format(self, record):
        dt = self.formatTime(record, self.datefmt)
        level = record.levelname.ljust(8)
        location = f"{record.name}:{record.funcName}:{record.lineno}"
        return f"{dt} | {level} | {location} - {record.getMessage()}"


class CompactJsonFormatter(jsonlogger.JsonFormatter):
    def format(self, record):
        dt = self.formatTime(record, self.datefmt)
        level = record.levelname.ljust(8)
        location = f"{record.name}:{record.funcName}:{record.lineno}"
        return f"{dt} | {level} | {location} - {record.getMessage()}"


def get_formatter(json_mode=False, color=False):
    datefmt = "%Y-%m-%d %H:%M:%S"

    if json_mode:
        formatter = CompactJsonFormatter()
        formatter.datefmt = datefmt
        return formatter

    if color:
        return colorlog.ColoredFormatter(
            "%(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt=datefmt,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red"
            }
        )

    formatter = LogifyxFormatter(datefmt=datefmt)
    return formatter
