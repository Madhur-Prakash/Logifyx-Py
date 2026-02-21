# 📂 Handlers Reference

Logifyx uses multiple output handlers to write logs to different destinations simultaneously. This document explains each handler and how to configure them.

---

## Overview

| Handler | Description | Auto-enabled |
|---------|-------------|--------------|
| [Console Handler](#console-handler) | Colored stdout output | ✅ Always |
| [File Handler](#file-handler) | Rotating file with backups | ✅ Always |
| [Remote HTTP Handler](#remote-http-handler) | POST to HTTP endpoint | When `remote_url` set |
| [Kafka Handler](#kafka-handler) | Stream to Kafka topic | When `kafka_servers` set |

All handlers are managed automatically by Logifyx. You just need to provide the configuration.

---

## Console Handler

**Always enabled.** Writes logs to stdout with optional color coding.

### Features

- Color-coded by log level (when `color=True`)
- Human-readable format for development
- Shows timestamp, logger name, level, message, file, and line number

### Configuration

```python
log = Logifyx(
    name="myapp",
    color=True  # Enable colored output
)
```

### Color Mapping

| Level | Color |
|-------|-------|
| DEBUG | Cyan |
| INFO | Green |
| WARNING | Yellow |
| ERROR | Red |
| CRITICAL | Bold Red |

### Example Output

```
2024-02-11 15:30:45 - myapp - INFO - Server started - /app/main.py - main.py - 42
2024-02-11 15:30:46 - myapp - WARNING - High memory usage - /app/main.py - main.py - 56
2024-02-11 15:30:47 - myapp - ERROR - Connection failed - /app/main.py - main.py - 78
```

---

## File Handler

**Always enabled.** Writes logs to a rotating file with automatic backup management.

### Features

- **Rotating files**: Automatically rotates when file reaches size limit
- **Backup management**: Keeps N backup files, deletes oldest
- **Concurrent-safe**: Uses `ConcurrentRotatingFileHandler` for multi-process safety
- **Auto-creates directory**: Creates log directory if it doesn't exist

### Configuration

```python
log = Logifyx(
    name="myapp",
    file="myapp.log",       # Log file name
    log_dir="logs",         # Directory for logs
    max_bytes=10_000_000,   # 10MB max file size
    backup_count=5          # Keep 5 backup files
)
```

### File Structure

```
logs/
├── myapp.log           # Current log file
├── myapp.log.1         # Previous (most recent backup)
├── myapp.log.2         # Older backup
├── myapp.log.3
├── myapp.log.4
└── myapp.log.5         # Oldest backup (deleted when 6th is created)
```

### Rotation Behavior

1. When `myapp.log` reaches `max_bytes` (10MB default)
2. Existing backups are renamed: `.1` → `.2`, `.2` → `.3`, etc.
3. `myapp.log` becomes `myapp.log.1`
4. New `myapp.log` is created
5. If backups exceed `backup_count`, oldest is deleted

---

## Remote HTTP Handler

**Enabled when `remote_url` is set.** Sends log records to an HTTP endpoint via POST requests.

### Features

- **Queue-based async**: Uses `QueueHandler` + `QueueListener` for non-blocking sends
- **Thread-safe**: Internal locking for safe concurrent access
- **Auto-retry**: Retries on failures
- **Circuit breaker**: Disables after N consecutive failures
- **JSON payload**: Structured log data with exception info

### Architecture

```
Logifyx Logger
    ↓
QueueHandler (instant, non-blocking)
    ↓
QueueListener (background thread)
    ↓
RemoteHandler → HTTP POST
```

This ensures logging never blocks your main application thread.

### Configuration

```python
log = Logifyx(
    name="myapp",
    remote_url="http://localhost:5000/logs"
)
```

Or via config:

```yaml
# logifyx.yaml
LOG_REMOTE: http://log-server:5000/logs
```

### Payload Format

Each log record is sent as a JSON POST request:

```json
{
  "level": "INFO",
  "message": "2024-02-11 15:30:45 - auth - INFO - User logged in",
  "logger": "auth-service",
  "timestamp": 1707666000.123456,
  "file": "/app/auth/login.py",
  "line": 42,
  "func": "handle_login",
  "exception": null
}
```

### Receiving Logs

Example Flask server to receive logs:

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

### Circuit Breaker

The handler automatically disables itself after 3 consecutive failures to prevent:
- Blocking the application
- Flooding a failing server
- Memory buildup from queued requests

```python
# Internal behavior:
# After 3 failures → handler.disabled = True
# No more attempts until restart
```

---

## Kafka Handler

**Enabled when `kafka_servers` is set.** Streams logs to Apache Kafka with Avro serialization.

### Features

- **Async producer**: Non-blocking with `aiokafka`
- **Avro serialization**: Efficient binary format
- **Schema Registry**: Optional Confluent Schema Registry integration
- **Schema evolution**: Supports BACKWARD, FORWARD, FULL compatibility
- **Circuit breaker**: Auto-disables after failures
- **Compression**: Gzip compression by default

### Configuration

```python
log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",  # Optional
    schema_compatibility="BACKWARD"
)
```

Or via config:

```yaml
# logifyx.yaml
LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

### Avro Schema

Logs are serialized using this Avro schema:

```json
{
  "type": "record",
  "name": "LogRecord",
  "namespace": "com.logifyx.logs",
  "fields": [
    {"name": "level", "type": "string"},
    {"name": "message", "type": "string"},
    {"name": "service", "type": "string"},
    {"name": "timestamp", "type": "string"},
    {"name": "file", "type": ["null", "string"], "default": null},
    {"name": "line", "type": ["null", "int"], "default": null},
    {"name": "function", "type": ["null", "string"], "default": null},
    {"name": "exception", "type": ["null", "string"], "default": null},
    {"name": "extra", "type": ["null", "string"], "default": null},
    {"name": "schema_version", "type": "int", "default": 1}
  ]
}
```

📖 See [Kafka Streaming Guide](kafka.md) for detailed setup instructions.

---

## Sensitive Data Masking

All handlers support sensitive data masking via the `MaskFilter`.

### Masked Patterns

```python
SENSITIVE = [
    r"password=\S+",
    r"token=\S+",
    r"secret=\S+",
    r"api_key=\S+",
    r"access_key=\S+",
    r"access_token=\S+",
]
```

### Example

```python
log = Logifyx(name="auth", mask=True)

log.info("Login attempt password=secret123 token=abc")
# All handlers receive: "Login attempt **** ****"
```

---

## Handler Priority and Formatting

### Format by Handler Type

| Handler | Color | JSON |
|---------|-------|------|
| Console | ✅ Respects `color` setting | ✅ If `json_mode=True` |
| File | ❌ Never (not readable in files) | ✅ If `json_mode=True` |
| Remote HTTP | ❌ N/A (sends JSON payload) | Always JSON |
| Kafka | ❌ N/A (sends Avro) | Always Avro/JSON |

### Log Format

Standard format (non-JSON):
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s - %(filename)s - %(lineno)d
```

Example:
```
2024-02-11 15:30:45 - myapp - INFO - Server started - /app/main.py - main.py - 42
```

JSON format (`json_mode=True`):
```json
{"asctime": "2024-02-11 15:30:45", "name": "myapp", "levelname": "INFO", "message": "Server started"}
```

---

## Next Steps

- [Configuration Guide](configuration.md) - All configuration options
- [Kafka Streaming](kafka.md) - Detailed Kafka setup
- [CLI Reference](cli.md) - Command line tools
