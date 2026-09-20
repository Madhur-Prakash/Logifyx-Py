import logging
import os
import warnings
from typing import Optional
from concurrent_log_handler import ConcurrentRotatingFileHandler
from .exceptions import LogifyxFileError
from .output import (
    DEFAULT_OUTPUT,
    ROLE_CONSOLE,
    ROLE_FILE,
    ROLE_KAFKA,
    ROLE_NULL,
    ROLE_REMOTE,
    ensure_log_directory,
    mark_owned,
    normalize_output,
    resolve_log_target,
    writes_to_console,
    writes_to_file,
)
from .remote import RemoteHandler

# Optional Kafka support. The handler class is held in a plain variable rather
# than rebound to None on failure, so a type checker still sees one type here.
KafkaHandler: Optional[type] = None
try:
    from .kafka import KafkaHandler as _KafkaHandler
    KafkaHandler = _KafkaHandler
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False


def build_file_handler(config):
    """
    Create the rotating, process-safe file handler for this config.

    Uses ConcurrentRotatingFileHandler (the same handler Logifyx has always
    used), which takes an inter-process lock around every write, so multiple
    threads *and* multiple processes can share one log file without interleaving
    or corrupting records.

    The target directory — including nested parents such as ``logs/subdir/`` —
    is created automatically.

    Raises:
        LogifyxFileError: the directory or the file itself could not be opened.
    """
    log_dir, filename = resolve_log_target(
        config.get("log_dir"),
        config.get("log_file"),
    )
    ensure_log_directory(log_dir)
    path = os.path.join(log_dir, filename) if log_dir else filename

    try:
        handler = ConcurrentRotatingFileHandler(
            path,
            maxBytes=config["max_bytes"],
            backupCount=config["backup_count"],
            encoding="utf-8",
        )
    except LogifyxFileError:
        raise
    except (OSError, ValueError) as exc:
        raise LogifyxFileError(
            f"Cannot open log file {path!r}: {exc}"
        ) from exc

    return mark_owned(handler, ROLE_FILE)


def validate_file_target(config, probe_file=True):
    """
    Resolve the log destination and prove it is usable, without logging anything.

    Called before any handler exists so that a bad path is reported at the
    configuration call site — the alternative is a misconfigured application
    that looks fine until the first log record disappears.

    Args:
        config:     Resolved config mapping.
        probe_file: Also open the file for append. Skipped when the filename is
                    still a placeholder (each logger names its own file), in
                    which case only the directory is checked, so no stray empty
                    file is left behind.

    Returns:
        The resolved log file path.

    Raises:
        LogifyxFileError: the directory or the file cannot be created/opened.
    """
    log_dir, filename = resolve_log_target(
        config.get("log_dir"),
        config.get("log_file"),
    )
    ensure_log_directory(log_dir)
    path = os.path.join(log_dir, filename) if log_dir else filename

    if probe_file:
        try:
            with open(path, "a", encoding="utf-8"):
                pass
        except OSError as exc:
            raise LogifyxFileError(
                f"Cannot open log file {path!r}: {exc}"
            ) from exc

    return path


def get_handlers(config):
    """
    Build the handler set for a resolved config.

    Which destination handlers exist is decided entirely by ``config["output"]``:

        both     file + console   (default — unchanged from earlier releases)
        file     file only        (nothing is written to stdout/stderr)
        console  console only     (no log file is opened)
        none     neither

    Remote HTTP and Kafka handlers are orthogonal: they are governed by
    ``remote_url`` / ``kafka_servers`` and are unaffected by ``output``.

    Every handler returned is stamped via ``mark_owned`` so that later
    reconfiguration can replace Logifyx's own handlers without disturbing
    handlers the application attached itself.
    """
    output = normalize_output(config.get("output", DEFAULT_OUTPUT))

    handlers = []

    if writes_to_file(output):
        handlers.append(build_file_handler(config))

    if writes_to_console(output):
        handlers.append(mark_owned(logging.StreamHandler(), ROLE_CONSOLE))

    if config.get("remote_url"):
        handlers.append(mark_owned(
            RemoteHandler(
                config["remote_url"],
                config["remote_timeout"],
                config["max_remote_retries"],
                config["remote_headers"],
            ),
            ROLE_REMOTE,
        ))

    # Kafka handler with Avro + Schema Registry
    if config.get("kafka_servers") and KAFKA_AVAILABLE:
        handlers.append(mark_owned(
            KafkaHandler(
                bootstrap_servers=config["kafka_servers"],
                topic=config.get("kafka_topic", "logs"),
                schema_registry_url=config.get("schema_registry_url"),
                schema_compatibility=config.get("schema_compatibility", "BACKWARD"),
            ),
            ROLE_KAFKA,
        ))
    elif config.get("kafka_servers") and not KAFKA_AVAILABLE:
        warnings.warn(
            "Kafka logging requested but kafka dependencies not installed. "
            "Install with: pip install kafka-python fastavro",
            RuntimeWarning
        )

    if not handlers:
        # With zero handlers, Python's logging falls back to `lastResort`, which
        # prints WARNING and above to stderr. That would break the promise that
        # output="none" emits nothing, so absorb records explicitly.
        handlers.append(mark_owned(logging.NullHandler(), ROLE_NULL))

    return handlers
