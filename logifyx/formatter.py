import logging
from pythonjsonlogger import jsonlogger
import colorlog

class CompactJsonFormatter(jsonlogger.JsonFormatter):
    def format(self, record):
        # Build the exact string you want
        log_line = (
            f"{self.formatTime(record, self.datefmt)} - "
            f"{record.name} - "
            f"{record.levelname} - "
            f"{record.getMessage()} - "
            f"{record.pathname} - "
            f"{record.filename} - "
            f"{record.lineno} - "
            f"{record.funcName}"
        )

        # Return as JSON
        return (log_line)

def get_formatter(json_mode=False, color=False):
    datefmt = "%Y-%m-%d %H:%M:%S"
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s - %(filename)s - %(lineno)d - %(funcName)s"

    if json_mode:
        formatter = CompactJsonFormatter()
        formatter.datefmt = datefmt
        return formatter

    if color:
        return colorlog.ColoredFormatter(
            "%(log_color)s" + fmt,
            datefmt=datefmt,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red"
            }
        )

    return logging.Formatter(fmt, datefmt=datefmt)
