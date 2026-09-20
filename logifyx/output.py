"""
Output destinations and handler ownership.

Two concerns live here, both of which the rest of the package depends on and
neither of which may import back into :mod:`logifyx.core` (keeps the import
graph acyclic: ``exceptions -> output -> handler -> core``).

1. **Output modes** — the ``console`` / ``file`` / ``both`` / ``none`` vocabulary
   that decides which destination handlers get built.

2. **Handler ownership** — every handler Logifyx creates is stamped with an
   owner marker and a role. Reconfiguration only ever touches stamped handlers,
   so handlers an application (or a third-party library) attached itself are
   never removed or reformatted. Roles are used instead of ``isinstance``
   checks because ``FileHandler`` subclasses ``StreamHandler``, which makes
   isinstance-based dispatch silently misclassify file handlers as console ones.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from .exceptions import LogifyxConfigurationError, LogifyxFileError

# --------------------------------------------------------------------------- #
# Output modes
# --------------------------------------------------------------------------- #

CONSOLE = "console"
FILE = "file"
BOTH = "both"
NONE = "none"

#: Canonical output modes, in documentation order.
VALID_OUTPUTS: Tuple[str, ...] = (CONSOLE, FILE, BOTH, NONE)

#: Logifyx has always written to console *and* file, so that stays the default.
DEFAULT_OUTPUT = BOTH

# Friendly spellings accepted in Python kwargs, env vars, and YAML.
_OUTPUT_ALIASES = {
    CONSOLE: CONSOLE,
    "console_only": CONSOLE,
    "console-only": CONSOLE,
    "terminal": CONSOLE,
    FILE: FILE,
    "file_only": FILE,
    "file-only": FILE,
    BOTH: BOTH,
    "console_and_file": BOTH,
    "console-and-file": BOTH,
    "file_and_console": BOTH,
    "all": BOTH,
    NONE: NONE,
    "off": NONE,
    "disabled": NONE,
    "silent": NONE,
}


def normalize_output(value, source: str = "output") -> str:
    """
    Map any accepted spelling of an output mode onto its canonical form.

    ``None`` resolves to the default mode (``"both"``), so callers can pass a
    missing config value straight through.

    Args:
        value:  The mode to normalize. Case-insensitive; surrounding whitespace
                is ignored. Accepts the canonical names plus the ``*_only`` /
                ``console_and_file`` / ``off`` aliases.
        source: Name used in the error message — the kwarg or env var the value
                came from.

    Raises:
        LogifyxConfigurationError: value is not a string or not a known mode.
    """
    if value is None:
        return DEFAULT_OUTPUT
    if not isinstance(value, str):
        raise LogifyxConfigurationError(
            f"{source} must be one of {list(VALID_OUTPUTS)}, "
            f"got {value!r} ({type(value).__name__})"
        )

    canonical = _OUTPUT_ALIASES.get(value.strip().lower().replace(" ", "_"))
    if canonical is None:
        raise LogifyxConfigurationError(
            f"{source} must be one of {list(VALID_OUTPUTS)}, got {value!r}"
        )
    return canonical


def writes_to_console(output: str) -> bool:
    """True when the given mode should produce a console handler."""
    return output in (CONSOLE, BOTH)


def writes_to_file(output: str) -> bool:
    """True when the given mode should produce a file handler."""
    return output in (FILE, BOTH)


# --------------------------------------------------------------------------- #
# Handler ownership
# --------------------------------------------------------------------------- #

ROLE_CONSOLE = "console"
ROLE_FILE = "file"
ROLE_REMOTE = "remote"
ROLE_KAFKA = "kafka"
ROLE_QUEUE = "queue"
ROLE_NULL = "null"

_OWNED_ATTR = "_logifyx_managed"
_ROLE_ATTR = "_logifyx_role"


def mark_owned(handler: logging.Handler, role: str) -> logging.Handler:
    """Stamp a handler as Logifyx-managed and record what it is for."""
    setattr(handler, _OWNED_ATTR, True)
    setattr(handler, _ROLE_ATTR, role)
    return handler


def is_owned(handler: logging.Handler) -> bool:
    """True only for handlers Logifyx created itself."""
    return getattr(handler, _OWNED_ATTR, False) is True


def role_of(handler: logging.Handler) -> Optional[str]:
    """The role a Logifyx handler was created for, or ``None`` if foreign."""
    return getattr(handler, _ROLE_ATTR, None)


def owned_handlers(logger: logging.Logger) -> List[logging.Handler]:
    """Handlers on ``logger`` that Logifyx created (safe to replace)."""
    return [h for h in logger.handlers if is_owned(h)]


# --------------------------------------------------------------------------- #
# Log file path resolution
# --------------------------------------------------------------------------- #


DEFAULT_LOG_FILE = "app.log"


def resolve_log_target(
    log_dir: Optional[str],
    log_file: Optional[str],
) -> Tuple[str, str]:
    """
    Resolve the directory and filename a file handler should write to.

    ``log_file`` is the single source of truth for the log file's location:

    * ``log_file="logs/app.log"``  -> ``("logs", "app.log")`` — ``log_dir`` unused
    * ``log_file="app.log"``       -> ``(log_dir, "app.log")`` — no directory part,
      so it lands inside ``log_dir``. This is what lets ``LOG_DIR`` be set once per
      environment while each logger still names its own file.
    * ``log_file=None``            -> ``(log_dir, "app.log")``

    Returns:
        ``(directory, filename)``. The directory may be ``""`` when the file
        should land in the current working directory.

    Raises:
        LogifyxConfigurationError: the resulting path has no filename component.
    """
    if not log_file:
        return (log_dir or ""), DEFAULT_LOG_FILE

    candidate = Path(str(log_file)).expanduser()
    filename = candidate.name
    if not filename:
        raise LogifyxConfigurationError(
            f"log_file must include a file name, got {log_file!r}"
        )

    parent = str(candidate.parent)
    # Path("app.log").parent is Path("."), which means "put it in log_dir".
    directory = parent if parent not in ("", ".") else (log_dir or "")
    return directory, filename


def ensure_log_directory(directory: str) -> None:
    """
    Create the log directory, including any missing parents.

    Users never have to pre-create ``logs/`` or ``logs/subdir/``.

    Raises:
        LogifyxFileError: the directory could not be created, or a non-directory
        already occupies the path.
    """
    if not directory:
        return
    try:
        os.makedirs(directory, exist_ok=True)
    except PermissionError as exc:
        raise LogifyxFileError(
            f"Cannot create log directory {directory!r}: permission denied. "
            f"Choose a writable log_dir/log_file, or pre-create the directory."
        ) from exc
    except OSError as exc:
        raise LogifyxFileError(
            f"Cannot create log directory {directory!r}: {exc}"
        ) from exc

    if not os.path.isdir(directory):
        raise LogifyxFileError(
            f"Log directory {directory!r} exists but is not a directory."
        )


__all__ = [
    "CONSOLE",
    "FILE",
    "BOTH",
    "NONE",
    "VALID_OUTPUTS",
    "DEFAULT_OUTPUT",
    "normalize_output",
    "writes_to_console",
    "writes_to_file",
    "ROLE_CONSOLE",
    "ROLE_FILE",
    "ROLE_REMOTE",
    "ROLE_KAFKA",
    "ROLE_QUEUE",
    "ROLE_NULL",
    "mark_owned",
    "is_owned",
    "role_of",
    "owned_handlers",
    "DEFAULT_LOG_FILE",
    "resolve_log_target",
    "ensure_log_directory",
]
