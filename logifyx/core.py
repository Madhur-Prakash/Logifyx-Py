import logging
from logging.handlers import QueueHandler, QueueListener
import time
from typing import Optional, Dict, Any, List, Union
import threading
import queue
import atexit
import weakref
from .config import load_config, _clear_path_warnings
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers, validate_file_target
from .exceptions import LogifyxConfigurationError
from .output import (
    DEFAULT_OUTPUT,
    ROLE_CONSOLE,
    ROLE_KAFKA,
    ROLE_NULL,
    ROLE_QUEUE,
    ROLE_REMOTE,
    is_owned,
    mark_owned,
    normalize_output,
    owned_handlers,
    role_of,
    writes_to_file,
)


# Sentinel object to detect if a parameter was explicitly passed
_sentinel = object()

# Valid logging levels
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"}


def _normalize_and_validate_level(level: Union[int, str]) -> Union[int, str]:
    """Normalize level string to uppercase and validate it."""
    if isinstance(level, str):
        level_upper = level.upper()
        if level_upper not in _VALID_LEVELS:
            raise LogifyxConfigurationError(
                f"Invalid log level: {level!r}. Must be one of: {', '.join(sorted(_VALID_LEVELS))}"
            )
        return level_upper
    return level


# Global queue and listener for async remote/kafka handling
_log_queue: queue.Queue = queue.Queue(maxsize=10_00_000)  # Large maxsize to prevent blocking in high-throughput scenarios
_queue_listener: Optional[QueueListener] = None
_listener_lock = threading.Lock()
_atexit_registered = False

_async_handlers: List[logging.Handler] = []

_global_overrides: Dict[str, Any] = {}
_global_lock = threading.RLock()

_instances: "weakref.WeakSet" = weakref.WeakSet()

_init_kwargs: Dict[str, dict] = {}


def _default_log_file(name: str) -> str:
    base_name = (name or "app").strip() or "app"
    return base_name if base_name.lower().endswith(".log") else f"{base_name}.log"


def _rebuild_listener_locked() -> None:
    """Restart the listener over the current _async_handlers. Caller holds the lock."""
    global _queue_listener, _atexit_registered

    if _queue_listener is not None:
        _queue_listener.stop()
        _queue_listener = None

    if _async_handlers:
        _queue_listener = QueueListener(
            _log_queue,
            *_async_handlers,
            respect_handler_level=True
        )
        _queue_listener.start()

        # Register atexit handler to flush remaining logs on exit
        if not _atexit_registered:
            atexit.register(_flush_and_stop_listener)
            _atexit_registered = True


def _register_async_handlers(handlers: list) -> None:
    """Add async handlers (remote, kafka) to the shared background listener."""
    if not handlers:
        return
    with _listener_lock:
        for handler in handlers:
            if handler not in _async_handlers:
                _async_handlers.append(handler)
        _rebuild_listener_locked()


def _unregister_async_handlers(handlers: list) -> None:
    """Detach async handlers from the listener, leaving other loggers' intact."""
    if not handlers:
        return
    with _listener_lock:
        for handler in handlers:
            if handler in _async_handlers:
                _async_handlers.remove(handler)
        _rebuild_listener_locked()


def _start_queue_listener(handlers: list) -> None:
    """Start background listener for async handlers (remote, kafka)."""
    _register_async_handlers(handlers)


def _flush_and_stop_listener() -> None:
    """Flush remaining logs and stop listener on program exit."""
    global _queue_listener
    with _listener_lock:
        if _queue_listener:
            # Stop the listener - this waits for the thread to finish
            # processing remaining items and join
            _queue_listener.stop()
            _queue_listener = None
        _async_handlers.clear()


def _stop_queue_listener() -> None:
    """Stop background listener gracefully."""
    global _queue_listener
    with _listener_lock:
        if _queue_listener:
            _queue_listener.stop()
            _queue_listener = None
        _async_handlers.clear()


def flush(timeout: float = 5.0) -> bool:
    """
    Block until the async log queue is empty, then return.

    Remote HTTP and Kafka handlers are async — log calls return instantly and
    the actual network send happens in a background thread. Call flush() before
    your process exits (or before a graceful shutdown) to ensure those buffered
    records are delivered.

    Does not stop the background listener, so logging continues normally
    after flush() returns. For a full teardown use shutdown() instead.

        from logifyx import flush

        flush()           # wait up to 5 s (default)
        flush(timeout=2)  # wait up to 2 s

    Args:
        timeout: Maximum seconds to wait for the queue to drain. Default: 5.0.

    Returns:
        True  — queue emptied within the timeout.
        False — timeout expired with records still pending.
    """
    start = time.time()
    while not _log_queue.empty():
        if time.time() - start > timeout:
            return False
        time.sleep(0.01)
    return True


def shutdown() -> None:
    """
    Flush all pending async log records and stop the background listener.

    Remote HTTP and Kafka records are delivered by a background thread. shutdown()
    waits for that thread to finish sending everything in the queue, then tears it
    down. After this call, any new remote/Kafka log records are dropped.

    shutdown() is registered with atexit automatically, so it runs on normal
    process exit. Call it explicitly only when you need delivery to complete
    before your own cleanup code runs (e.g. before closing a database connection
    that a log handler may reference).

        from logifyx import shutdown

        try:
            run_app()
        finally:
            shutdown()   # guarantee delivery before process teardown
    """
    _flush_and_stop_listener()


_VALID_COMPATIBILITY = {
    "BACKWARD", "BACKWARD_TRANSITIVE",
    "FORWARD",  "FORWARD_TRANSITIVE",
    "FULL",     "FULL_TRANSITIVE",
    "NONE",
}


def _validate_options(
    config_dir=None,
    env_file=None,
    yaml_file=None,
    json_mode=None,
    remote_url=None,
    log_dir=None,
    log_file=None,
    output=None,
    mask=None,
    color=None,
    backup_count=None,
    max_bytes=None,
    kafka_servers=None,
    kafka_topic=None,
    schema_registry_url=None,
    schema_compatibility=None,
    remote_timeout=None,
    max_remote_retries=None,
    remote_headers=None,
    level=None,
) -> None:
    """
    Strictly type-check and range-check Logifyx options.

    Shared by Logifyx.configure() and configure_logging() so both entry points
    reject the same bad input with the same message. ``None`` always means
    "not supplied — fall through to env/YAML/defaults" and is never validated.

    Raises:
        TypeError:  a value has the wrong type.
        ValueError: a value has the right type but an unacceptable value.
                    Output-mode errors raise LogifyxConfigurationError, which
                    is itself a ValueError.
    """
    # str params
    for param, value in (
        ("config_dir",          config_dir),
        ("env_file",            env_file),
        ("yaml_file",           yaml_file),
        ("remote_url",          remote_url),
        ("log_dir",             log_dir),
        ("log_file",            log_file),
        ("kafka_topic",         kafka_topic),
        ("schema_registry_url", schema_registry_url),
    ):
        if value is not None and not isinstance(value, str):
            raise TypeError(
                f"{param} must be a str, got {value!r} ({type(value).__name__})"
            )

    # output — console / file / both / none (aliases accepted)
    if output is not None:
        normalize_output(output, source="output")

    # bool params — True/False only, no strings or ints accepted
    for param, value in (
        ("color",     color),
        ("mask",      mask),
        ("json_mode", json_mode),
    ):
        if value is not None and not isinstance(value, bool):
            raise TypeError(
                f"{param} must be True or False, got {value!r} ({type(value).__name__})"
            )

    # int params — bool subclasses int in Python so explicitly reject those too
    for param, value, min_val in (
        ("max_bytes",         max_bytes,         1),
        ("backup_count",      backup_count,      0),
        ("remote_timeout",    remote_timeout,    1),
        ("max_remote_retries", max_remote_retries, 0),
    ):
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{param} must be an int, got {value!r} ({type(value).__name__})"
                )
            if value < min_val:
                raise LogifyxConfigurationError(
                    f"{param} must be >= {min_val}, got {value!r}"
                )

    # kafka_servers — str ("host:port") or list of str
    if kafka_servers is not None:
        if not isinstance(kafka_servers, (str, list)):
            raise TypeError(
                f"kafka_servers must be a str or list of str, got {kafka_servers!r} ({type(kafka_servers).__name__})"
            )
        if isinstance(kafka_servers, list) and not all(isinstance(s, str) for s in kafka_servers):
            raise TypeError(
                "kafka_servers list must contain only str entries, e.g. ['host1:9092', 'host2:9092']"
            )

    # remote_headers — dict with str keys and str values
    if remote_headers is not None:
        if not isinstance(remote_headers, dict):
            raise TypeError(
                f"remote_headers must be a dict, got {remote_headers!r} ({type(remote_headers).__name__})"
            )
        bad = [(k, v) for k, v in remote_headers.items() if not isinstance(k, str) or not isinstance(v, str)]
        if bad:
            k, v = bad[0]
            raise TypeError(
                f"remote_headers must be Dict[str, str] — key {k!r} ({type(k).__name__}) "
                f"or value {v!r} ({type(v).__name__}) is not a str"
            )

    # schema_compatibility — fixed set of valid values
    if schema_compatibility is not None:
        if not isinstance(schema_compatibility, str):
            raise TypeError(
                f"schema_compatibility must be a str, got {schema_compatibility!r} ({type(schema_compatibility).__name__})"
            )
        if schema_compatibility.upper() not in _VALID_COMPATIBILITY:
            raise LogifyxConfigurationError(
                f"schema_compatibility must be one of {sorted(_VALID_COMPATIBILITY)}, "
                f"got {schema_compatibility!r}"
            )

    # level — str matching a valid level name, or a plain int (not bool)
    if level is not None:
        if isinstance(level, bool):
            raise TypeError(
                f"level must be a log-level str or int, got {level!r} ({type(level).__name__})"
            )
        if isinstance(level, str):
            if level.upper() not in _VALID_LEVELS:
                raise LogifyxConfigurationError(
                    f"level must be one of {sorted(_VALID_LEVELS)}, got {level!r}"
                )
        elif not isinstance(level, int):
            raise TypeError(
                f"level must be a log-level str or int, got {level!r} ({type(level).__name__})"
            )


class Logifyx(logging.Logger):
    """
    Drop-in replacement for logging.Logger with console, file, remote HTTP,
    and Kafka output — plus sensitive-data masking and JSON mode.

    Two ways to create a logger:

    Option 1 — direct instantiation (simplest, no setup required):

        from logifyx import Logifyx

        log = Logifyx("auth", log_dir="logs", color=True)
        log.info("Server started")

    Option 2 — global registration via setup_logify() (recommended for apps
    with multiple modules, because every call to get_logify_logger("auth")
    anywhere in the process returns the same already-configured instance):

        # Once, at the top of main.py / app.py / wsgi.py:
        from logifyx import setup_logify, get_logify_logger
        setup_logify()

        # Anywhere in your codebase:
        log = get_logify_logger("auth", log_dir="logs", color=True)
        log.info("Server started")

    Configuration priority (highest → lowest):
        kwargs passed here  >  environment variables  >  logifyx.yaml  >  built-in defaults

    Omitting a kwarg is not the same as passing None — omitting means "fall through
    to env/yaml/defaults". Passing an explicit value always wins.

    Args:
        name:                 Logger name. Use dot notation for hierarchy ("app.auth").
        level:                Minimum level to emit. Accepts "DEBUG", "INFO", "WARNING",
                              "ERROR", "CRITICAL" (case-insensitive) or a logging int.
                              Default: "INFO".
        output:               Where logs go — "console", "file", "both", or "none".
                              "file" writes to the log file and prints nothing to
                              stdout or stderr. Default: "both" (unchanged behaviour).
        log_file:             Path to the log file, e.g. "logs/app.log". Missing
                              directories are created automatically. A bare file
                              name ("api.log") is placed inside log_dir.
                              Default: "<name>.log".
        log_dir:              Directory used when log_file has no directory part.
                              Default: "logs".
        max_bytes:            Rotate the file when it reaches this many bytes.
                              Default: 10_000_000 (10 MB).
        backup_count:         Number of rotated backup files to keep. Default: 5.
        color:                Colorize console output by level. Default: True.
        json_mode:            Emit each line as a JSON object instead of plain text.
                              Automatically disables color. Default: False.
        mask:                 Redact passwords, tokens, and secrets in all output.
                              Default: True.
        remote_url:           HTTP endpoint to POST log records to. Delivery is async
                              and non-blocking (queue-based). Default: None (disabled).
        remote_timeout:       Seconds before an HTTP send times out. Default: 5.
        max_remote_retries:   Consecutive failures before the remote handler disables
                              itself to avoid blocking. Default: 3.
        remote_headers:       Extra HTTP headers as a dict, e.g.
                              {"Authorization": "Bearer <token>"}. Default: None.
        kafka_servers:        Kafka bootstrap server(s), e.g. "localhost:9092" or
                              "k1:9092,k2:9092". Default: None (disabled).
        kafka_topic:          Kafka topic to produce log records to. Default: "logs".
        schema_registry_url:  Confluent Schema Registry URL for Avro serialization.
                              Default: None (JSON over Kafka instead).
        schema_compatibility: Schema compatibility mode — BACKWARD, FORWARD, FULL,
                              or NONE. Default: "BACKWARD".
        config_dir:           Directory to search for logifyx.yaml. Default: project root.
        env_file:             Path to a .env file to load. Default: ".env".
        yaml_file:            Explicit path to a YAML config file, overrides auto-discovery.
    """
    

    def __init__(
        self,
        name: str = "app",
        level: Union[int, str] = logging.NOTSET,  # Required by Logger base class
        config_dir = _sentinel,
        env_file = _sentinel,
        yaml_file = _sentinel,
        json_mode = _sentinel,
        remote_url = _sentinel,
        log_dir = _sentinel,
        log_file = _sentinel,
        output = _sentinel,
        mask = _sentinel,
        color = _sentinel,
        backup_count = _sentinel,
        max_bytes = _sentinel,
        kafka_servers = _sentinel,
        kafka_topic = _sentinel,
        schema_registry_url = _sentinel,
        schema_compatibility = _sentinel,
        remote_timeout = _sentinel,
        max_remote_retries = _sentinel,
        remote_headers = _sentinel
    ):
        # Normalize and validate level string
        level = _normalize_and_validate_level(level)

        # Initialize base Logger first
        super().__init__(name, level)

        # Skip if already configured (handlers exist = already set up)
        if self.handlers:
            return

        # Create reload lock
        self._reload_lock = threading.RLock()

        # Async handlers this logger contributed to the shared queue listener,
        # tracked so reconfiguration can detach exactly those again.
        self._owned_async_handlers: List[logging.Handler] = []

        # Store init params (only those explicitly provided).
        # `level` is positional on logging.Logger and defaults to NOTSET, so
        # anything else is an explicit choice and must reach configure() —
        # otherwise configure() would overwrite it with the config file value.
        self._init_params = {
            "level": level if level not in (logging.NOTSET, "NOTSET") else _sentinel,
            "config_dir": config_dir,
            "env_file": env_file,
            "yaml_file": yaml_file,
            "json_mode": json_mode,
            "remote_url": remote_url,
            "log_dir": log_dir,
            "log_file": log_file,
            "output": output,
            "mask": mask,
            "color": color,
            "backup_count": backup_count,
            "max_bytes": max_bytes,
            "kafka_servers": kafka_servers,
            "kafka_topic": kafka_topic,
            "schema_registry_url": schema_registry_url,
            "schema_compatibility": schema_compatibility,
            "remote_timeout": remote_timeout,
            "max_remote_retries": max_remote_retries,
            "remote_headers": remote_headers
        }

        # Track this logger so configure_logging() can re-apply settings to it.
        _instances.add(self)

        # If we were constructed by logging.getLogger() (which only passes `name`),
        # get_logify_logger() will have pre-registered the caller's kwargs here
        # so they aren't lost.  Pop atomically so a second call for the same name
        # (which hits the registry cache and never reaches __init__) leaves nothing.
        pre = _init_kwargs.pop(name, None)
        if pre:
            self._init_params.update(pre)

        # Filter out sentinel values - keep only explicitly provided params
        provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}

        # Configure even when no explicit kwargs were passed so zero-config
        # usage still creates handlers and emits INFO-level messages.
        if provided:
            self.configure(**provided)
        else:
            self.configure() # configure with defaults from config file or presets

    def configure(
        self,
        config_dir: Optional[str] = None,
        env_file: Optional[str] = None,
        yaml_file: Optional[str] = None,
        json_mode: Optional[bool] = None,
        remote_url: Optional[str] = None,
        log_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        output: Optional[str] = None,
        mask: Optional[bool] = None,
        color: Optional[bool] = None,
        backup_count: Optional[int] = None,
        max_bytes: Optional[int] = None,
        kafka_servers: Optional[list] = None,
        kafka_topic: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        schema_compatibility: Optional[str] = None,
        remote_timeout: Optional[int] = None,
        max_remote_retries: Optional[int] = None,
        remote_headers: Optional[Dict[str, str]] = None,
        level: Optional[Union[int, str]] = None,
        replace: bool = False
    ) -> "Logifyx":
        """
        Apply configuration options and build handlers.

        You do not need to call this directly — __init__ calls it automatically.
        It is called again by reload() / reload_from_file() and by
        configure_logging() when settings change at runtime.

        Config priority (highest wins):
            kwargs passed here
              >  process-wide defaults from configure_logging()
              >  environment / .env
              >  logifyx.yaml
              >  built-in defaults

        Passing None for a kwarg means "do not override this setting" — the value
        from configure_logging()/env/yaml/defaults is used instead. This differs
        from passing False or an empty string, which are treated as explicit values.

        Special behaviour:
            - Calling configure() on a logger that already has Logifyx handlers is
              a no-op, so repeated calls never stack up duplicate handlers. Pass
              replace=True to tear the Logifyx-owned handlers down and rebuild.
            - Handlers the application attached itself are never counted, removed,
              or reformatted — only Logifyx-owned handlers are managed.
            - If json_mode=True and color=True are both active, json_mode wins and
              color is silently disabled (colorized JSON is not supported).
            - If log_file is not set anywhere, it defaults to "<name>.log"
              inside log_dir.

        Args:
            output:  "console", "file", "both", or "none". "file" suppresses all
                     terminal output. Default: "both".
            log_file: Path to the log file ("logs/app.log"). Parent directories
                     are created as needed. A bare file name goes in log_dir.
            replace: Rebuild Logifyx-owned handlers even if some already exist.

        Returns:
            self — allows method chaining, e.g. Logifyx("x").configure(color=False).
        """
        # Skip if already configured — only Logifyx's own handlers count, so a
        # user-attached handler never blocks (or gets clobbered by) setup.
        if owned_handlers(self) and not replace:
            return self

        # --- strict type validation ---
        _validate_options(
            config_dir=config_dir,
            env_file=env_file,
            yaml_file=yaml_file,
            json_mode=json_mode,
            remote_url=remote_url,
            log_dir=log_dir,
            log_file=log_file,
            output=output,
            mask=mask,
            color=color,
            backup_count=backup_count,
            max_bytes=max_bytes,
            kafka_servers=kafka_servers,
            kafka_topic=kafka_topic,
            schema_registry_url=schema_registry_url,
            schema_compatibility=schema_compatibility,
            remote_timeout=remote_timeout,
            max_remote_retries=max_remote_retries,
            remote_headers=remote_headers,
            level=level,
        )

        if replace:
            self._teardown_owned_handlers()

        globals_ = get_global_config()

        # Load base config — config file locations may themselves be set globally
        self.config = load_config(
            config_dir=config_dir or globals_.get("config_dir"),
            env_file=env_file or globals_.get("env_file"),
            yaml_file=yaml_file or globals_.get("yaml_file"),
        )

        # Layer 1: process-wide defaults from configure_logging()
        for key, value in globals_.items():
            if key in ("config_dir", "env_file", "yaml_file"):
                continue
            self.config[key] = value
        if globals_.get("log_file"):
            self.config["_file_is_default"] = False

        # Layer 2: kwargs passed to this call (most specific, wins)
        overrides = {
            "log_dir": log_dir,
            "log_file": log_file,
            "output": output,
            "remote_url": remote_url,
            "backup_count": backup_count,
            "max_bytes": max_bytes,
            "mask": mask,
            "color": color,
            "level": level,
            "json_mode": json_mode,
            "kafka_servers": kafka_servers,
            "kafka_topic": kafka_topic,
            "schema_registry_url": schema_registry_url,
            "schema_compatibility": schema_compatibility,
            "remote_timeout": remote_timeout,
            "max_remote_retries": max_remote_retries,
            "remote_headers": remote_headers
        }

        # Apply overrides
        for key, value in overrides.items():
            if value is not None:
                self.config[key] = value

        self.config["output"] = normalize_output(self.config.get("output", DEFAULT_OUTPUT))

        if log_file is None and self.config.get("_file_is_default", False):
            # Nothing named the log file, so the logger names it: "<name>.log",
            # resolved inside log_dir.
            self.config["log_file"] = _default_log_file(self.name)

        # Conflict resolution
        if self.config.get("json_mode") and self.config.get("color"):
            self.config["json_mode"] = False

        final_level = self.config.get("level", logging.INFO)
        # Normalize and validate level
        final_level = _normalize_and_validate_level(final_level)
        self.setLevel(final_level)

        self.propagate = False

        self._build()

        return self

    @property
    def output(self) -> str:
        """
        The resolved output mode: "console", "file", "both", or "none".

            log = Logifyx("api", output="file")
            log.output            # "file"
        """
        return getattr(self, "config", {}).get("output", DEFAULT_OUTPUT)

    def set_output(
        self,
        output: str,
        log_file: Optional[str] = None,
        log_dir: Optional[str] = None,
    ) -> "Logifyx":
        """
        Switch this logger's destination at runtime.

        Rebuilds only Logifyx-owned handlers, so switching from "both" to "file"
        removes the console handler and nothing else — handlers the application
        attached stay exactly where they are.

            log = Logifyx("api")            # console + file
            log.set_output("file")          # file only, terminal goes quiet
            log.set_output("file", log_file="logs/api/requests.log")

        Args:
            output:   "console", "file", "both", or "none".
            log_file: Optional new log file path, e.g. "logs/app.log".
            log_dir:  Optional new log directory.

        Returns:
            self — allows chaining.
        """
        normalize_output(output, source="output")
        with self._reload_lock:
            self._init_params["output"] = output
            if log_file is not None:
                self._init_params["log_file"] = log_file
            if log_dir is not None:
                self._init_params["log_dir"] = log_dir
            provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}
            self.configure(replace=True, **provided)
        return self

    def _teardown_owned_handlers(self) -> None:
        """
        Detach and close every Logifyx-created handler on this logger.

        Handlers the application or a third-party library attached are left
        untouched — that is the whole point of the ownership marker.
        """
        for handler in list(self.handlers):
            if not is_owned(handler):
                continue
            self.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                # A handler that fails to close must not abort reconfiguration,
                # and must not be reported through the logging system we are
                # in the middle of rebuilding.
                pass

        async_handlers = getattr(self, "_owned_async_handlers", [])
        if async_handlers:
            # Remove from the shared listener first so the background thread is
            # not holding them while they close.
            _unregister_async_handlers(async_handlers)
            for handler in async_handlers:
                try:
                    handler.close()
                except Exception:
                    pass
            self._owned_async_handlers = []

    def _build(self) -> None:
        """
        Build and attach handlers with queue-based async architecture.

        Handlers are dispatched by their declared role rather than by isinstance:
        FileHandler subclasses StreamHandler, so an isinstance check would treat
        the rotating file handler as a console handler and colorize the log file.
        """
        sync_handlers = []  # Console, file, null
        async_handlers = []  # Remote, Kafka (go through queue)

        json_mode = self.config.get("json_mode")

        for handler in get_handlers(self.config):
            role = role_of(handler)

            if role == ROLE_NULL:
                # Absorbs records so logging's stderr lastResort never fires.
                sync_handlers.append(handler)
                continue

            if role == ROLE_CONSOLE:
                formatter = get_formatter(json_mode, self.config.get("color"))
                sync_handlers.append(handler)
            elif role in (ROLE_REMOTE, ROLE_KAFKA):
                formatter = get_formatter(json_mode, False)
                async_handlers.append(handler)
            else:
                # File handler (and any future non-console sync destination) —
                # never colorized, since escape codes do not belong in a file.
                formatter = get_formatter(json_mode, False)
                sync_handlers.append(handler)

            handler.setLevel(self.level)
            handler.setFormatter(formatter)

            if self.config.get("mask"):
                handler.addFilter(MaskFilter())

        # Add sync handlers directly
        for handler in sync_handlers:
            self.addHandler(handler)

        # Add async handlers via QueueHandler
        if async_handlers:
            queue_handler = QueueHandler(_log_queue)
            queue_handler.setLevel(self.level)
            mark_owned(queue_handler, ROLE_QUEUE)
            self.addHandler(queue_handler)
            _register_async_handlers(async_handlers)
            self._owned_async_handlers = list(async_handlers)

    def _log(self, level, msg, args, **kwargs):
        if args:
            try:
                str(msg) % args
            except (TypeError, ValueError):
                # args don't match any format specifier — append them as a debug suffix
                parts = [repr(a) for a in (args if isinstance(args, tuple) else (args,))]
                msg = f"{msg} {', '.join(parts)}"
                args = ()
        super()._log(level, msg, args, **kwargs)

    def reload(self) -> None:
        """
        Tear down all handlers and reconfigure using the kwargs from __init__.

        Use this to pick up updated environment variables or a changed logifyx.yaml
        without restarting the process. The kwargs you originally passed at creation
        are re-applied on top of the freshly loaded config.

            log = Logifyx("auth", log_dir="logs")
            # edit logifyx.yaml or change an env var at runtime ...
            log.reload()   # drops old handlers, rebuilds with original kwargs + new config

        Only Logifyx-owned handlers are torn down. Handlers your application
        attached to this logger survive the reload untouched.
        """
        with self._reload_lock:
            self._teardown_owned_handlers()

            # Rebuild with provided params
            provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}
            self.configure(replace=True, **provided)

    def reload_from_file(self) -> None:
        """
        Tear down all handlers and reconfigure from logifyx.yaml only.

        Unlike reload(), this does NOT re-apply kwargs passed at creation —
        the fresh config comes entirely from logifyx.yaml and environment variables.
        Use this when you want the config file to be the sole source of truth
        after a config file update, discarding any code-level overrides.

            log = Logifyx("auth", log_dir="custom_logs")  # kwarg is NOT re-applied
            # edit logifyx.yaml ...
            log.reload_from_file()                        # picks up YAML, drops kwarg

        Only Logifyx-owned handlers are torn down. Handlers your application
        attached to this logger survive the reload untouched.
        """
        with self._reload_lock:
            self._teardown_owned_handlers()

            # Reload config and rebuild
            self.config = load_config()
            provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}
            self.configure(replace=True, **provided)


class ContextLoggerAdapter(logging.LoggerAdapter):
    """
    Wraps a Logifyx logger to prepend structured key=value context to every message.

    Pass a dict of context fields at construction time. Every log call through
    the adapter automatically includes those fields — you do not need to repeat
    them on each call.

    Setup: no extra registration needed beyond having a Logifyx logger.

        from logifyx import Logifyx, ContextLoggerAdapter

        log = Logifyx("auth")
        request_log = ContextLoggerAdapter(log, {"request_id": "abc123", "user_id": 42})
        request_log.info("Login successful")

    Text mode output:
        request_id=abc123 user_id=42 | Login successful

    JSON mode output (when log was created with json_mode=True):
        {"level": "INFO", ..., "request_id": "abc123", "user_id": 42, "message": "Login successful"}

    Args:
        logger: A configured Logifyx instance.
        extra:  Dict of context fields to inject into every log record.
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        # Check if logger is in JSON mode
        if hasattr(self.logger, 'config') and self.logger.config.get("json_mode"):
            # For JSON mode, merge context into extra
            kwargs["extra"] = {**self.extra, **kwargs.get("extra", {})}
            return msg, kwargs
        else:
            # For text mode, prepend context to message
            context = " ".join(f"{k}={v}" for k, v in self.extra.items())
            return f"{context} | {msg}" if context else msg, kwargs


def get_logify_logger(
        name: str,
        level = _sentinel,
        config_dir = _sentinel,
        env_file = _sentinel,
        yaml_file = _sentinel,
        json_mode = _sentinel,
        remote_url = _sentinel,
        log_dir = _sentinel,
        log_file = _sentinel,
        output = _sentinel,
        mask = _sentinel,
        color = _sentinel,
        backup_count = _sentinel,
        max_bytes = _sentinel,
        kafka_servers = _sentinel,
        kafka_topic = _sentinel,
        schema_registry_url = _sentinel,
        schema_compatibility = _sentinel,
        remote_timeout = _sentinel,
        max_remote_retries = _sentinel,
        remote_headers = _sentinel) -> Logifyx:
    """
    Get or create a Logifyx logger, with a guaranteed singleton per name.

    REQUIRED SETUP — Logifyx must be registered as the logger class once, at the
    very top of your entry point (main.py, app.py, wsgi.py, etc.). Either call
    does that:

        from logifyx import configure_logging
        configure_logging(output="file", log_file="logs/app.log")

        # ...or, when you want Logifyx loggers but no process-wide policy:
        from logifyx import setup_logify
        setup_logify()

    configure_logging() also stores process-wide defaults and re-applies them to
    existing loggers. setup_logify() only registers the class and changes nothing
    else — the right choice inside a library, which should not impose a logging
    policy on the application using it.

    Then call get_logify_logger() anywhere in your codebase. The first call
    for a given name creates and configures the logger; every subsequent call
    with the same name returns the same already-configured instance — kwargs
    passed on repeat calls are ignored.

        from logifyx import get_logify_logger

        log = get_logify_logger("auth", log_dir="logs", mask=True)
        log.info("Server started")

    Why use this instead of Logifyx("name") directly?
        Python's logging.getLogger() keeps a process-wide registry so that
        logging.getLogger("auth") anywhere in the codebase returns the same
        object. get_logify_logger() goes through that same registry, giving you
        the singleton guarantee while still accepting Logifyx-specific kwargs.

    Args:
        name:                 Logger name. Same name always returns the same instance.
        level:                Minimum level to emit: "DEBUG", "INFO", "WARNING", "ERROR",
                              "CRITICAL" (case-insensitive) or a logging int.
                              Default: "INFO".
        output:               "console", "file", "both", or "none". "file" writes only
                              to the log file — nothing reaches the terminal.
                              Default: "both".
        log_file:             Log file path, e.g. "logs/app.log". Directories are
                              created automatically; a bare file name goes inside
                              log_dir. Default: "<name>.log".
        log_dir:              Directory used when log_file has no directory part.
                              Default: "logs".
        max_bytes:            Rotate the file at this size in bytes. Default: 10_000_000.
        backup_count:         Number of rotated backup files to keep. Default: 5.
        color:                Colorize console output by level. Default: True.
        json_mode:            Emit each line as a JSON object. Disables color. Default: False.
        mask:                 Redact passwords, tokens, and secrets. Default: True.
        remote_url:           HTTP endpoint to POST log records to (async). Default: None.
        remote_timeout:       HTTP send timeout in seconds. Default: 5.
        max_remote_retries:   Failures before the remote handler self-disables. Default: 3.
        remote_headers:       Extra HTTP headers, e.g. {"Authorization": "Bearer <tok>"}.
        kafka_servers:        Kafka bootstrap server(s), e.g. "localhost:9092".
        kafka_topic:          Kafka topic to produce to. Default: "logs".
        schema_registry_url:  Confluent Schema Registry URL for Avro. Default: None.
        schema_compatibility: Schema compatibility mode. Default: "BACKWARD".
        config_dir:           Directory containing logifyx.yaml. Default: project root.
        env_file:             Path to a .env file to load. Default: ".env".
        yaml_file:            Explicit path to a YAML config file.

    Returns:
        Configured Logifyx instance (same object on repeated calls with the same name).

    Raises:
        TypeError: neither setup_logify() nor configure_logging() was called
                   before this function.
    """
    func_params = {
        "level": level,
        "config_dir": config_dir,
        "env_file": env_file,
        "yaml_file": yaml_file,
        "json_mode": json_mode,
        "remote_url": remote_url,
        "log_dir": log_dir,
        "log_file": log_file,
        "output": output,
        "mask": mask,
        "color": color,
        "backup_count": backup_count,
        "max_bytes": max_bytes,
        "kafka_servers": kafka_servers,
        "kafka_topic": kafka_topic,
        "schema_registry_url": schema_registry_url,
        "schema_compatibility": schema_compatibility,
        "remote_timeout": remote_timeout,
        "max_remote_retries": max_remote_retries,
        "remote_headers": remote_headers
    }

    # Filter out sentinel values before registering
    provided = {k: v for k, v in func_params.items() if v is not _sentinel}

    # Pre-register kwargs BEFORE logging.getLogger() fires Logifyx.__init__.
    # The logging manager calls __init__(name) with no extra args, so kwargs
    # passed here would otherwise be silently discarded.
    if provided:
        _init_kwargs[name] = provided

    try:
        logger = logging.getLogger(name)
    finally:
        # Always clean up: __init__ pops on new loggers; we clean up here
        # for existing loggers (registry hit, __init__ never called) or errors.
        _init_kwargs.pop(name, None)

    if not isinstance(logger, Logifyx):
        raise TypeError(
            "LoggerClass not set to Logifyx. "
            "Call setup_logify() at app startup before get_logify_logger()."
        )

    return logger


def setup_logify() -> None:
    """
    Register Logifyx as the global logger class. Call once at app startup.

    This must be the first Logifyx call in your process — place it at the top
    of your entry point before any get_logify_logger() calls:

        # main.py / app.py / wsgi.py
        from logifyx import setup_logify, get_logify_logger

        setup_logify()                        # register once
        log = get_logify_logger("myapp")      # now safe to use anywhere

    What it does: calls logging.setLoggerClass(Logifyx) so that Python's
    logging manager constructs a Logifyx instance (instead of a plain
    logging.Logger) the first time logging.getLogger(name) is called for
    any new name.

    Skipping this causes get_logify_logger() to raise TypeError.
    It has no effect on loggers created with Logifyx("name") directly —
    direct instantiation does not go through the logging registry.

    setup_logify() vs configure_logging():
        configure_logging() does this registration too, and additionally stores
        process-wide defaults and rebuilds the handlers of every existing Logifyx
        logger. setup_logify() only registers the class; it stores nothing and
        leaves existing loggers exactly as they are.

        Use configure_logging() in an application, where one logging policy for
        the process is what you want. Use setup_logify() when each logger should
        configure itself, or inside a library, which must not overwrite the
        settings of the application using it.
    """
    logging.setLoggerClass(Logifyx)


def get_global_config() -> Dict[str, Any]:
    """
    A copy of the process-wide defaults installed by configure_logging().

    Empty until configure_logging() is called. These sit above environment
    variables and logifyx.yaml, and below kwargs passed to an individual logger.
    """
    with _global_lock:
        return dict(_global_overrides)


def _live_loggers() -> List["Logifyx"]:
    """Every Logifyx logger still referenced somewhere in the process."""
    with _global_lock:
        return list(_instances)


def configure_logging(
    level: Optional[Union[int, str]] = None,
    output: Optional[str] = None,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    color: Optional[bool] = None,
    json_mode: Optional[bool] = None,
    mask: Optional[bool] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
    remote_url: Optional[str] = None,
    remote_timeout: Optional[int] = None,
    max_remote_retries: Optional[int] = None,
    remote_headers: Optional[Dict[str, str]] = None,
    kafka_servers: Optional[list] = None,
    kafka_topic: Optional[str] = None,
    schema_registry_url: Optional[str] = None,
    schema_compatibility: Optional[str] = None,
    config_dir: Optional[str] = None,
    env_file: Optional[str] = None,
    yaml_file: Optional[str] = None,
    reset: bool = False,
) -> None:
    """
    Configure Logifyx for the whole process. Call once at startup.

    This is the recommended entry point when you want one logging policy for the
    entire application rather than per-logger kwargs:

        from logifyx import configure_logging, get_logify_logger

        configure_logging(level="INFO", output="file", log_file="logs/app.log")

        log = get_logify_logger("my_app")
        log.info("Application started")     # goes to logs/app.log, not the terminal

    It does three things:

    1. Registers Logifyx as the logger class (same as setup_logify()), so plain
       ``logging.getLogger("my_app")`` also returns a configured Logifyx logger.
    2. Stores the given settings as process-wide defaults. Loggers created later
       pick them up automatically.
    3. Re-applies them to every Logifyx logger that already exists, replacing
       only Logifyx-owned handlers.

    **Output modes**

        output="console"   console only — no log file is opened
        output="file"      file only — nothing is written to stdout or stderr
        output="both"      console + file (the default, and Logifyx's behaviour
                           in every earlier release)
        output="none"      no console and no file handler

    ``output`` governs the console and file destinations only. Remote HTTP and
    Kafka delivery stay controlled by ``remote_url`` / ``kafka_servers``.

    **Safe to call repeatedly.** Each call rebuilds Logifyx-owned handlers rather
    than appending to them, so three identical calls still produce exactly one
    file handler and one copy of each log line::

        configure_logging(output="file")
        configure_logging(output="file")
        configure_logging(output="file")
        log.info("hello")                   # written once

    Switching modes takes effect immediately::

        configure_logging(output="both")
        log.info("test 1")                  # terminal + file
        configure_logging(output="file")
        log.info("test 2")                  # file only

    **Priority.** These settings outrank environment variables and logifyx.yaml,
    but not kwargs passed to a specific logger — ``Logifyx("audit",
    output="console")`` keeps its console output even after
    ``configure_logging(output="file")``, because the explicit per-logger choice
    is the more specific one.

    Args:
        level:                Minimum level: "DEBUG"/"INFO"/… or a logging int.
        output:               "console", "file", "both", or "none". Also accepts
                              "console_only", "file_only", "console_and_file".
        log_file:             Log file path, e.g. "logs/app.log". Missing
                              directories — including nested ones — are created
                              automatically. A bare file name ("api.log") is placed
                              inside log_dir. Default: "<logger name>.log".
        log_dir:              Directory used when log_file has no directory part.
                              Default: "logs".
        color:                Colorize console output.
        json_mode:            Emit each record as a single-line JSON object. Applies
                              to the file as well, so file-only mode stays valid JSON.
        mask:                 Redact passwords, tokens, and secrets.
        max_bytes:            Rotate the log file at this size. Default: 10 MB.
        backup_count:         Rotated backups to keep. Default: 5.
        remote_url:           HTTP endpoint to POST records to (async).
        remote_timeout:       HTTP send timeout in seconds.
        max_remote_retries:   Failures before the remote handler self-disables.
        remote_headers:       Extra HTTP headers as Dict[str, str].
        kafka_servers:        Kafka bootstrap server(s).
        kafka_topic:          Kafka topic to produce to.
        schema_registry_url:  Confluent Schema Registry URL for Avro.
        schema_compatibility: Schema compatibility mode.
        config_dir:           Directory to search for logifyx.yaml and .env.
        env_file:             Explicit path to a .env file.
        yaml_file:            Explicit path to a YAML config file.
        reset:                Discard previously stored defaults instead of
                              merging into them.

    Raises:
        TypeError:                 a value has the wrong type.
        LogifyxConfigurationError: a value is out of range, or `output` is not a
                                   recognised mode. (Also a ValueError.)
        LogifyxFileError:          the log file or its directory could not be
                                   created. (Also a RuntimeError.)
    """
    _validate_options(
        config_dir=config_dir,
        env_file=env_file,
        yaml_file=yaml_file,
        json_mode=json_mode,
        remote_url=remote_url,
        log_dir=log_dir,
        log_file=log_file,
        output=output,
        mask=mask,
        color=color,
        backup_count=backup_count,
        max_bytes=max_bytes,
        kafka_servers=kafka_servers,
        kafka_topic=kafka_topic,
        schema_registry_url=schema_registry_url,
        schema_compatibility=schema_compatibility,
        remote_timeout=remote_timeout,
        max_remote_retries=max_remote_retries,
        remote_headers=remote_headers,
        level=level,
    )

    supplied = {
        "level": _normalize_and_validate_level(level) if level is not None else None,
        "output": normalize_output(output) if output is not None else None,
        "log_file": log_file,
        "log_dir": log_dir,
        "color": color,
        "json_mode": json_mode,
        "mask": mask,
        "max_bytes": max_bytes,
        "backup_count": backup_count,
        "remote_url": remote_url,
        "remote_timeout": remote_timeout,
        "max_remote_retries": max_remote_retries,
        "remote_headers": remote_headers,
        "kafka_servers": kafka_servers,
        "kafka_topic": kafka_topic,
        "schema_registry_url": schema_registry_url,
        "schema_compatibility": schema_compatibility,
        "config_dir": config_dir,
        "env_file": env_file,
        "yaml_file": yaml_file,
    }

    with _global_lock:
        previous = dict(_global_overrides)
        if reset:
            _global_overrides.clear()
        _global_overrides.update(
            {k: v for k, v in supplied.items() if v is not None}
        )
        merged = dict(_global_overrides)

    # Fail here, not at the first log call: check the destination is usable
    # while the caller is still looking at the configuration code. On failure
    # roll the defaults back so a rejected call leaves no half-applied state.
    try:
        effective_output = normalize_output(merged.get("output", DEFAULT_OUTPUT))
        if writes_to_file(effective_output):
            config = dict(load_config(
                config_dir=merged.get("config_dir"),
                env_file=merged.get("env_file"),
                yaml_file=merged.get("yaml_file"),
            ))
            config.update(merged)
            # Only probe the file itself when its name is pinned here. Without
            # log_file each logger names its own file, so checking the directory
            # is the most that can be verified — and avoids creating a stray file.
            validate_file_target(config, probe_file=merged.get("log_file") is not None)
    except Exception:
        with _global_lock:
            _global_overrides.clear()
            _global_overrides.update(previous)
        raise

    # Future loggers, including ones from plain logging.getLogger().
    setup_logify()

    # Existing loggers: rebuild Logifyx-owned handlers under the new settings.
    for logger in _live_loggers():
        logger.reload()


def reset_logging() -> None:
    """
    Undo configure_logging() and detach every Logifyx-owned handler.

    Clears the process-wide defaults, tears down Logifyx's handlers on every live
    logger, and stops the background listener for remote/Kafka delivery.
    Handlers your application attached are left in place.

    Mainly useful in test suites that need a clean slate between cases::

        import pytest
        from logifyx import reset_logging

        @pytest.fixture(autouse=True)
        def clean_logifyx():
            reset_logging()
            yield
            reset_logging()
    """
    with _global_lock:
        _global_overrides.clear()

    # A fresh start should warn again about a bad path, not stay quiet
    # because an earlier configuration already reported it.
    _clear_path_warnings()

    for logger in _live_loggers():
        with logger._reload_lock:
            logger._teardown_owned_handlers()

    _stop_queue_listener()

