import logging
from pythonjsonlogger import jsonlogger

LEVEL_COLORS = {
    "DEBUG":    "\033[36m",
    "INFO":     "\033[32m",
    "WARNING":  "\033[33m",
    "ERROR":    "\033[31m",
    "CRITICAL": "\033[1;31m",
}
RESET  = "\033[0m"
BLUE   = "\033[34m"
WHITE  = "\033[97m"


def _format_line(record, datefmt, color=True):
    dt = logging.Formatter(datefmt=datefmt).formatTime(record, datefmt)
    level_color = LEVEL_COLORS.get(record.levelname, "")
    level = record.levelname.ljust(8)

    if color:
        colored_level    = f"{level_color}{level}{RESET}"
        colored_location = f"{BLUE}{record.name}{WHITE}:{BLUE}{record.funcName}:{record.lineno}{RESET}"
        colored_message  = f"{level_color}{record.getMessage()}{RESET}"
        colored_dt = f"\033[32m{dt}{RESET}"
        return f"{colored_dt} | {colored_level} | {colored_location} - {colored_message}"

    location = f"{record.name}:{record.funcName}:{record.lineno}"
    return f"{dt} | {level} | {location} - {record.getMessage()}"


class LogifyxFormatter(logging.Formatter):
    """Default formatter: entire line colored by level."""

    def format(self, record):
        return _format_line(record, self.datefmt, color=True)


class PlainLogifyxFormatter(logging.Formatter):
    """Plain formatter: no color (opt-in via color=False)."""

    def format(self, record):
        return _format_line(record, self.datefmt, color=False)


class CompactJsonFormatter(jsonlogger.JsonFormatter):
    """JSON-mode formatter: entire line colored by level."""

    def format(self, record):
        return _format_line(record, self.datefmt, color=True)


def get_formatter(json_mode=False, color=True):
    datefmt = "%Y-%m-%d %H:%M:%S"

    if json_mode:
        formatter = CompactJsonFormatter()
        formatter.datefmt = datefmt
        return formatter

    if not color:
        return PlainLogifyxFormatter(datefmt=datefmt)

    return LogifyxFormatter(datefmt=datefmt)
