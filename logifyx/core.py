import logging
from logging.handlers import QueueHandler, QueueListener
import time
from typing import Optional, Dict, Any
import threading
import queue
import atexit
from .config import load_config
from .presets import MODES
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


# Sentinel object to detect if a parameter was explicitly passed
_sentinel = object()

# Global queue and listener for async remote/kafka handling
_log_queue: queue.Queue = queue.Queue(maxsize=10_00_000)  # Large maxsize to prevent blocking in high-throughput scenarios
_queue_listener: Optional[QueueListener] = None
_listener_lock = threading.Lock()
_atexit_registered = False


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
    Wait for queued logs to be sent without stopping the listener.
    
    Use this in servers to ensure logs are delivered during shutdown
    without blocking normal operation. Non-blocking if queue empties quickly.
    
    Args:
        timeout: Maximum seconds to wait for queue to drain (default 5.0)
        
    Returns:
        True if queue drained within timeout, False otherwise
        
    Usage:
        from logifyx import flush
        
        # In request handler or periodic cleanup
        flush(timeout=2.0)
    """
    start = time.time()
    while not _log_queue.empty():
        if time.time() - start > timeout:
            return False
        time.sleep(0.01)
    return True


def shutdown() -> None:
    """
    Explicitly flush and stop all async logging handlers.
    
    Call this before your application exits to ensure all queued remote/kafka
    logs are delivered. This is automatically registered with atexit, but calling
    it explicitly ensures all logs are sent before any cleanup code runs.
    
    Usage:
        from logifyx import shutdown
        
        # At end of your application
        shutdown()
    """
    _flush_and_stop_listener()


class Logifyx(logging.Logger):
    """
    Production-grade logging class extending logging.Logger.
    
    Usage:
        # Option 1: Direct instantiation
        log = Logifyx("auth", mode="prod", remote_url="http://...")
        
        # Option 2: Global registration (recommended)
        import logging
        from logifyx import Logifyx, get_logify_logger
        
        logging.setLoggerClass(Logifyx)
        log = get_logify_logger("auth", mode="prod")
    """
    

    def __init__(
        self,
        name: str = "app",
        level: int = logging.NOTSET,  # Required by Logger base class
        mode = _sentinel,
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
        # Initialize base Logger first
        super().__init__(name, level)
        
        # Skip if already configured (handlers exist = already set up)
        if self.handlers:
            return
            
        # Create reload lock
        self._reload_lock = threading.RLock()
        
        # Store init params (only those explicitly provided)
        self._init_params = {
            "mode": mode,
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
        
        # Filter out sentinel values - keep only explicitly provided params
        provided = {k: v for k, v in self._init_params.items() if v is not _sentinel}
        
        # Auto-configure if any params provided (direct instantiation)
        if provided:
            self.configure(**provided)

    def configure(
        self,
        mode: Optional[str] = None,
        json_mode: Optional[bool] = None,
        remote_url: Optional[str] = None,
        log_dir: Optional[str] = None,
        mask: bool = True,
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
        level: Optional[int] = None
    ) -> "Logifyx":
        """
        Configure the logger with all options.
        Called automatically on direct instantiation, or manually via get_logify_logger().
        """
        # Skip if already configured (handlers exist)
        if self.handlers:
            return self
            
        # Load base config
        self.config = load_config()

        # Apply preset
        if mode and mode in MODES:
            self.config.update(MODES[mode])
            self.config["mode"] = mode

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

        # Conflict resolution
        if self.config.get("json_mode") and self.config.get("color"):
            self.config["json_mode"] = False

        final_level = self.config.get("level", logging.INFO)
        self.setLevel(final_level)
        
        self.propagate = False
        logging.raiseExceptions = self.config.get("mode") != "prod"

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
        """Reload logger configuration and handlers."""
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
        """Reload configuration from logifyx.yaml file."""
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
    Adapter for injecting structured context (request_id, user_id, etc.) into logs.
    
    Usage:
        log = Logifyx("auth", mode="prod")
        request_log = ContextLoggerAdapter(log, {"request_id": "abc123", "user_id": 42})
        request_log.info("Login successful")
        
    Output:
        request_id=abc123 user_id=42 | Login successful
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
        mode = _sentinel,
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
    Get or create a Logifyx logger instance.
    
    This ensures singleton-per-name behavior and proper configuration.
    
    Usage:
        # First, set Logifyx as the logger class (once at app startup)
        import logging
        logging.setLoggerClass(Logifyx)
        
        # Then get loggers
        log = get_logify_logger("auth", mode="prod", remote_url="http://...")
    
    Args:
        name: Logger name (singleton per name)
        **kwargs: Configuration options passed to Logifyx.configure()
    
    Returns:
        Configured Logifyx instance
    """
    func_params = {
        "mode": mode,
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

    logger = logging.getLogger(name)
    
    if not isinstance(logger, Logifyx):
        raise TypeError(
            "LoggerClass not set to Logifyx. "
            "Call logging.setLoggerClass(Logifyx) at app startup."
        )
    
    # Filter out sentinel values - keep only explicitly provided params
    provided = {k: v for k, v in func_params.items() if v is not _sentinel}
    
    # Configure only if not already configured (no handlers yet)
    if not logger.handlers and provided:
        logger.configure(**provided)
    
    return logger


def setup_logify() -> None:
    """
    Register Logifyx as the global logger class.
    Call this once at application startup.
    
    Usage:
        from logifyx import setup_logify, get_logify_logger
        
        setup_logify()
        log = get_logify_logger("myapp", mode="prod")
    """
    logging.setLoggerClass(Logifyx)

