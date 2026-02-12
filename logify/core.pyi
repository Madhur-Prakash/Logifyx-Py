from typing import Any, Dict, List, Optional
import logging

class Logify(logging.Logger):
    config: Dict[str, Any]
    _configured: bool

    def __init__(
        self,
        name: str = "app",
        level: int = ...,
        mode: Optional[str] = None,
        json_mode: Optional[bool] = None,
        remote_url: Optional[str] = None,
        log_dir: Optional[str] = None,
        mask: bool = True,
        color: Optional[bool] = None,
        backup_count: Optional[int] = None,
        max_bytes: Optional[int] = None,
        file: Optional[str] = None,
        kafka_servers: Optional[List[str]] = None,
        kafka_topic: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        schema_compatibility: Optional[str] = None,
        remote_timeout: Optional[int] = None,
        max_remote_retries: Optional[int] = None,
        remote_headers: Optional[Dict[str, str]] = None
    ) -> None: ...

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
        kafka_servers: Optional[List[str]] = None,
        kafka_topic: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        schema_compatibility: Optional[str] = None,
        remote_timeout: Optional[int] = None,
        max_remote_retries: Optional[int] = None,
        remote_headers: Optional[Dict[str, str]] = None,
        level: Optional[int] = None
    ) -> "Logify": ...

    def reload(self) -> None: ...
    def reload_from_file(self) -> None: ...


class ContextLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]) -> None: ...
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple: ...


def get_logify_logger(name: str, **kwargs: Any) -> Logify: ...
def setup_logify() -> None: ...
