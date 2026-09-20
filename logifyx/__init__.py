from importlib.metadata import PackageNotFoundError, version as _package_version

from .core import (
    Logifyx,
    ContextLoggerAdapter,
    get_logify_logger,
    setup_logify,
    configure_logging,
    reset_logging,
    get_global_config,
    shutdown,
    flush,
)
from .exceptions import LogifyxError, LogifyxConfigurationError, LogifyxFileError
from .output import BOTH, CONSOLE, FILE, NONE, VALID_OUTPUTS

try:
    #: Installed distribution version. pyproject.toml stays the single source
    #: of truth — this reads it back rather than duplicating the number here.
    __version__ = _package_version("logifyx")
except PackageNotFoundError:          # running from a source tree, not installed
    __version__ = "0.0.0.dev0"


__all__ = [
    "__version__",
    "Logifyx",
    "ContextLoggerAdapter",
    "get_logify_logger",
    "setup_logify",
    "configure_logging",
    "reset_logging",
    "get_global_config",
    "shutdown",
    "flush",
    "LogifyxError",
    "LogifyxConfigurationError",
    "LogifyxFileError",
    "CONSOLE",
    "FILE",
    "BOTH",
    "NONE",
    "VALID_OUTPUTS",
]
