[← Docs Index](README.md) · [Handlers](handlers.md) · [Kafka](kafka.md) · [CLI](cli.md) · [README](../README.md)

---

# Configuration Guide

Logifyx supports multiple configuration sources. Settings are resolved in this order (highest wins):

```
1. Python kwargs        — values passed directly to Logifyx() or get_logify_logger()
2. System env vars      — variables set in the shell (export / $env:)
3. .env file            — loaded automatically from the project root via python-dotenv
4. logifyx.yaml         — YAML file in the project root
5. Defaults             — hardcoded fallbacks (listed below)
```

If the same key appears in both system env vars and `.env`, the system env var wins.

---

## All Environment Variables

Every setting has a corresponding env var with a `LOG_` prefix. All can be set in `.env`, `logifyx.yaml`, or as real shell env vars.

### Core

| Env Var | Python kwarg | Default | Description |
|---------|-------------|---------|-------------|
| `LOG_LEVEL` | `level` | `"INFO"` | Minimum level to emit. One of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Logs below this level are silently dropped. |
| `LOG_MASK` | `mask` | `true` | Auto-mask sensitive values like `password=`, `token=`, `secret=`, `api_key=` in every handler. |

### Console Output

| Env Var | Python kwarg | Default | Description |
|---------|-------------|---------|-------------|
| `LOG_COLOR` | `color` | `true` | Color the console output by log level. Set `false` for plain text (e.g. when piping output to a file). |
| `LOG_JSON` | `json_mode` | `false` | Emit each log as a single-line JSON object instead of the pipe-separated text format. Useful when piping to `jq` or a log aggregator. `color` and `json_mode` are mutually exclusive — if both are `true`, `json_mode` is ignored. |

### File Output

| Env Var | Python kwarg | Default | Description |
|---------|-------------|---------|-------------|
| `LOG_FILE` | `file` | `<logger-name>.log` | Log file name inside `LOG_DIR`. If not set, defaults to the logger name (e.g. `myapp.log`). |
| `LOG_DIR` | `log_dir` | `"logs"` | Directory where log files are written. Created automatically if it does not exist. |
| `LOG_MAX_BYTES` | `max_bytes` | `10000000` (10 MB) | When the log file exceeds this size it is rotated. Set to `0` to disable rotation. |
| `LOG_BACKUP_COUNT` | `backup_count` | `5` | How many rotated backup files to keep (`app.log.1` … `app.log.5`). Oldest is deleted when a new one is created. |

### Remote HTTP

| Env Var | Python kwarg | Default | Description |
|---------|-------------|---------|-------------|
| `LOG_REMOTE` | `remote_url` | `None` | HTTP(S) endpoint URL. When set, every log record is POSTed as JSON to this URL in the background (non-blocking). |
| `LOG_REMOTE_TIMEOUT` | `remote_timeout` | `5` | Seconds to wait for the HTTP server to respond before timing out. |
| `LOG_REMOTE_RETRIES` | `max_remote_retries` | `3` | Number of consecutive failures allowed before the remote handler permanently disables itself (circuit breaker). |
| `LOG_REMOTE_HEADERS` | `remote_headers` | `{"Content-Type": "application/json"}` | Custom HTTP headers sent with every request. In `.env` write as a JSON string: `LOG_REMOTE_HEADERS={"Authorization": "Bearer tok"}`. In `logifyx.yaml` write as a nested mapping. |

### Kafka Streaming

| Env Var | Python kwarg | Default | Description |
|---------|-------------|---------|-------------|
| `LOG_KAFKA_SERVERS` | `kafka_servers` | `None` | Comma-separated list of Kafka broker addresses. Setting this enables the Kafka handler. Example: `localhost:9092` or `b1:9092,b2:9092,b3:9092`. |
| `LOG_KAFKA_TOPIC` | `kafka_topic` | `"logs"` | Kafka topic logs are published to. The topic is created automatically if the broker is configured to allow it. |
| `LOG_SCHEMA_REGISTRY` | `schema_registry_url` | `None` | URL of a Confluent Schema Registry. When set, Logifyx registers its Avro schema on startup and serializes messages in Confluent wire format (5-byte header + Avro binary). When `None`, Logifyx still uses Avro binary but without the schema ID header. See the [Kafka Streaming guide](kafka.md#what-is-schema-registry) for details. |
| `LOG_SCHEMA_COMPATIBILITY` | `schema_compatibility` | `"BACKWARD"` | Schema evolution rule enforced by the Schema Registry. `BACKWARD` (default) means new schema versions can read data written by older versions. Other options: `FORWARD`, `FULL`, `NONE`. |

---

## Log Format

Console and file output uses this format:

```
2026-06-11 19:45:17 | INFO     | myapp:handle_request:42 - User logged in
│                      │          │     │              │     │
│                      │          │     │              │     └─ message
│                      │          │     │              └─ line number
│                      │          │     └─ function name (or filename if top-level)
│                      │          └─ logger name
│                      └─ level (padded to 8 chars)
└─ timestamp
```

Colors (when `color=True`, default):
- Date → green
- Level → level color (cyan/green/yellow/red/bold-red)
- `name:func:line` → blue
- Message → level color

JSON mode output (`json_mode=True`):
```json
{"timestamp": "2026-06-11 19:45:17", "level": "INFO", "logger": "myapp", "function": "handle_request", "line": 42, "message": "User logged in"}
```

---

## Configuration Methods

### Python kwargs (highest priority)

```python
from logifyx import Logifyx

log = Logifyx(
    name="myapp",
    level="DEBUG",
    color=True,
    json_mode=False,
    file="myapp.log",
    log_dir="logs",
    mask=True,
    max_bytes=10_000_000,
    backup_count=5,
    remote_url="http://log-server:5000/logs",
    remote_timeout=5,
    max_remote_retries=3,
    remote_headers={"Authorization": "Bearer token"},
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD",
)
```

### .env file

Loaded automatically from the working directory. Add to `.gitignore` — use it for secrets.

```env
# Core
LOG_LEVEL=INFO
LOG_MASK=true

# Console
LOG_COLOR=true
LOG_JSON=false

# File
LOG_FILE=app.log
LOG_DIR=logs
LOG_MAX_BYTES=10000000
LOG_BACKUP_COUNT=5

# Remote HTTP
LOG_REMOTE=http://log-server:5000/logs
LOG_REMOTE_TIMEOUT=5
LOG_REMOTE_RETRIES=3
LOG_REMOTE_HEADERS={"Authorization": "Bearer your-token"}

# Kafka
LOG_KAFKA_SERVERS=localhost:9092
LOG_KAFKA_TOPIC=app-logs
LOG_SCHEMA_REGISTRY=http://localhost:8081
LOG_SCHEMA_COMPATIBILITY=BACKWARD
```

### logifyx.yaml

Place in the project root. Good for non-secret defaults committed to version control.

```yaml
LOG_LEVEL: INFO
LOG_MASK: true

LOG_COLOR: true
LOG_JSON: false

LOG_FILE: app.log
LOG_DIR: logs
LOG_MAX_BYTES: 10000000
LOG_BACKUP_COUNT: 5

LOG_REMOTE: http://log-server:5000/logs
LOG_REMOTE_TIMEOUT: 5
LOG_REMOTE_RETRIES: 3
LOG_REMOTE_HEADERS:
  Content-Type: application/json
  Authorization: Bearer your-token

LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

---

## Log Levels

| Level | Value | When to use |
|-------|-------|-------------|
| `DEBUG` | 10 | Detailed tracing, variable dumps, step-by-step flow |
| `INFO` | 20 | Normal operational events (server started, user logged in) |
| `WARNING` | 30 | Unexpected but recoverable (deprecated API used, retry attempt) |
| `ERROR` | 40 | A failure that needs attention but did not crash the process |
| `CRITICAL` | 50 | A failure that may crash or corrupt the application |

---

## Viewing Resolved Config

Use the [CLI](cli.md) to see the fully merged config (all sources combined):

```bash
logifyx --config

# From a different directory
logifyx --config --config-dir ./my-service

# With explicit paths
logifyx --config --env-file ./deploy/.env --yaml-file ./deploy/logifyx.yaml
```

---

## See also

- [Handlers Reference](handlers.md) — what each handler does with these settings
- [Kafka Streaming](kafka.md) — deep dive on `LOG_KAFKA_*` and Schema Registry
- [CLI Reference](cli.md) — inspect the resolved config from the terminal
- [README](../README.md) — quick-start examples
