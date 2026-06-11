[← Docs Index](README.md) · [Configuration](configuration.md) · [Kafka](kafka.md) · [CLI](cli.md) · [README](../README.md)

---

# Handlers Reference

Logifyx writes logs to multiple destinations simultaneously. Handlers are created automatically based on your configuration — you never register them manually.

---

## Overview

| Handler | Always on? | Enabled when |
|---------|-----------|--------------|
| Console | Yes | Always |
| File | Yes | Always |
| Remote HTTP | No | `remote_url` is set |
| Kafka | No | `kafka_servers` is set |

---

## Console Handler

Writes every log record to stdout.

### Log format

```
2026-06-11 19:45:17 | INFO     | myapp:handle_request:42 - User logged in
```

- Timestamp — always green
- Level — color-coded by severity (cyan / green / yellow / red / bold-red)
- `name:function:line` — blue
- Message — color-coded by severity

Color is on by default (`LOG_COLOR=true`). Pass `color=False` to get plain text — useful when you pipe stdout to a file or another tool. All color and format settings are listed in the [Configuration Guide](configuration.md#console-output).

### Color map

| Level | Color |
|-------|-------|
| DEBUG | Cyan |
| INFO | Green |
| WARNING | Yellow |
| ERROR | Red |
| CRITICAL | Bold Red |

### JSON mode

When `json_mode=True` (or `LOG_JSON=true`), each record is a single-line JSON object instead:

```json
{"timestamp": "2026-06-11 19:45:17", "level": "INFO", "logger": "myapp", "function": "handle_request", "line": 42, "message": "User logged in"}
```

`color` and `json_mode` are mutually exclusive. If both are set, `json_mode` is silently disabled.

---

## File Handler

Writes logs to a rotating file. Always enabled alongside the console handler.

- Multi-process safe (`ConcurrentRotatingFileHandler`)
- Log directory is created automatically if it does not exist
- Plain text format (no ANSI color codes)

```python
log = Logifyx(
    name="myapp",
    file="myapp.log",       # default: <name>.log
    log_dir="logs",          # default: logs/
    max_bytes=10_000_000,    # rotate when file hits 10 MB
    backup_count=5,          # keep 5 old files
)
```

### Rotation behaviour

When `myapp.log` hits `max_bytes`:
1. `myapp.log.4` → deleted
2. `myapp.log.3` → `myapp.log.4`
3. `myapp.log.2` → `myapp.log.3`
4. `myapp.log.1` → `myapp.log.2`
5. `myapp.log`   → `myapp.log.1`
6. New empty `myapp.log` is created

---

## Remote HTTP Handler

POSTs log records as JSON to an HTTP endpoint. Enabled when `remote_url` is set.

Runs fully in the background — the main thread is never blocked waiting for HTTP.

```
your code → log.info()
               ↓
         QueueHandler  (instant, non-blocking)
               ↓
         QueueListener (background thread)
               ↓
         RemoteHandler → HTTP POST → your server
```

```python
log = Logifyx(
    name="myapp",
    remote_url="http://log-server:5000/logs",
    remote_timeout=5,           # seconds before giving up on one request
    max_remote_retries=3,       # disable handler after this many consecutive failures
    remote_headers={"Authorization": "Bearer token"},
)
```

### Payload

```json
{
  "level": "INFO",
  "message": "User logged in",
  "service": "myapp",
  "timestamp": 1749657917.123,
  "file": "/app/auth.py",
  "line": 42,
  "func": "handle_login",
  "exception": null
}
```

### Circuit breaker

After `max_remote_retries` consecutive failures the handler marks itself disabled and stops trying. This prevents a dead log server from slowing your app. The handler re-enables on the next process restart.

### Example receiving server (Flask)

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/logs", methods=["POST"])
def receive():
    data = request.json
    print(f"[{data['level']}] {data['service']}: {data['message']}")
    return {"status": "ok"}, 200

app.run(port=5000)
```

---

## Kafka Handler

Streams log records to a Kafka topic using Avro serialization. Enabled when `kafka_servers` is set.

Like the Remote HTTP handler, Kafka sends happen in the background via a `QueueHandler` + `QueueListener`.

```python
log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",  # optional
    schema_compatibility="BACKWARD",
)
```

See the [Kafka Streaming guide](kafka.md) for full setup instructions including Docker, CLI commands, Avro schema, and a Python consumer.

---

## Sensitive Data Masking

All handlers run log messages through `MaskFilter` when `mask=True` (default). The following patterns are replaced with `****`:

| Pattern matched | Example |
|----------------|---------|
| `password=<value>` | `password=secret` → `****` |
| `token=<value>` | `token=abc123` → `****` |
| `secret=<value>` | `secret=xyz` → `****` |
| `api_key=<value>` | `api_key=key` → `****` |
| `access_key=<value>` | `access_key=k` → `****` |
| `access_token=<value>` | `access_token=t` → `****` |

Masking happens before the record reaches any handler, so the value never appears in the file, remote payload, or Kafka message either.

---

## See also

- [Configuration Guide](configuration.md) — all env vars that control handler behaviour
- [Kafka Streaming](kafka.md) — full Kafka + Avro + Schema Registry setup
- [CLI Reference](cli.md) — inspect which handlers will be active for a given config
- [README](../README.md) — quick-start examples
