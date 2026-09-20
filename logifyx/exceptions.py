"""
Logifyx exception hierarchy.

Every exception raised deliberately by Logifyx derives from :class:`LogifyxError`,
so applications can catch all configuration problems with a single except clause::

    from logifyx import LogifyxError, configure_logging

    try:
        configure_logging(output="file", log_file="/root/denied/app.log")
    except LogifyxError as exc:
        print(f"logging setup failed: {exc}")

The concrete subclasses also inherit from the builtin exception type Logifyx
used before this hierarchy existed (``ValueError`` / ``RuntimeError``), so code
written against older releases keeps working unchanged.
"""


class LogifyxError(Exception):
    """Base class for every error raised by Logifyx."""


class LogifyxConfigurationError(LogifyxError, ValueError):
    """
    A configuration value is missing, malformed, or contradictory.

    Also a ``ValueError`` for backward compatibility with releases that raised
    plain ``ValueError`` for bad configuration.
    """


class LogifyxFileError(LogifyxError, RuntimeError):
    """
    A log file or its directory could not be created or opened.

    Also a ``RuntimeError`` for backward compatibility with releases that raised
    ``RuntimeError("Cannot create log directory: ...")``.
    """


__all__ = ["LogifyxError", "LogifyxConfigurationError", "LogifyxFileError"]
