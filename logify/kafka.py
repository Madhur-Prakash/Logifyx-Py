"""
Kafka Log Handler with Avro Schema Registry Support

Features:
- Async Kafka producer (aiokafka)
- Avro serialization with schema versioning
- Schema Registry integration with compatibility modes
- Auto-retry with circuit breaker pattern

Usage:
    log = Logify(
        name="myapp",
        kafka_servers="localhost:9092",
        kafka_topic="logs",
        schema_registry_url="http://localhost:8081",
        schema_compatibility="BACKWARD"  # BACKWARD, FORWARD, FULL, NONE
    ).get_logger()
"""

import logging
import traceback
import asyncio
import fastavro
import requests
from fastavro.schema import parse_schema
import json
import io
import struct
from datetime import datetime
from aiokafka import AIOKafkaProducer
from typing import Optional, Dict, Any

# Avro schema for log records (versioned)
LOG_SCHEMA_V1 = {
    "type": "record",
    "name": "LogRecord",
    "namespace": "com.logify.logs",
    "doc": "Log record schema v1",
    "fields": [
        {"name": "level", "type": "string", "doc": "Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"},
        {"name": "message", "type": "string", "doc": "Log message"},
        {"name": "service", "type": "string", "doc": "Service/logger name"},
        {"name": "timestamp", "type": "string", "doc": "ISO8601 timestamp"},
        {"name": "file", "type": ["null", "string"], "default": None, "doc": "Source file path"},
        {"name": "line", "type": ["null", "int"], "default": None, "doc": "Line number"},
        {"name": "function", "type": ["null", "string"], "default": None, "doc": "Function name"},
        {"name": "exception", "type": ["null", "string"], "default": None, "doc": "Exception traceback if any"},
        # Optional fields with defaults for BACKWARD compatibility
        {"name": "extra", "type": ["null", "string"], "default": None, "doc": "Extra JSON data"},
        {"name": "schema_version", "type": "int", "default": 1, "doc": "Schema version for evolution"}
    ]
}

# Compatibility modes for schema registry
COMPATIBILITY_MODES = ["BACKWARD", "BACKWARD_TRANSITIVE", "FORWARD", "FORWARD_TRANSITIVE", "FULL", "FULL_TRANSITIVE", "NONE"]


class AvroSerializer:
    """Handles Avro serialization with schema registry."""

    def __init__(self, schema_registry_url: Optional[str] = None, compatibility: str = "BACKWARD"):
        self.schema_registry_url = schema_registry_url
        self.compatibility = compatibility
        self.schema_id = None
        self._schema = LOG_SCHEMA_V1
        self._writer = None
        self._fastavro_available = False
        
        self._init_avro()

    def _init_avro(self):
        """Initialize Avro writer."""
        try:
            
            self._parsed_schema = parse_schema(self._schema)
            self._fastavro_available = True
        except ImportError:
            self._fastavro_available = False

    def register_schema(self, topic: str) -> Optional[int]:
        """Register schema with schema registry and get schema ID."""
        if not self.schema_registry_url:
            return None

        try:
            subject = f"{topic}-value"
            
            # Set compatibility mode
            compat_url = f"{self.schema_registry_url}/config/{subject}"
            requests.put(compat_url, json={"compatibility": self.compatibility}, timeout=5)
            
            # Register schema
            register_url = f"{self.schema_registry_url}/subjects/{subject}/versions"
            response = requests.post(
                register_url,
                json={"schema": json.dumps(self._schema)},
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                timeout=5
            )
            
            if response.status_code in (200, 201):
                self.schema_id = response.json().get("id")
                return self.schema_id
                
        except Exception:
            pass
        
        return None

    def serialize(self, record: Dict[str, Any]) -> bytes:
        """Serialize record to Avro binary format."""
        if not self._fastavro_available:
            # Fallback to JSON if fastavro not available
            return json.dumps(record).encode('utf-8')

        buffer = io.BytesIO()
        
        # Write magic byte + schema ID (Confluent wire format)
        if self.schema_id:
            buffer.write(struct.pack('>bI', 0, self.schema_id))
        
        # Write Avro data
        fastavro.schemaless_writer(buffer, self._parsed_schema, record)
        
        return buffer.getvalue()

    @property
    def schema(self) -> Dict:
        return self._schema


class KafkaHandler(logging.Handler):
    """
    Async Kafka logging handler with Avro serialization.
    
    Supports:
    - Async message production (non-blocking)
    - Avro schema with schema registry
    - Schema versioning and compatibility
    - Circuit breaker pattern for failures
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str = "logs",
        schema_registry_url: Optional[str] = None,
        schema_compatibility: str = "BACKWARD",
        max_failures: int = 5,
        acks: str = "all",
        compression_type: str = "gzip",
        **kafka_kwargs
    ):
        super().__init__()
        
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.schema_registry_url = schema_registry_url
        self.schema_compatibility = schema_compatibility
        self.max_failures = max_failures
        self.acks = acks
        self.compression_type = compression_type
        self.kafka_kwargs = kafka_kwargs
        
        self.failures = 0
        self.disabled = False
        self._producer = None
        self._loop = None
        self._serializer = None
        
        # Initialize serializer
        self._init_serializer()

    def _init_serializer(self):
        """Initialize Avro serializer."""
        self._serializer = AvroSerializer(
            schema_registry_url=self.schema_registry_url,
            compatibility=self.schema_compatibility
        )
        # Register schema if registry is configured
        if self.schema_registry_url:
            self._serializer.register_schema(self.topic)

    async def _get_producer(self):
        """Lazily initialize async Kafka producer."""
        if self._producer is None:
            try:
                
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    acks=self.acks,
                    compression_type=self.compression_type,
                    **self.kafka_kwargs
                )
                await self._producer.start()
                
            except ImportError:
                raise ImportError(
                    "aiokafka is required for Kafka logging. "
                    "Install it with: pip install aiokafka"
                )
        return self._producer

    def _build_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Build Avro-compatible log record."""
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "service": record.name,
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
            "exception": None,
            "extra": None,
            "schema_version": 1
        }

        # Add exception info if present
        if record.exc_info:
            payload["exception"] = ''.join(traceback.format_exception(*record.exc_info))

        # Add extra fields as JSON
        extra_fields = {k: v for k, v in record.__dict__.items() 
                       if k not in ('name', 'msg', 'args', 'created', 'filename',
                                   'funcName', 'levelname', 'levelno', 'lineno',
                                   'module', 'msecs', 'pathname', 'process',
                                   'processName', 'relativeCreated', 'stack_info',
                                   'thread', 'threadName', 'exc_info', 'exc_text',
                                   'message', 'asctime')}
        if extra_fields:
            payload["extra"] = json.dumps(extra_fields)

        return payload

    async def _send_async(self, record: logging.LogRecord):
        """Send log record to Kafka asynchronously."""
        try:
            producer = await self._get_producer()
            payload = self._build_record(record)
            
            # Serialize with Avro
            value = self._serializer.serialize(payload)
            
            # Send to Kafka
            await producer.send_and_wait(
                self.topic,
                value=value,
                key=record.name.encode('utf-8')
            )
            
            self.failures = 0  # Reset on success
            
        except Exception as e:
            self.failures += 1
            if self.failures >= self.max_failures:
                self.disabled = True

    def emit(self, record: logging.LogRecord):
        """Emit log record to Kafka."""
        if self.disabled:
            return

        try:
            # Run async send in background
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_async(record))
            else:
                loop.run_until_complete(self._send_async(record))
                
        except RuntimeError:
            # No event loop, create one
            asyncio.run(self._send_async(record))

    async def flush_async(self):
        """Flush pending messages."""
        if self._producer:
            await self._producer.flush()

    async def close_async(self):
        """Close Kafka producer."""
        if self._producer:
            await self._producer.flush()
            await self._producer.stop()
            self._producer = None

    def close(self):
        """Close handler."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.close_async())
            else:
                loop.run_until_complete(self.close_async())
        except RuntimeError:
            asyncio.run(self.close_async())
        super().close()


def get_log_schema() -> Dict:
    """Get the current Avro schema for log records."""
    return LOG_SCHEMA_V1


def get_compatibility_modes() -> list:
    """Get available schema compatibility modes."""
    return COMPATIBILITY_MODES
