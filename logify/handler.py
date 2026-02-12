import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from .remote import RemoteHandler
import os
import warnings


# Optional Kafka support
try:
    from .kafka import KafkaHandler
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaHandler = None


def get_handlers(config):

    try:
        log_dir = config['log_dir']
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        raise RuntimeError(f"Cannot create log directory: {log_dir}")

    handlers = []

    file_handler = ConcurrentRotatingFileHandler(
        os.path.join(log_dir, config["file"]),
        maxBytes=config["max_bytes"],
        backupCount=config["backup_count"]
    )

    handlers.append(file_handler)

    console = logging.StreamHandler()
    handlers.append(console)

    if config.get("remote_url"):
        handlers.append(RemoteHandler(config["remote_url"], config['remote_timeout'], config['max_remote_retries'], config['remote_headers']))

    # Kafka handler with Avro + Schema Registry
    if config.get("kafka_servers") and KAFKA_AVAILABLE:
        handlers.append(KafkaHandler(
            bootstrap_servers=config["kafka_servers"],
            topic=config.get("kafka_topic", "logs"),
            schema_registry_url=config.get("schema_registry_url"),
            schema_compatibility=config.get("schema_compatibility", "BACKWARD")
        ))
    elif config.get("kafka_servers") and not KAFKA_AVAILABLE:
        warnings.warn(
            "Kafka logging requested but kafka dependencies not installed. "
            "Install with: pip install kafka-python fastavro",
            RuntimeWarning
        )

    return handlers
