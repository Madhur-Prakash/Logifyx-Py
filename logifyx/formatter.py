import json
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


def _append_traceback(formatter, record, line):
    """
    Append exception and stack text to a formatted line.

    Mirrors logging.Formatter.format's own tail handling, which the custom
    format() overrides below would otherwise skip — without this,
    logger.exception() writes the message and silently drops the traceback.
    """
    if record.exc_info and not record.exc_text:
        record.exc_text = formatter.formatException(record.exc_info)

    if record.exc_text:
        if line[-1:] != "\n":
            line += "\n"
        line += record.exc_text

    if record.stack_info:
        if line[-1:] != "\n":
            line += "\n"
        line += formatter.formatStack(record.stack_info)

    return line


class LogifyxFormatter(logging.Formatter):
    """Default formatter: entire line colored by level."""

    def format(self, record):
        return _append_traceback(
            self, record, _format_line(record, self.datefmt, color=True)
        )


class PlainLogifyxFormatter(logging.Formatter):
    """Plain formatter: no color (opt-in via color=False)."""

    def format(self, record):
        return _append_traceback(
            self, record, _format_line(record, self.datefmt, color=False)
        )


_STANDARD_RECORD_ATTRS = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "thread", "threadName", "taskName",
})


class CompactJsonFormatter(jsonlogger.JsonFormatter):
    """JSON-mode formatter: single-line JSON object per record."""

    def format(self, record):
        dt = logging.Formatter(datefmt=self.datefmt).formatTime(record, self.datefmt)
        func = record.filename.replace(".py", "") if record.funcName == "<module>" else record.funcName
        out = {
            "timestamp": dt,
            "level":     record.levelname,
            "logger":    record.name,
            "function":  func,
            "line":      record.lineno,
            "message":   record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                out[key] = value

        # Tracebacks: json.dumps escapes the newlines, so the record stays on
        # one line and the output remains parseable line-by-line.
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            out["exception"] = record.exc_text
        if record.stack_info:
            out["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(out, ensure_ascii=False, default=str)


def get_formatter(json_mode=False, color=True):
    datefmt = "%Y-%m-%d %H:%M:%S"

    if json_mode:
        formatter = CompactJsonFormatter()
        formatter.datefmt = datefmt
        return formatter

    if color is False:
        return PlainLogifyxFormatter(datefmt=datefmt)

    return LogifyxFormatter(datefmt=datefmt)
