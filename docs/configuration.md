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

| Env Var | Python kwarg | Default | Accepted values | Description |
|---------|-------------|---------|-----------------|-------------|
| `LOG_LEVEL` | `level` | `"INFO"` | `DEBUG` `INFO` `WARNING` `ERROR` `CRITICAL` `NOTSET` | Minimum level to emit. Logs below this level are silently dropped. Invalid values raise `ValueError`. |
| `LOG_MASK` | `mask` | `true` | `true` / `false` only | Auto-mask sensitive values like `password=`, `token=`, `secret=`, `api_key=` in every handler. |

### Console Output

| Env Var | Python kwarg | Default | Accepted values | Description |
|---------|-------------|---------|-----------------|-------------|
| `LOG_COLOR` | `color` | `true` | `true` / `false` only | Color the console output by log level. Set `false` for plain text (e.g. when piping output to a file). |
| `LOG_JSON` | `json_mode` | `false` | `true` / `false` only | Emit each log as a single-line JSON object. `color` and `json_mode` are mutually exclusive — if both are `true`, `json_mode` wins. |

### File Output

| Env Var | Python kwarg | Default | Constraint | Description |
|---------|-------------|---------|------------|-------------|
| `LOG_FILE` | `file` | `<logger-name>.log` | str | Log file name inside `LOG_DIR`. Defaults to the logger name (e.g. `myapp.log`). |
| `LOG_DIR` | `log_dir` | `"logs"` | str | Directory where log files are written. Created automatically if it does not exist. |
| `LOG_MAX_BYTES` | `max_bytes` | `10000000` (10 MB) | int, >= 1 | Rotate the file when it reaches this size in bytes. |
| `LOG_BACKUP_COUNT` | `backup_count` | `5` | int, >= 0 | How many rotated backup files to keep (`app.log.1` … `app.log.N`). Set to `0` to keep none. |

### Remote HTTP

| Env Var | Python kwarg | Default | Constraint | Description |
|---------|-------------|---------|------------|-------------|
| `LOG_REMOTE` | `remote_url` | `None` | str | HTTP(S) endpoint URL. When set, every log record is POSTed as JSON in the background (non-blocking). |
| `LOG_REMOTE_TIMEOUT` | `remote_timeout` | `5` | int, >= 1 | Seconds to wait for the HTTP server to respond before timing out. |
| `LOG_REMOTE_RETRIES` | `max_remote_retries` | `3` | int, >= 0 | Consecutive failures allowed before the remote handler permanently disables itself (circuit breaker). |
| `LOG_REMOTE_HEADERS` | `remote_headers` | `{"Content-Type": "application/json"}` | dict[str, str] | Custom HTTP headers. In `.env`: valid JSON string. In YAML: nested mapping. Invalid JSON raises `ValueError`. |

### Kafka Streaming

| Env Var | Python kwarg | Default | Constraint | Description |
|---------|-------------|---------|------------|-------------|
| `LOG_KAFKA_SERVERS` | `kafka_servers` | `None` | str or list[str] | Kafka broker address(es). Example: `localhost:9092` or `b1:9092,b2:9092`. Setting this enables the Kafka handler. |
| `LOG_KAFKA_TOPIC` | `kafka_topic` | `"logs"` | str | Kafka topic logs are published to. |
| `LOG_SCHEMA_REGISTRY` | `schema_registry_url` | `None` | str | URL of a Confluent Schema Registry. When set, messages are serialized in Confluent wire format (5-byte header + Avro binary). See the [Kafka guide](kafka.md). |
| `LOG_SCHEMA_COMPATIBILITY` | `schema_compatibility` | `"BACKWARD"` | see below | Schema evolution rule. Must be one of: `BACKWARD`, `BACKWARD_TRANSITIVE`, `FORWARD`, `FORWARD_TRANSITIVE`, `FULL`, `FULL_TRANSITIVE`, `NONE`. Invalid values raise `ValueError`. |

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

## Validation Rules

Logifyx validates every value at configuration time and raises immediately on bad input — no silent fallbacks.

### Python kwargs (`Logifyx()` / `get_logify_logger()`)

| Type | Rule | Bad example → error |
|------|------|---------------------|
| bool (`color`, `mask`, `json_mode`) | Must be `True` or `False` — no strings, no ints | `color="true"` → `TypeError` |
| int (`max_bytes`) | Must be `int`, >= 1 | `max_bytes=0` → `ValueError` |
| int (`backup_count`, `max_remote_retries`) | Must be `int`, >= 0 | `backup_count=-1` → `ValueError` |
| int (`remote_timeout`) | Must be `int`, >= 1 | `remote_timeout="5"` → `TypeError` |
| str params | Must be `str` | `log_dir=123` → `TypeError` |
| `remote_headers` | Must be `dict[str, str]` | `remote_headers={"k": 1}` → `TypeError` |
| `kafka_servers` | `str` or `list[str]` | `kafka_servers=9092` → `TypeError` |
| `schema_compatibility` | One of the 7 valid values | `schema_compatibility="strict"` → `ValueError` |
| `level` | Valid level name (`str`) or plain `int`, not `bool` | `level=True` → `TypeError` |

> **Note:** `bool` is a subclass of `int` in Python, so `True` and `False` pass a plain `isinstance(x, int)` check. Logifyx rejects them explicitly for all `int` params.

### Env vars and YAML

| Type | Rule | Bad example → error |
|------|------|---------------------|
| bool (`LOG_COLOR`, `LOG_MASK`, `LOG_JSON`) | Only `"true"` or `"false"` (case-insensitive) | `LOG_COLOR=1` → `ValueError` |
| int env vars | Must parse as integer, must meet minimum | `LOG_MAX_BYTES=abc` → `ValueError` |
| `LOG_LEVEL` | Must be a valid level name | `LOG_LEVEL=verbose` → `ValueError` |
| `LOG_SCHEMA_COMPATIBILITY` | Must be one of the 7 valid values | `LOG_SCHEMA_COMPATIBILITY=strict` → `ValueError` |
| `LOG_REMOTE_HEADERS` | Must be a valid JSON object in `.env`; a mapping in YAML | `LOG_REMOTE_HEADERS=not-json` → `ValueError` |

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
