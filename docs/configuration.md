# ⚙️ Configuration Guide

Logifyx provides flexible configuration through multiple sources with a clear priority order.

---

## Configuration Priority

Settings are resolved in this order (highest to lowest priority):

```
1. Python Code Arguments  (highest)
2. Environment Variables
3. logifyx.yaml file
4. Default Values         (lowest)
```

This means you can set defaults in `logifyx.yaml`, override them with environment variables for different environments, and still override specific values in code.

---

## Configuration Methods

### 1. Python Code (Highest Priority)

Pass configuration directly to the `Logifyx` constructor:

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

Or use a `.env` file (loaded automatically via python-dotenv):

```env
LOG_LEVEL=DEBUG
LOG_FILE=app.log
LOG_DIR=logs
LOG_COLOR=True
LOG_MASK=True
```

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

# Kafka Streaming
LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

---

## All Configuration Options

### Core Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `name` | - | - | `"app"` | Logger name (identifies the service) |
| `level` | `LOG_LEVEL` | `LOG_LEVEL` | `"INFO"` | Minimum log level |
| `mode` | `LOG_MODE` | `LOG_MODE` | `"dev"` | Preset mode (dev/prod/simple) |

### Output Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `file` | `LOG_FILE` | `LOG_FILE` | `"app.log"` | Log file name |
| `log_dir` | `LOG_DIR` | `LOG_DIR` | `"logs"` | Directory for log files |
| `color` | `LOG_COLOR` | `LOG_COLOR` | `False` | Enable colored console output |
| `json_mode` | `LOG_JSON` | `LOG_JSON` | `False` | Enable JSON formatted logs |
| `mask` | `LOG_MASK` | `LOG_MASK` | `True` | Mask sensitive data |

### File Rotation Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `max_bytes` | `LOG_MAX_BYTES` | `LOG_MAX_BYTES` | `10000000` | Max file size before rotation (bytes) |
| `backup_count` | `LOG_BACKUP_COUNT` | `LOG_BACKUP_COUNT` | `5` | Number of backup files to keep |

### Remote HTTP Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `remote_url` | `LOG_REMOTE` | `LOG_REMOTE` | `None` | HTTP endpoint URL |

### Kafka Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `kafka_servers` | `LOG_KAFKA_SERVERS` | `LOG_KAFKA_SERVERS` | `None` | Kafka bootstrap servers |
| `kafka_topic` | `LOG_KAFKA_TOPIC` | `LOG_KAFKA_TOPIC` | `"logs"` | Kafka topic name |
| `schema_registry_url` | `LOG_SCHEMA_REGISTRY` | `LOG_SCHEMA_REGISTRY` | `None` | Schema Registry URL |
| `schema_compatibility` | `LOG_SCHEMA_COMPATIBILITY` | `LOG_SCHEMA_COMPATIBILITY` | `"BACKWARD"` | Schema compatibility mode |

---

## Log Levels

| Level | Value | Description |
|-------|-------|-------------|
| `DEBUG` | 10 | Detailed information for debugging |
| `INFO` | 20 | General operational information |
| `WARNING` | 30 | Something unexpected happened |
| `ERROR` | 40 | A serious problem occurred |
| `CRITICAL` | 50 | Program may not be able to continue |

---

## Preset Modes

Logifyx includes preset configurations for common use cases:

### `dev` Mode (Development)

```python
{
    "level": "DEBUG",
    "color": True,
    "json_mode": False
}
```

Best for: Local development with verbose, colorful output.

### `prod` Mode (Production)

```python
{
    "level": "INFO",
    "color": False,
    "json_mode": True
}
```

Best for: Production with structured JSON logs for aggregators like ELK, Splunk.

### `simple` Mode

```python
{
    "level": "INFO",
    "color": False,
    "json_mode": False
}
```

Best for: Simple plain-text logging without colors.

### Using Presets

```python
# Preset with overrides
log = Logifyx(
    name="myapp",
    mode="prod",        # Use production preset
)
```

---

## Environment-Specific Configuration

### Development Setup

```yaml
# logifyx.yaml
LOG_MODE: dev
LOG_LEVEL: DEBUG
LOG_COLOR: True
```

### Production Setup

```yaml
# logifyx.yaml
LOG_MODE: prod
LOG_LEVEL: INFO
LOG_JSON: True
LOG_REMOTE: http://log-aggregator:5000/logs
LOG_KAFKA_SERVERS: kafka:9092
```

### Using `.env` for Secrets

```env
# .env (add to .gitignore)
LOG_REMOTE=http://internal-log-server:5000/logs
LOG_KAFKA_SERVERS=kafka.internal:9092
LOG_SCHEMA_REGISTRY=http://schema-registry.internal:8081
```

---

## Viewing Current Configuration

Use the CLI to inspect resolved configuration:

```bash
logifyx --config
```

Output:
```
📦 Logifyx Configuration (logifyx.yaml: found):

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
    "schema_compatibility": "BACKWARD"
}
```

---

## Next Steps

- [Handlers Reference](handlers.md) - Learn about output handlers
- [Kafka Streaming](kafka.md) - Set up Kafka log streaming
- [CLI Reference](cli.md) - Command line tools
