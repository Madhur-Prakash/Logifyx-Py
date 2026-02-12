import logging
from logging.handlers import QueueHandler, QueueListener
from typing import Optional, Dict, Any
import threading
import queue
from .config import load_config
from .presets import MODES
from .formatter import get_formatter
from .filters import MaskFilter
from .handler import get_handlers


# Global queue and listener for async remote/kafka handling
_log_queue: queue.Queue = queue.Queue(-1)  # Unbounded queue
_queue_listener: Optional[QueueListener] = None
_listener_lock = threading.Lock()


def _start_queue_listener(handlers: list) -> None:
    """Start background listener for async handlers (remote, kafka)."""
    global _queue_listener
    with _listener_lock:
        if _queue_listener is None and handlers:
            _queue_listener = QueueListener(
                _log_queue,
                *handlers,
                respect_handler_level=True
            )
            _queue_listener.start()


def _stop_queue_listener() -> None:
    """Stop background listener gracefully."""
    global _queue_listener
    with _listener_lock:
        if _queue_listener:
            _queue_listener.stop()
            _queue_listener = None


class Logify(logging.Logger):
    """
    Production-grade logging class extending logging.Logger.
    
    Usage:
        # Option 1: Direct instantiation
        log = Logify("auth", mode="prod", remote_url="http://...")
        
        # Option 2: Global registration (recommended)
        import logging
        from logify import Logify, get_logify_logger
        
        logging.setLoggerClass(Logify)
        log = get_logify_logger("auth", mode="prod")
    """
    
    _configured: bool = False

    def __init__(
        self,
        name: str = "app",
        level: int = logging.NOTSET,  # Required by Logger base class
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
        remote_headers: Optional[Dict[str, str]] = None
    ):
        # Initialize base Logger first
        super().__init__(name, level)
        
        # Skip configuration if already configured (singleton pattern)
        if self._configured:
            return
            
        # Create reload lock
        self._reload_lock = threading.RLock()
        
        # Store init params for later configure() calls
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
        
        # Auto-configure if any params provided (direct instantiation)
        if any(v is not None for k, v in self._init_params.items() if k != "mask"):
            self.configure(**self._init_params)

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
    ) -> "Logify":
        """
        Configure the logger with all options.
        Called automatically on direct instantiation, or manually via get_logify_logger().
        """
        if self._configured:
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
        self._configured = True
        
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

            # Reset configured flag and rebuild
            self._configured = False
            self.configure(**self._init_params)

    def reload_from_file(self) -> None:
        """Reload configuration from logify.yaml file."""
        with self._reload_lock:
            self.config = load_config()
            self._configured = False
            self.configure(**self._init_params)


class ContextLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter for injecting structured context (request_id, user_id, etc.) into logs.
    
    Usage:
        log = Logify("auth", mode="prod")
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


def get_logify_logger(name: str, **kwargs) -> Logify:
    """
    Get or create a Logify logger instance.
    
    This ensures singleton-per-name behavior and proper configuration.
    
    Usage:
        # First, set Logify as the logger class (once at app startup)
        import logging
        logging.setLoggerClass(Logify)
        
        # Then get loggers
        log = get_logify_logger("auth", mode="prod", remote_url="http://...")
    
    Args:
        name: Logger name (singleton per name)
        **kwargs: Configuration options passed to Logify.configure()
    
    Returns:
        Configured Logify instance
    """
    logger = logging.getLogger(name)
    
    if not isinstance(logger, Logify):
        raise TypeError(
            "LoggerClass not set to Logify. "
            "Call logging.setLoggerClass(Logify) at app startup."
        )
    
    # Configure only if not already configured
    if not logger._configured and kwargs:
        logger.configure(**kwargs)
    
    return logger


def setup_logify() -> None:
    """
    Register Logify as the global logger class.
    Call this once at application startup.
    
    Usage:
        from logify import setup_logify, get_logify_logger
        
        setup_logify()
        log = get_logify_logger("myapp", mode="prod")
    """
    logging.setLoggerClass(Logify)

