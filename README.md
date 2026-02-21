<div align="center">

# Logifyx

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Kafka](https://img.shields.io/badge/Kafka-Streaming-orange?logo=apache-kafka)
![Avro](https://img.shields.io/badge/Avro-Schema-red)

**A modern, production-ready Python logging framework with zero configuration.**

[Quick Start](#-quick-start) • [Features](#-features) • [Configuration](#%EF%B8%8F-configuration) • [Handlers](#-handlers) • [Kafka Streaming](#-kafka-streaming) • [CLI](#-cli-tool) • [API Reference](#-api-reference)

</div>

---

## Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Preset Modes](#-preset-modes)
- [Configuration](#%EF%B8%8F-configuration)
- [Handlers](#-handlers)
  - [Console Handler](#console-handler)
  - [File Handler](#file-handler)
  - [Remote HTTP Handler](#remote-http-handler)
  - [Kafka Handler](#kafka-handler)
- [Sensitive Data Masking](#-sensitive-data-masking)
- [Context Injection](#-context-injection)
- [Kafka Streaming](#-kafka-streaming)
- [CLI Tool](#-cli-tool)
- [API Reference](#-api-reference)
- [Examples](#-examples)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Colored Console Output** | Beautiful, readable logs with color-coded levels |
| **Rotating File Logs** | Auto-rotating log files with size limits and backup |
| **Remote HTTP Streaming** | Send logs to any HTTP endpoint in real-time |
| **Kafka Streaming** | Stream logs to Apache Kafka with Avro serialization |
| **Sensitive Data Masking** | Auto-mask passwords, tokens, and API keys |
| **JSON Mode** | Structured JSON logging for log aggregators |
| **YAML + ENV Config** | Configure via `yaml` file, environment, or code |
| **Zero Config Mode** | Works out of the box with sensible defaults |
| **Preset Modes** | Quick setup with `dev`, `prod`, and `simple` presets |
| **CLI Tool** | Inspect configuration from command line |
| **Global Registration** | Use `setup_logify()` for framework-level integration |
| **Context Injection** | Add `request_id`, `user_id` to logs with `ContextLoggerAdapter` |
| **Thread-Safe** | Queue-based async architecture for non-blocking remote logging |
| **Hot Reload** | Reload configuration without restarting your application |
| **Graceful Shutdown** | Automatic flush of pending logs on program exit |

---

## Installation

```bash
pip install logifyx
```

For Kafka streaming support:

```bash
pip install logifyx[kafka]
```

**Dependencies:**
- `colorlog` - Colored console output
- `python-json-logger` - JSON formatting
- `pyyaml` - YAML configuration
- `concurrent-log-handler` - Multi-process safe file handling
- `requests` - HTTP remote logging
- `python-dotenv` - Environment variable loading
- `aiokafka` - Async Kafka producer (optional)
- `fastavro` - Avro serialization (optional)

---

## Quick Start

### Basic Usage (Zero Config)

```python
from logifyx import Logifyx

log = Logifyx(name="myapp")

log.info("Application started")
log.warning("This is a warning")
log.error("Something went wrong")
```

### With Presets

```python
from logifyx import Logifyx

# Development mode: DEBUG level, colored output
log = Logifyx(name="myapp", mode="dev")

# Production mode: INFO level, JSON output
log = Logifyx(name="myapp", mode="prod")
```

### Full Configuration

```python
from logifyx import Logifyx

log = Logifyx(
    name="auth-service",
    mode="prod",
    file="auth.log",
    log_dir="logs",
    color=True,
    mask=True,  # Auto-mask sensitive data
    remote_url="http://localhost:5000/logs",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs"
)

log.info("Server started on port 8080")
log.warning("password=secret123 token=abc")  # Masked: **** ****
log.error("Authentication failed", exc_info=True)
```

### Global Registration (Recommended for Large Apps)

```python
from logifyx import setup_logify, get_logify_logger

# Call once at app startup
setup_logify()

# Now use get_logify_logger anywhere in your app
log = get_logify_logger("auth", mode="prod", file="auth.log")
api_log = get_logify_logger("api", mode="prod", file="api.log")
```

### Context Injection (Request Tracking)

```python
from logifyx import Logifyx, ContextLoggerAdapter

log = Logifyx(name="auth", mode="prod")

# Wrap with context for request-scoped logging
request_log = ContextLoggerAdapter(
    log,
    {"request_id": "req-abc123", "user_id": 42}
)

request_log.info("User authenticated")
# Output: request_id=req-abc123 user_id=42 | User authenticated
```

### Graceful Shutdown

```python
from logifyx import Logifyx, flush, shutdown

log = Logifyx(name="myapp", remote_url="http://localhost:5000/logs")

log.info("Processing request")

# Option 1: Wait for queued logs without stopping (use in servers)
flush(timeout=5.0)

# Option 2: Full shutdown (called automatically via atexit)
shutdown()
```

---

## 🎯 Preset Modes

Logifyx includes preset configurations for common use cases:

| Mode | Level | Color | JSON | Use Case |
|------|-------|-------|------|----------|
| `dev` | DEBUG | ✅ | ❌ | Local development with verbose, colorful output |
| `prod` | INFO | ❌ | ✅ | Production with structured JSON logs |
| `simple` | INFO | ❌ | ❌ | Basic plain-text logging |

```python
# Development mode
log = Logifyx(name="myapp", mode="dev")   # Colorful debug logs

# Production mode
log = Logifyx(name="myapp", mode="prod")  # JSON production logs

# Simple mode
log = Logifyx(name="myapp", mode="simple")  # Plain text logs
```

### Preset Details

**`dev` Mode:**
```python
{
    "level": "DEBUG",
    "color": True,
    "json_mode": False
}
```

**`prod` Mode:**
```python
{
    "level": "INFO",
    "color": False,
    "json_mode": True
}
```

**`simple` Mode:**
```python
{
    "level": "INFO",
    "color": False,
    "json_mode": False
}
```

---

## Configuration

Logifyx supports multiple configuration sources with clear priority:

```
Python Code Arguments > Environment Variables > logifyx.yaml > Defaults
```

### 1. Python Code (Highest Priority)

```python
from logifyx import Logifyx

log = Logifyx(
    name="myapp",
    level="DEBUG",
    color=True,
    file="myapp.log",
    log_dir="logs",
    mask=True
)
```

### 2. Environment Variables

Set environment variables with the `LOG_` prefix:

```bash
# Linux/macOS
export LOG_LEVEL=DEBUG
export LOG_FILE=app.log
export LOG_COLOR=True
export LOG_KAFKA_SERVERS=localhost:9092

# Windows PowerShell
$env:LOG_LEVEL = "DEBUG"
$env:LOG_FILE = "app.log"
```

Or use a `.env` file (loaded automatically via `python-dotenv`):

```env
LOG_LEVEL=DEBUG
LOG_FILE=app.log
LOG_DIR=logs
LOG_COLOR=True
LOG_MASK=True
```

### Sample `.env` File

Here's a complete `.env` file with all available options:

```env
# ===========================================
# Logifyx Configuration - Sample .env File
# ===========================================

# ---- Core Settings ----
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_MODE=dev                            # dev, prod, simple

# ---- Output Settings ----
LOG_FILE=app.log                        # Log file name
LOG_DIR=logs                            # Directory for log files
LOG_COLOR=True                          # Enable colored console output
LOG_JSON=False                          # Enable JSON formatted logs
LOG_MASK=True                           # Mask sensitive data (passwords, tokens, etc.)

# ---- File Rotation ----
LOG_MAX_BYTES=10000000                  # Max file size before rotation (10MB)
LOG_BACKUP_COUNT=5                      # Number of backup files to keep

# ---- Remote HTTP Logging ----
LOG_REMOTE=http://localhost:5000/logs   # HTTP endpoint URL
LOG_REMOTE_TIMEOUT=5                    # Request timeout in seconds
LOG_REMOTE_RETRIES=3                    # Max failures before disabling
LOG_REMOTE_HEADERS={"Content-Type": "application/json", "Authorization": "Bearer your-token"}  # Custom HTTP headers (JSON format)

# ---- Kafka Streaming ----
LOG_KAFKA_SERVERS=localhost:9092        # Kafka bootstrap servers (comma-separated)
LOG_KAFKA_TOPIC=app-logs                # Kafka topic name
LOG_SCHEMA_REGISTRY=http://localhost:8081  # Confluent Schema Registry URL
LOG_SCHEMA_COMPATIBILITY=BACKWARD       # BACKWARD, FORWARD, FULL, NONE
```

> **Note:** Add `.env` to your `.gitignore` to avoid committing secrets.

### 3. YAML Configuration File

Create a `logifyx.yaml` file in your project root:

```yaml
# Logging Settings
LOG_LEVEL: DEBUG
LOG_FILE: app.log
LOG_DIR: logs
LOG_COLOR: True
LOG_JSON: False
LOG_MASK: True
LOG_MODE: dev

# File Rotation
LOG_MAX_BYTES: 10000000
LOG_BACKUP_COUNT: 5

# Remote HTTP Streaming
LOG_REMOTE: http://localhost:5000/logs
LOG_REMOTE_TIMEOUT: 5
LOG_REMOTE_RETRIES: 3
LOG_REMOTE_HEADERS:
  Content-Type: application/json
  Authorization: Bearer your-token

# Kafka Streaming
LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

### All Configuration Options

#### Core Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `name` | - | - | `"app"` | Logger name (identifies the service) |
| `level` | `LOG_LEVEL` | `LOG_LEVEL` | `"INFO"` | Minimum log level |
| `mode` | `LOG_MODE` | `LOG_MODE` | `"dev"` | Preset mode (dev/prod/simple) |

#### Output Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `file` | `LOG_FILE` | `LOG_FILE` | `"app.log"` | Log file name |
| `log_dir` | `LOG_DIR` | `LOG_DIR` | `"logs"` | Directory for log files |
| `color` | `LOG_COLOR` | `LOG_COLOR` | `False` | Enable colored console output |
| `json_mode` | `LOG_JSON` | `LOG_JSON` | `False` | Enable JSON formatted logs |
| `mask` | `LOG_MASK` | `LOG_MASK` | `True` | Mask sensitive data |

#### File Rotation Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `max_bytes` | `LOG_MAX_BYTES` | `LOG_MAX_BYTES` | `10000000` | Max file size before rotation (bytes) |
| `backup_count` | `LOG_BACKUP_COUNT` | `LOG_BACKUP_COUNT` | `5` | Number of backup files to keep |

#### Remote HTTP Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `remote_url` | `LOG_REMOTE` | `LOG_REMOTE` | `None` | HTTP endpoint URL |
| `remote_timeout` | `LOG_REMOTE_TIMEOUT` | `LOG_REMOTE_TIMEOUT` | `5` | Request timeout (seconds) |
| `max_remote_retries` | `LOG_REMOTE_RETRIES` | `LOG_REMOTE_RETRIES` | `3` | Max failures before disabling |
| `remote_headers` | - | `LOG_REMOTE_HEADERS` | `{"Content-Type": "application/json"}` | Custom HTTP headers |

#### Kafka Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `kafka_servers` | `LOG_KAFKA_SERVERS` | `LOG_KAFKA_SERVERS` | `None` | Kafka bootstrap servers |
| `kafka_topic` | `LOG_KAFKA_TOPIC` | `LOG_KAFKA_TOPIC` | `"logs"` | Kafka topic name |
| `schema_registry_url` | `LOG_SCHEMA_REGISTRY` | `LOG_SCHEMA_REGISTRY` | `None` | Schema Registry URL |
| `schema_compatibility` | `LOG_SCHEMA_COMPATIBILITY` | `LOG_SCHEMA_COMPATIBILITY` | `"BACKWARD"` | Schema compatibility mode |

### Log Levels

| Level | Value | Description |
|-------|-------|-------------|
| `DEBUG` | 10 | Detailed information for debugging |
| `INFO` | 20 | General operational information |
| `WARNING` | 30 | Something unexpected happened |
| `ERROR` | 40 | A serious problem occurred |
| `CRITICAL` | 50 | Program may not be able to continue |

---

## Handlers

Logifyx writes logs to multiple destinations simultaneously:

| Handler | Description | Auto-enabled |
|---------|-------------|--------------|
| **Console** | Colored stdout output | ✅ Always |
| **File** | Rotating file with backups | ✅ Always |
| **Remote HTTP** | POST to HTTP endpoint | When `remote_url` set |
| **Kafka** | Stream to Kafka topic | When `kafka_servers` set |

### Console Handler

**Always enabled.** Writes logs to stdout with optional color coding.

#### Color Mapping

| Level | Color |
|-------|-------|
| DEBUG | Cyan |
| INFO | Green |
| WARNING | Yellow |
| ERROR | Red |
| CRITICAL | Bold Red |

```python
log = Logifyx(name="myapp", color=True)
```

#### Example Output

```
2024-02-11 15:30:45 - myapp - INFO - Server started - /app/main.py - main.py - 42
2024-02-11 15:30:46 - myapp - WARNING - High memory usage - /app/main.py - main.py - 56
2024-02-11 15:30:47 - myapp - ERROR - Connection failed - /app/main.py - main.py - 78
```

### File Handler

**Always enabled.** Writes logs to a rotating file with automatic backup management.

#### Features

- **Rotating files**: Automatically rotates when file reaches size limit
- **Backup management**: Keeps N backup files, deletes oldest
- **Concurrent-safe**: Uses `ConcurrentRotatingFileHandler` for multi-process safety
- **Auto-creates directory**: Creates log directory if it doesn't exist

```python
log = Logifyx(
    name="myapp",
    file="myapp.log",       # Log file name
    log_dir="logs",         # Directory for logs
    max_bytes=10_000_000,   # 10MB max file size
    backup_count=5          # Keep 5 backup files
)
```

#### File Structure

```
logs/
├── myapp.log           # Current log file
├── myapp.log.1         # Previous (most recent backup)
├── myapp.log.2         # Older backup
├── myapp.log.3
├── myapp.log.4
└── myapp.log.5         # Oldest backup
```

### Remote HTTP Handler

**Enabled when `remote_url` is set.** Sends log records to an HTTP endpoint via POST requests.

#### Features

- **Queue-based async**: Uses `QueueHandler` + `QueueListener` for non-blocking sends
- **Thread-safe**: Internal locking for safe concurrent access
- **Auto-retry**: Retries on failures
- **Circuit breaker**: Disables after N consecutive failures (default: 3)
- **JSON payload**: Structured log data with exception info

#### Architecture

```
Logifyx Logger
    ↓
QueueHandler (instant, non-blocking)
    ↓
QueueListener (background thread)
    ↓
RemoteHandler → HTTP POST
```

```python
log = Logifyx(
    name="myapp",
    remote_url="http://localhost:5000/logs",
    remote_timeout=5,
    max_remote_retries=3,
    remote_headers={"Authorization": "Bearer token"}
)
```

#### Payload Format

```json
{
  "level": "INFO",
  "message": "2024-02-11 15:30:45 - auth - INFO - User logged in",
  "service": "auth-service",
  "timestamp": 1707666000.123456,
  "file": "/app/auth/login.py",
  "line": 42,
  "func": "handle_login",
  "exception": null
}
```

#### Example Flask Server

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/logs', methods=['POST'])
def receive_logs():
    log_data = request.json
    print(f"[{log_data['level']}] {log_data['service']}: {log_data['message']}")
    return {"status": "received"}, 200

if __name__ == '__main__':
    app.run(port=5000)
```

### Kafka Handler

**Enabled when `kafka_servers` is set.** Streams logs to Apache Kafka with Avro serialization.

See [Kafka Streaming](#-kafka-streaming) section for detailed documentation.

---

## Sensitive Data Masking

Logifyx automatically masks sensitive data patterns in all handlers:

```python
log = Logifyx(name="auth", mask=True)

log.info("User login password=secret123 token=abc123")
# Output: User login **** ****
```

### Masked Patterns

| Pattern | Example |
|---------|---------|
| `password=...` | `password=secret123` → `****` |
| `token=...` | `token=abc123` → `****` |
| `secret=...` | `secret=mykey` → `****` |
| `api_key=...` | `api_key=xyz` → `****` |
| `access_key=...` | `access_key=123` → `****` |
| `access_token=...` | `access_token=tok` → `****` |

---

## Context Injection

Use `ContextLoggerAdapter` to inject structured context (request_id, user_id, etc.) into logs:

```python
from logifyx import Logifyx, ContextLoggerAdapter

log = Logifyx(name="auth", mode="prod")

# Wrap logger with context for request-scoped logging
request_log = ContextLoggerAdapter(
    log,
    {"request_id": "abc123", "user_id": 42, "session": "sess-xyz"}
)

request_log.info("User authenticated")
# Text output: request_id=abc123 user_id=42 session=sess-xyz | User authenticated

# JSON output (if json_mode=True): includes context in extra fields
```

### Use Cases

- **Request tracking**: Add `request_id` for distributed tracing
- **User context**: Include `user_id` for audit logs
- **Multi-tenant**: Add `tenant_id` for SaaS applications

---

## Kafka Streaming

Stream logs to Apache Kafka with Avro serialization and Schema Registry support.

### Features

- **Async Producer**: Non-blocking log delivery using `aiokafka`
- **Avro Serialization**: Efficient binary format with schema validation
- **Schema Registry**: Confluent Schema Registry integration
- **Schema Evolution**: BACKWARD, FORWARD, FULL compatibility modes
- **Circuit Breaker**: Automatic disable after repeated failures
- **Compression**: Gzip compression for efficient network usage

### Quick Start

#### 1. Install Dependencies

```bash
pip install aiokafka fastavro
```

#### 2. Start Kafka (Docker)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: kafka
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,PLAINTEXT_HOST://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 5

  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    container_name: schema-registry
    depends_on:
      kafka:
        condition: service_healthy
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: PLAINTEXT://kafka:29092
```

```bash
docker-compose up -d
```

#### 3. Use Kafka Logging

```python
from logifyx import Logifyx

log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD"
)

log.info("This message goes to Kafka!")
```

### Avro Schema

Logs are serialized using this Avro schema:

```json
{
  "type": "record",
  "name": "LogRecord",
  "namespace": "com.logifyx.logs",
  "doc": "Log record schema v1",
  "fields": [
    {"name": "level", "type": "string", "doc": "Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"},
    {"name": "message", "type": "string", "doc": "Log message"},
    {"name": "service", "type": "string", "doc": "Service/logger name"},
    {"name": "timestamp", "type": "string", "doc": "ISO8601 timestamp"},
    {"name": "file", "type": ["null", "string"], "default": null, "doc": "Source file path"},
    {"name": "line", "type": ["null", "int"], "default": null, "doc": "Line number"},
    {"name": "function", "type": ["null", "string"], "default": null, "doc": "Function name"},
    {"name": "exception", "type": ["null", "string"], "default": null, "doc": "Exception traceback if any"},
    {"name": "extra", "type": ["null", "string"], "default": null, "doc": "Extra JSON data"},
    {"name": "schema_version", "type": "int", "default": 1, "doc": "Schema version for evolution"}
  ]
}
```

### Schema Compatibility Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `BACKWARD` | New schema can read old data | Adding optional fields |
| `BACKWARD_TRANSITIVE` | All previous schemas | Strict backward compatibility |
| `FORWARD` | Old schema can read new data | Removing optional fields |
| `FORWARD_TRANSITIVE` | All future schemas | Strict forward compatibility |
| `FULL` | Both backward and forward | Most restrictive |
| `FULL_TRANSITIVE` | All versions both ways | Maximum compatibility |
| `NONE` | No compatibility checks | Development only |

**Recommended: BACKWARD Compatibility**
- ✅ Adding new optional fields (with defaults)
- ✅ Adding new fields with default values
- ❌ Removing fields
- ❌ Changing field types

### Consuming Logs

#### Python Consumer

```python
import asyncio
import json
from aiokafka import AIOKafkaConsumer

async def consume_logs():
    consumer = AIOKafkaConsumer(
        'app-logs',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        group_id='log-viewer'
    )
    
    await consumer.start()
    print("Listening for logs...")
    
    try:
        async for msg in consumer:
            try:
                log = json.loads(msg.value.decode('utf-8'))
            except:
                # Handle Avro (skip 5-byte header)
                import fastavro, io
                from logifyx.kafka import LOG_SCHEMA_V1
                from fastavro.schema import parse_schema
                
                data = msg.value[5:] if msg.value[0] == 0 else msg.value
                schema = parse_schema(LOG_SCHEMA_V1)
                log = fastavro.schemaless_reader(io.BytesIO(data), schema)
            
            print(f"[{log['level']}] {log['service']}: {log['message']}")
    finally:
        await consumer.stop()

asyncio.run(consume_logs())
```

#### Kafka Console Consumer

```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic app-logs \
  --from-beginning
```

### Production Configuration

#### Multiple Brokers

```python
log = Logifyx(
    name="myapp",
    kafka_servers="kafka1:9092,kafka2:9092,kafka3:9092",
    kafka_topic="app-logs"
)
```

### Troubleshooting

| Error | Solution |
|-------|----------|
| `KafkaConnectionError` | Ensure Kafka is running: `docker-compose ps` |
| `Schema registry connection failed` | Wait 30-60s after startup, check `curl http://localhost:8081` |
| `ImportError: aiokafka` | Install: `pip install aiokafka fastavro` |

---

## CLI Tool

Inspect your Logifyx configuration from the command line.

### Commands

#### `logifyx --config`

Display the resolved configuration from all sources:

```bash
logifyx --config
```

**Output:**

```
Logifyx Configuration (logifyx.yaml: found):

{
    "level": "DEBUG",
    "color": true,
    "max_bytes": 10000000,
    "backup_count": 5,
    "log_dir": "logs",
    "file": "app.log",
    "mode": "dev",
    "json_mode": false,
    "mask": true,
    "remote_url": null,
    "kafka_servers": "localhost:9092",
    "kafka_topic": "logs",
    "schema_registry_url": null,
    "schema_compatibility": "BACKWARD",
    "remote_timeout": 5,
    "max_remote_retries": 3,
    "remote_headers": {"Content-Type": "application/json"}
}
```

#### `logifyx --help`

```bash
logifyx --help
```

### Use Cases

```bash
# Verify config before deployment
logifyx --config

# Check specific settings
logifyx --config | grep kafka

# Compare environments
logifyx --config > config-snapshot.json
```

---

## API Reference

### `Logifyx` Class

Main logger class extending `logging.Logger`.

```python
from logifyx import Logifyx

log = Logifyx(
    name: str = "app",                    # Logger name
    level: int = logging.NOTSET,          # Log level
    mode: str = None,                     # Preset mode (dev/prod/simple)
    json_mode: bool = None,               # JSON output
    remote_url: str = None,               # HTTP endpoint
    log_dir: str = None,                  # Log directory
    mask: bool = True,                    # Mask sensitive data
    color: bool = None,                   # Colored output
    backup_count: int = None,             # Backup files count
    max_bytes: int = None,                # Max file size
    file: str = None,                     # Log filename
    kafka_servers: str = None,            # Kafka bootstrap servers
    kafka_topic: str = None,              # Kafka topic
    schema_registry_url: str = None,      # Schema Registry URL
    schema_compatibility: str = None,     # Schema compatibility
    remote_timeout: int = None,           # HTTP timeout
    max_remote_retries: int = None,       # HTTP max retries
    remote_headers: dict = None           # HTTP headers
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `configure(**kwargs)` | Configure the logger with all options |
| `reload()` | Reload logger configuration and handlers |
| `reload_from_file()` | Reload configuration from `logifyx.yaml` |

### `ContextLoggerAdapter` Class

Adapter for injecting structured context into logs.

```python
from logifyx import ContextLoggerAdapter

adapter = ContextLoggerAdapter(
    logger: Logifyx,              # Base logger
    extra: dict                  # Context dictionary
)
```

### `get_logify_logger()` Function

Get or create a configured Logifyx logger instance.

```python
from logifyx import get_logify_logger

log = get_logify_logger(
    name: str,                   # Logger name (singleton per name)
    **kwargs                     # Same options as Logifyx constructor
)
```

**Note:** Requires calling `setup_logify()` first.

### `setup_logify()` Function

Register Logifyx as the global logger class.

```python
from logifyx import setup_logify

setup_logify()  # Call once at app startup
```

### `flush()` Function

Wait for queued logs to be sent without stopping the listener.

```python
from logifyx import flush

success = flush(timeout: float = 5.0)  # Returns True if drained
```

### `shutdown()` Function

Explicitly flush and stop all async logging handlers.

```python
from logifyx import shutdown

shutdown()  # Call before application exits
```

**Note:** Automatically registered with `atexit`, but call explicitly for immediate cleanup.

---

## Examples

### Basic Demo

```python
from logifyx import Logifyx, ContextLoggerAdapter, get_logify_logger, setup_logify, flush

# Direct instantiation
log = Logifyx(
    name="auth",
    mode="dev",
    file="auth.log",
    color=True,
    mask=True
)

log.info("Server started")
log.warning("password=123456 token=abcd123")  # Masked
log.error("Login failed")

# Global registration
setup_logify()
api_log = get_logify_logger("api", mode="dev", file="api.log")
api_log.info("API endpoint hit")

# Context injection
request_log = ContextLoggerAdapter(
    log,
    {"request_id": "req-abc123", "user_id": 42}
)
request_log.info("User authenticated")

# Cleanup
flush(timeout=5.0)
```

### Kafka Demo

```python
from logifyx import Logifyx

log = Logifyx(
    name="kafka-demo",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD",
    color=True
)

log.info("Application started")
log.debug("Debug message")
log.warning("Warning message")

try:
    1 / 0
except Exception:
    log.error("Exception occurred", exc_info=True)

log.info("Application finished")
```

---

## Project Structure

```
logifyx/
├── __init__.py      # Package exports
├── core.py          # Main Logifyx class
├── config.py        # Configuration loading
├── handler.py       # Handler factory
├── formatter.py     # Log formatters
├── filters.py       # Sensitive data masking
├── presets.py       # Mode presets (dev/prod/simple)
├── remote.py        # HTTP remote handler
├── kafka.py         # Kafka + Avro handler
└── cli.py           # CLI tool
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ by [Madhur Prakash](https://github.com/madhurprakash)**

[Report Bug](https://github.com/Madhur-Prakash/Logifyx-Py/issues) • [Request Feature](https://github.com/Madhur-Prakash/Logifyx-Py/issues)

</div>
