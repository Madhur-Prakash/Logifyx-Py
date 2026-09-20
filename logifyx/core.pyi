from typing import Any, Dict, List, MutableMapping, Optional, Union
import logging


class Logifyx(logging.Logger):
    config: Dict[str, Any]

    def __init__(
        self,
        name: str = "app",
        level: Union[int, str] = ...,
        config_dir: Optional[str] = ...,
        env_file: Optional[str] = ...,
        yaml_file: Optional[str] = ...,
        json_mode: Optional[bool] = ...,
        remote_url: Optional[str] = ...,
        log_dir: Optional[str] = ...,
        log_file: Optional[str] = ...,
        output: Optional[str] = ...,
        mask: Optional[bool] = ...,
        color: Optional[bool] = ...,
        backup_count: Optional[int] = ...,
        max_bytes: Optional[int] = ...,
        kafka_servers: Optional[Union[str, List[str]]] = ...,
        kafka_topic: Optional[str] = ...,
        schema_registry_url: Optional[str] = ...,
        schema_compatibility: Optional[str] = ...,
        remote_timeout: Optional[int] = ...,
        max_remote_retries: Optional[int] = ...,
        remote_headers: Optional[Dict[str, str]] = ...,
    ) -> None: ...

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
        kafka_servers: Optional[Union[str, List[str]]] = None,
        kafka_topic: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        schema_compatibility: Optional[str] = None,
        remote_timeout: Optional[int] = None,
        max_remote_retries: Optional[int] = None,
        remote_headers: Optional[Dict[str, str]] = None,
        level: Optional[Union[int, str]] = None,
        replace: bool = False,
    ) -> "Logifyx": ...

    @property
    def output(self) -> str: ...

    def set_output(
        self,
        output: str,
        log_file: Optional[str] = None,
        log_dir: Optional[str] = None,
    ) -> "Logifyx": ...

    def reload(self) -> None: ...
    def reload_from_file(self) -> None: ...


class ContextLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]) -> None: ...
    def process(self, msg: Any, kwargs: MutableMapping[str, Any]) -> tuple: ...


def get_logify_logger(
    name: str,
    level: Optional[Union[int, str]] = ...,
    config_dir: Optional[str] = ...,
    env_file: Optional[str] = ...,
    yaml_file: Optional[str] = ...,
    json_mode: Optional[bool] = ...,
    remote_url: Optional[str] = ...,
    log_dir: Optional[str] = ...,
    log_file: Optional[str] = ...,
    output: Optional[str] = ...,
    mask: Optional[bool] = ...,
    color: Optional[bool] = ...,
    backup_count: Optional[int] = ...,
    max_bytes: Optional[int] = ...,
    kafka_servers: Optional[Union[str, List[str]]] = ...,
    kafka_topic: Optional[str] = ...,
    schema_registry_url: Optional[str] = ...,
    schema_compatibility: Optional[str] = ...,
    remote_timeout: Optional[int] = ...,
    max_remote_retries: Optional[int] = ...,
    remote_headers: Optional[Dict[str, str]] = ...,
) -> Logifyx: ...


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
    kafka_servers: Optional[Union[str, List[str]]] = None,
    kafka_topic: Optional[str] = None,
    schema_registry_url: Optional[str] = None,
    schema_compatibility: Optional[str] = None,
    config_dir: Optional[str] = None,
    env_file: Optional[str] = None,
    yaml_file: Optional[str] = None,
    reset: bool = False,
) -> None: ...


def reset_logging() -> None: ...
def get_global_config() -> Dict[str, Any]: ...
def setup_logify() -> None: ...
def flush(timeout: float = 5.0) -> bool: ...
def shutdown() -> None: ...
