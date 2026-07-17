import logging
from logging.handlers import QueueHandler, QueueListener
import time
from typing import Optional, Dict, Any, Union
import threading
import queue
import atexit
from .config import load_config
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


# Sentinel object to detect if a parameter was explicitly passed
_sentinel = object()

# Valid logging levels
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"}


def _normalize_and_validate_level(level: Union[int, str]) -> Union[int, str]:
    """Normalize level string to uppercase and validate it."""
    if isinstance(level, str):
        level_upper = level.upper()
        if level_upper not in _VALID_LEVELS:
            raise ValueError(
                f"Invalid log level: {level!r}. Must be one of: {', '.join(sorted(_VALID_LEVELS))}"
            )
        return level_upper
    return level


# Global queue and listener for async remote/kafka handling
_log_queue: queue.Queue = queue.Queue(maxsize=10_00_000)  # Large maxsize to prevent blocking in high-throughput scenarios
_queue_listener: Optional[QueueListener] = None
_listener_lock = threading.Lock()
_atexit_registered = False

# Holds kwargs from get_logify_logger() so __init__ can pick them up.
# logging.getLogger() triggers Logifyx(name) with no extra args; this dict
# bridges the gap so user-supplied kwargs reach configure() on first creation.
_init_kwargs: Dict[str, dict] = {}


def _default_log_file(name: str) -> str:
    base_name = (name or "app").strip() or "app"
    return base_name if base_name.lower().endswith(".log") else f"{base_name}.log"


def _start_queue_listener(handlers: list) -> None:
    """Start background listener for async handlers (remote, kafka)."""
    global _queue_listener, _atexit_registered
    with _listener_lock:
        if _queue_listener is None and handlers:
            _queue_listener = QueueListener(
                _log_queue,
                *handlers,
                respect_handler_level=True
            )
            _queue_listener.start()
            
            # Register atexit handler to flush remaining logs on exit
            if not _atexit_registered:
                atexit.register(_flush_and_stop_listener)
                _atexit_registered = True


def _flush_and_stop_listener() -> None:
    """Flush remaining logs and stop listener on program exit."""
    global _queue_listener
    with _listener_lock:
        if _queue_listener:
            # Stop the listener - this waits for the thread to finish
            # processing remaining items and join
            _queue_listener.stop()
            _queue_listener = None


def _stop_queue_listener() -> None:
    """Stop background listener gracefully."""
    global _queue_listener
    with _listener_lock:
        if _queue_listener:
            _queue_listener.stop()
            _queue_listener = None


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
        log_dir:              Directory for rotating log files. Default: "logs".
        file:                 Log filename inside log_dir. Default: "<name>.log".
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
        mask = _sentinel,
        color = _sentinel,
        backup_count = _sentinel,
        max_bytes = _sentinel,
        file = _sentinel,
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
        
        # Store init params (only those explicitly provided)
        self._init_params = {
            "config_dir": config_dir,
            "env_file": env_file,
            "yaml_file": yaml_file,
            "json_mode": json_mode,
            "remote_url": remote_url,
            "log_dir": log_dir,
            "mask": mask,
            "color": color,
            "backup_count": backup_count,
            "max_bytes": max_bytes,
            "file": file,
            "kafka_servers": kafka_servers,
            "kafka_topic": kafka_topic,
            "schema_registry_url": schema_registry_url,
            "schema_compatibility": schema_compatibility,
            "remote_timeout": remote_timeout,
            "max_remote_retries": max_remote_retries,
            "remote_headers": remote_headers
        }
        
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
        mask: Optional[bool] = None,
        color: Optional[bool] = None,
        backup_count: Optional[int] = None,
        max_bytes: Optional[int] = None,
        file: Optional[str] = None,
        kafka_servers: Optional[list] = None,
        kafka_topic: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        schema_compatibility: Optional[str] = None,
        remote_timeout: Optional[int] = None,
        max_remote_retries: Optional[int] = None,
        remote_headers: Optional[Dict[str, str]] = None,
        level: Optional[Union[int, str]] = None
    ) -> "Logifyx":
        """
        Apply configuration options and build handlers.

        You do not need to call this directly — __init__ calls it automatically.
        It is only called again by reload() / reload_from_file() after those
        methods clear the existing handlers.

        Config priority (highest wins):
            kwargs passed here  >  environment / .env  >  logifyx.yaml  >  built-in defaults

        Passing None for a kwarg means "do not override this setting" — the value
        from env/yaml/defaults is used instead. This differs from passing False or
        an empty string, which are treated as explicit values.

        Special behaviour:
            - If json_mode=True and color=True are both active, json_mode wins and
              color is silently disabled (colorized JSON is not supported).
            - If file is not set anywhere, the log filename defaults to "<name>.log".

        Returns:
            self — allows method chaining, e.g. Logifyx("x").configure(color=False).
        """
        # Skip if already configured (handlers exist)
        if self.handlers:
            return self

        # --- strict type validation ---

        # str params
        for param, value in (
            ("config_dir",          config_dir),
            ("env_file",            env_file),
            ("yaml_file",           yaml_file),
            ("remote_url",          remote_url),
            ("log_dir",             log_dir),
            ("file",                file),
            ("kafka_topic",         kafka_topic),
            ("schema_registry_url", schema_registry_url),
        ):
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f"{param} must be a str, got {value!r} ({type(value).__name__})"
                )

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
                    raise ValueError(
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
        _VALID_COMPATIBILITY = {
            "BACKWARD", "BACKWARD_TRANSITIVE",
            "FORWARD",  "FORWARD_TRANSITIVE",
            "FULL",     "FULL_TRANSITIVE",
            "NONE",
        }
        if schema_compatibility is not None:
            if not isinstance(schema_compatibility, str):
                raise TypeError(
                    f"schema_compatibility must be a str, got {schema_compatibility!r} ({type(schema_compatibility).__name__})"
                )
            if schema_compatibility.upper() not in _VALID_COMPATIBILITY:
                raise ValueError(
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
                    raise ValueError(
                        f"level must be one of {sorted(_VALID_LEVELS)}, got {level!r}"
                    )
            elif not isinstance(level, int):
                raise TypeError(
                    f"level must be a log-level str or int, got {level!r} ({type(level).__name__})"
                )

        # Load base config
        self.config = load_config(config_dir=config_dir, env_file=env_file, yaml_file=yaml_file)

        overrides = {
            "log_dir": log_dir,
            "remote_url": remote_url,
            "backup_count": backup_count,
            "max_bytes": max_bytes,
            "file": file,
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

        if file is None and self.config.get("_file_is_default", False):
            self.config["file"] = _default_log_file(self.name)

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

    def _build(self) -> None:
        """Build and attach handlers with queue-based async architecture."""
        sync_handlers = []  # Console, file
        async_handlers = []  # Remote, Kafka (go through queue)

        for handler in get_handlers(self.config):
            # Determine formatter based on handler type
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                formatter = get_formatter(
                    self.config.get("json_mode"),
                    self.config.get("color"),
                )
                sync_handlers.append(handler)
            elif handler.__class__.__name__ in ("RemoteHandler", "KafkaHandler"):
                formatter = get_formatter(self.config.get("json_mode"), False)
                async_handlers.append(handler)
            else:
                formatter = get_formatter(self.config.get("json_mode"), False)
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
            self.addHandler(queue_handler)
            _start_queue_listener(async_handlers)

    def reload(self) -> None:
        """
        Tear down all handlers and reconfigure using the kwargs from __init__.

        Use this to pick up updated environment variables or a changed logifyx.yaml
        without restarting the process. The kwargs you originally passed at creation
        are re-applied on top of the freshly loaded config.

            log = Logifyx("auth", log_dir="logs")
            # edit logifyx.yaml or change an env var at runtime ...
            log.reload()   # drops old handlers, rebuilds with original kwargs + new config
        """
        with self._reload_lock:
            # Stop queue listener
            _stop_queue_listener()
            
            # Remove existing handlers safely
            for handler in self.handlers[:]:
                self.removeHandler(handler)
                handler.close()

            # Rebuild with provided params (handlers cleared, so configure() will run)
            provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}
            self.configure(**provided)

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
        """
        with self._reload_lock:
            # Stop queue listener
            _stop_queue_listener()
            
            # Remove existing handlers
            for handler in self.handlers[:]:
                self.removeHandler(handler)
                handler.close()
            
            # Reload config and rebuild
            self.config = load_config()
            provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}
            self.configure(**provided)


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
        config_dir = _sentinel,
        env_file = _sentinel,
        yaml_file = _sentinel,
        json_mode = _sentinel,
        remote_url = _sentinel,
        log_dir = _sentinel,
        mask = _sentinel,
        color = _sentinel,
        backup_count = _sentinel,
        max_bytes = _sentinel,
        file = _sentinel,
        kafka_servers = _sentinel,
        kafka_topic = _sentinel,
        schema_registry_url = _sentinel,
        schema_compatibility = _sentinel,
        remote_timeout = _sentinel,
        max_remote_retries = _sentinel,
        remote_headers = _sentinel) -> Logifyx:
    """
    Get or create a Logifyx logger, with a guaranteed singleton per name.

    REQUIRED SETUP — call setup_logify() once before using this function,
    at the very top of your entry point (main.py, app.py, wsgi.py, etc.):

        from logifyx import setup_logify
        setup_logify()

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
        log_dir:              Directory for rotating log files. Default: "logs".
        file:                 Log filename inside log_dir. Default: "<name>.log".
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
        TypeError: setup_logify() was not called before this function.
    """
    func_params = {
        "config_dir": config_dir,
        "env_file": env_file,
        "yaml_file": yaml_file,
        "json_mode": json_mode,
        "remote_url": remote_url,
        "log_dir": log_dir,
        "mask": mask,
        "color": color,
        "backup_count": backup_count,
        "max_bytes": max_bytes,
        "file": file,
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
    """
    logging.setLoggerClass(Logifyx)

