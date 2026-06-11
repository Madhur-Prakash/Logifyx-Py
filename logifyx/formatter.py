import logging
from pythonjsonlogger import jsonlogger
import colorlog

LEVEL_COLORS = {
    "DEBUG":    "\033[36m",      # cyan
    "INFO":     "\033[32m",      # green
    "WARNING":  "\033[33m",      # yellow
    "ERROR":    "\033[31m",      # red
    "CRITICAL": "\033[1;31m",    # bold red
}
RESET = "\033[0m"


class LogifyxFormatter(logging.Formatter):
    """Default formatter: only the level name is colored."""

    def format(self, record):
        dt = self.formatTime(record, self.datefmt)
        color = LEVEL_COLORS.get(record.levelname, "")
        level = f"{color}{record.levelname.ljust(8)}{RESET}"
        location = f"{record.name}:{record.funcName}:{record.lineno}"
        return f"{dt} | {level} | {location} - {record.getMessage()}"


class CompactJsonFormatter(jsonlogger.JsonFormatter):
    """JSON-mode formatter: only the level name is colored."""

    def format(self, record):
        dt = self.formatTime(record, self.datefmt)
        color = LEVEL_COLORS.get(record.levelname, "")
        level = f"{color}{record.levelname.ljust(8)}{RESET}"
        location = f"{record.name}:{record.funcName}:{record.lineno}"
        return f"{dt} | {level} | {location} - {record.getMessage()}"


def get_formatter(json_mode=False, color=False):
    datefmt = "%Y-%m-%d %H:%M:%S"

    if json_mode:
        formatter = CompactJsonFormatter()
        formatter.datefmt = datefmt
        return formatter

    if color:
        # Entire line is colored
        return colorlog.ColoredFormatter(
            "%(asctime)s | %(log_color)s%(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s%(reset)s",
            datefmt=datefmt,
            log_colors={
                "DEBUG":    "cyan",
                "INFO":     "green",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_red",
            },
        )

    # Default: only level name is colored
    return LogifyxFormatter(datefmt=datefmt)
