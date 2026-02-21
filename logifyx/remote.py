import logging
import threading
import requests


class RemoteHandler(logging.Handler):
    """
    Thread-safe HTTP handler for sending logs to a remote server.
    
    Designed to work with QueueListener for non-blocking async logging.
    Uses internal lock for thread-safe state management.
    """

    def __init__(self, url: str, timeout: int = 2, max_failures: int = 3, headers: dict = None):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self.max_failures = max_failures
        self.headers = headers or {}
        
        # Thread-safe state
        self._lock = threading.Lock()
        self._failures = 0
        self._disabled = False

    @property
    def disabled(self) -> bool:
        with self._lock:
            return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        with self._lock:
            self._disabled = value

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the remote server.
        Thread-safe and failure-tolerant.
        """
        if self.disabled:
            return

        try:
            log_entry = self.format(record)
            
            payload = {
                "level": record.levelname,
                "message": log_entry,
                "service": record.name,
                "timestamp": record.created,
                "file": record.pathname,
                "line": record.lineno,
                "func": record.funcName,
            }

            # Add exception info if present
            if record.exc_info:
                payload["exception"] = self.formatter.formatException(record.exc_info)

            self._send(payload)
            
            # Reset failures on success
            with self._lock:
                self._failures = 0

        except Exception:
            self._handle_failure(record)

    def _send(self, payload: dict) -> None:
        """Send payload to remote server."""
        response = requests.post(
            self.url,
            json=payload,
            timeout=self.timeout,
            headers=self.headers
        )
        response.raise_for_status()

    def _handle_failure(self, record: logging.LogRecord) -> None:
        """Handle sending failure with auto-disable after max failures."""
        with self._lock:
            self._failures += 1
            current_failures = self._failures
            
            if current_failures >= self.max_failures:
                self._disabled = True

        self.handleError(record)
        
        if current_failures >= self.max_failures:
            # Log warning about disabling (outside lock)
            import sys
            print(
                f"⚠️ Remote logging to {self.url} disabled after {current_failures} failures",
                file=sys.stderr
            )

    def close(self) -> None:
        """Clean up handler resources."""
        self.acquire()
        try:
            super().close()
        finally:
            self.release()
