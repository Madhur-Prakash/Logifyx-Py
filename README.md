<div align="center">

<img width="473" height="136" alt="ascii-art-text" src="https://github.com/user-attachments/assets/b2e7cc20-4491-4937-864c-54705bc1a97b" />


[![PyPI version](https://img.shields.io/pypi/v/logifyx.svg?logo=pypi&label=logifyx%20on%20PyPI)](https://pypi.org/project/logifyx/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/logifyx?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/logifyx)

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Kafka](https://img.shields.io/badge/Kafka-Streaming-orange?logo=apache-kafka)
![Avro](https://img.shields.io/badge/Avro-Schema-red)


**A modern, production-ready Python logging framework with zero configuration.**

[View on PyPI](https://pypi.org/project/logifyx/)

[Quick Start](#quick-start) • [Features](#features) • [Configuration](#configuration) • [Handlers](#handlers) • [Kafka Streaming](#kafka-streaming) • [CLI](#cli-tool) • [API Reference](#api-reference) • [Full Docs](docs/README.md)

</div>

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Upgrading to 2.0](#upgrading-to-20)
- [Quick Start](#quick-start)
- [Output Modes](#output-modes)
- [Configuration](#configuration)
- [Handlers](#handlers)
    - [Console Handler](#console-handler)
    - [File Handler](#file-handler)
    - [Remote HTTP Handler](#remote-http-handler)
    - [Kafka Handler](#kafka-handler)
- [Sensitive Data Masking](#sensitive-data-masking)
- [Context Injection](#context-injection)
- [Kafka Streaming](#kafka-streaming)
- [CLI Tool](#cli-tool)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Configurable Output** | Send logs to the console, a file, both, or nowhere |
| **File-Only Logging** | `output="file"` writes to disk with zero terminal output |
| **Colored Console Output** | Beautiful, readable logs with color-coded levels |
| **Rotating File Logs** | Auto-rotating log files with size limits and backup |
| **Remote HTTP Streaming** | Send logs to any HTTP endpoint in real-time |
| **Kafka Streaming** | Stream logs to Apache Kafka with Avro serialization |
| **Sensitive Data Masking** | Auto-mask passwords, tokens, and API keys |
| **JSON Mode** | Structured JSON logging for log aggregators |
| **YAML + ENV Config** | Configure via `yaml` file, environment, or code |
| **Zero Config Mode** | Works out of the box with sensible defaults |
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
- `python-json-logger` - JSON formatting
- `pyyaml` - YAML configuration
- `concurrent-log-handler` - Multi-process safe file handling
- `requests` - HTTP remote logging
- `python-dotenv` - Environment variable loading
- `aiokafka` - Async Kafka producer (optional)
- `fastavro` - Avro serialization (optional)

---

## Upgrading to 2.0

2.0 adds [output modes](#output-modes) and removes one redundant parameter.

### `file` → `log_file`

`file` was a filename resolved inside `log_dir`. `log_file` does the same job and more —
it takes a full path, creates missing directories, and still falls back to `log_dir` when
given a bare file name. Passing `file=` now raises `TypeError`.

| 1.x | 2.0 |
|-----|-----|
| `Logifyx("api", file="api.log")` | `Logifyx("api", log_file="api.log")` |
| `Logifyx("api", log_dir="logs", file="api.log")` | `Logifyx("api", log_file="logs/api.log")` |
| `log.config["file"]` | `log.config["log_file"]` |

The `LOG_FILE` env var and YAML key keep their name and now map to `log_file`. The only
behavioural difference: a value carrying a directory part (`LOG_FILE=sub/api.log`) is now
a path relative to the working directory rather than being nested inside `LOG_DIR`.

### Everything else is backward compatible

`Logifyx()`, `get_logify_logger()`, `setup_logify()`, `ContextLoggerAdapter`, `flush()`,
`shutdown()`, `reload()`, masking, JSON mode, rotation, remote HTTP and Kafka all behave
as before. Two long-standing bugs were fixed along the way — `logger.exception()` now
writes the traceback, and `Logifyx("app", level="DEBUG")` now honours the level. See the
[CHANGELOG](CHANGELOG.md) for details.

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

By default Logifyx writes to **both** the console and a rotating log file. If you do not pass `log_file=...`, the file is named after the logger, so the example above creates `logs/myapp.log`.

To write to a file and keep the terminal completely silent, see [Output Modes](#output-modes).

### Full Configuration

```python
from logifyx import Logifyx

log = Logifyx(
    name="auth-service",
    log_file="logs/auth.log",
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
from logifyx import configure_logging, get_logify_logger

# Call once at app startup — sets the policy for the whole process
configure_logging(level="INFO", output="file", log_file="logs/app.log")

# Now use get_logify_logger anywhere in your app
log = get_logify_logger("auth")
api_log = get_logify_logger("api")
```

Each logger can still override the shared policy:

```python
audit = get_logify_logger("audit", log_file="logs/audit.log")   # own file
debug = get_logify_logger("debug", output="both")               # also on console
```

If you want Logifyx loggers but *no* process-wide policy — each logger
configuring itself, or a library that must not impose settings on its host —
use `setup_logify()` instead. See
[`setup_logify()` vs `configure_logging()`](#setup_logify-vs-configure_logging).

```python
from logifyx import setup_logify, get_logify_logger

setup_logify()
log = get_logify_logger("auth", output="file", log_file="logs/auth.log")
```

### Context Injection (Request Tracking)

```python
from logifyx import Logifyx, ContextLoggerAdapter

log = Logifyx(name="auth")

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

## Output Modes

> **Upgrading from 1.x?** `output` is new and defaults to `both`, so your logs keep going
> to the console and a file. One breaking change: the `file` kwarg was removed in favour
> of `log_file` — see [Upgrading to 2.0](#upgrading-to-20).

Logifyx sends every log record to a **destination**. The `output` setting decides which
destinations exist:

| `output` | Console | Log file | Use it when |
|----------|---------|----------|-------------|
| `"both"` *(default)* | ✅ | ✅ | Local development — see logs and keep them |
| `"file"` | ❌ | ✅ | Daemons, cron jobs, servers — **no terminal output at all** |
| `"console"` | ✅ | ❌ | Containers where a log collector reads stdout/stderr |
| `"none"` | ❌ | ❌ | Tests, or when your app installs its own handlers |

`output` controls the console and file destinations only. Remote HTTP and Kafka delivery
stay governed by `remote_url` / `kafka_servers`, so you can stream to Kafka while the
terminal stays quiet.

### File-only logging (no terminal output)

```python
from logifyx import configure_logging, get_logify_logger

configure_logging(
    level="INFO",
    output="file",
    log_file="logs/app.log"
)

logger = get_logify_logger("my_app")

logger.info("Application started")
logger.error("Something failed")
```

`logs/app.log`:

```text
2026-09-20 18:30:12 | INFO     | my_app:main:14 - Application started
2026-09-20 18:30:12 | ERROR    | my_app:main:15 - Something failed
```

Terminal:

```text
<no output>
```

**Nothing** is written to `stdout` or `stderr` in this mode — not by Logifyx, and not by
Python's `lastResort` fallback. The `logs/` directory is created for you, including
nested paths such as `logs/2026/09/app.log`.

### Console only

```python
configure_logging(output="console")
```

No log file is opened at all — Logifyx will not create `logs/` or touch the disk.

### Both (the default)

```python
configure_logging(output="both", log_file="logs/app.log")
```

`both` is the default, so log destinations behave exactly as they did in 1.x unless you
opt into another mode.

### Disabling Logifyx output

```python
configure_logging(output="none")
```

Logifyx attaches a `NullHandler` and emits nothing anywhere. Useful in libraries and test
suites.

### Friendlier spellings

If you prefer to spell the intent out, these are accepted everywhere `output` is:

| You write | Resolves to |
|-----------|-------------|
| `"console_only"` | `"console"` |
| `"file_only"` | `"file"` |
| `"console_and_file"` | `"both"` |
| `"off"`, `"disabled"` | `"none"` |

Values are case-insensitive. Anything unrecognised raises `LogifyxConfigurationError`
listing the valid modes.

### Switching modes at runtime

Calling `configure_logging()` again **replaces** Logifyx's handlers rather than adding to
them, so the console handler is genuinely removed — not just muted:

```python
configure_logging(output="both", log_file="logs/app.log")
logger.info("test 1")        # terminal + logs/app.log

configure_logging(output="file", log_file="logs/app.log")
logger.info("test 2")        # logs/app.log only
```

Calling it repeatedly with the same settings is safe and never duplicates log lines:

```python
configure_logging(output="file")
configure_logging(output="file")
configure_logging(output="file")

logger.info("hello")         # appears exactly once in the file
```

To switch a single logger without touching the rest of the application, use
`set_output()`:

```python
log = get_logify_logger("audit")
log.set_output("file", log_file="logs/audit.log")
log.output                   # "file"
```

### Your own handlers are never touched

Logifyx stamps every handler it creates. Reconfiguration only ever replaces stamped
handlers, so anything you attached yourself survives:

```python
import logging
from logifyx import configure_logging, get_logify_logger

log = get_logify_logger("my_app")
log.addHandler(logging.handlers.SysLogHandler())   # yours

configure_logging(output="file", log_file="logs/app.log")

# Your SysLogHandler is still attached, with its own formatter and level.
```

The same applies in reverse: Logifyx loggers set `propagate = False` and never attach
handlers to the root logger, so configuring Logifyx cannot silence or duplicate logging
from `urllib3`, `requests`, `httpx`, `uvicorn`, `fastapi`, or anything else.

### Environment variables and YAML

```bash
export LOG_OUTPUT=file
export LOG_FILE=logs/app.log
export LOG_LEVEL=INFO
```

```yaml
# logifyx.yaml
LOG_OUTPUT: file
LOG_FILE: logs/app.log
LOG_LEVEL: INFO
```

The `LOGIFYX_`-prefixed spellings `LOGIFYX_OUTPUT`, `LOGIFYX_LOG_FILE`, `LOGIFYX_LEVEL`
and `LOGIFYX_LOG_DIR` are accepted as aliases, for environments where a bare `LOG_LEVEL`
already belongs to another tool.

Explicit Python configuration always wins over the environment — see
[Configuration](#configuration) for the full priority chain.

---

## Configuration

Logifyx supports multiple configuration sources with clear priority:

```
Per-logger kwargs > configure_logging() > Environment Variables > logifyx.yaml > Defaults
```

`configure_logging()` sets process-wide defaults; kwargs passed to a specific logger are
more specific and therefore win:

```python
configure_logging(output="file", log_file="logs/app.log")

audit = Logifyx("audit", output="console")   # keeps its console output
```

### 1. Python Code (Highest Priority)

```python
from logifyx import Logifyx

log = Logifyx(
    name="myapp",
    level="DEBUG",
    output="file",
    log_file="logs/myapp.log",
    color=True,
    mask=True
)
```

Or set it once for the whole process:

```python
from logifyx import configure_logging

configure_logging(
    level="DEBUG",
    output="file",
    log_file="logs/myapp.log"
)
```

### 2. Environment Variables

Set environment variables with the `LOG_` prefix:

```bash
# Linux/macOS
export LOG_LEVEL=DEBUG
export LOG_OUTPUT=file
export LOG_FILE=logs/app.log
export LOG_COLOR=True
export LOG_KAFKA_SERVERS=localhost:9092

# Windows PowerShell
$env:LOG_LEVEL = "DEBUG"
$env:LOG_OUTPUT = "file"
$env:LOG_FILE = "logs/app.log"
```

Or use a `.env` file (loaded automatically via `python-dotenv`):

```env
LOG_LEVEL=DEBUG
LOG_OUTPUT=file
LOG_FILE=logs/app.log
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

# ---- Output Settings ----
LOG_OUTPUT=both                         # console, file, both (default), none
LOG_FILE=logs/app.log                   # Log file path (directories auto-created)
LOG_DIR=logs                            # Directory used when LOG_FILE has no dir part
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
LOG_OUTPUT: file
LOG_FILE: logs/app.log
LOG_DIR: logs
LOG_COLOR: True
LOG_JSON: False
LOG_MASK: True

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
| `level` | `LOG_LEVEL` | `LOG_LEVEL` | `"INFO"` | Minimum log level. One of: `DEBUG` `INFO` `WARNING` `ERROR` `CRITICAL` `NOTSET`. Invalid values raise `ValueError`. |

#### Output Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `output` | `LOG_OUTPUT` | `LOG_OUTPUT` | `"both"` | Where logs go: `console`, `file`, `both`, or `none`. `file` produces no terminal output. Aliases: `console_only`, `file_only`, `console_and_file`, `off`. |
| `log_file` | `LOG_FILE` | `LOG_FILE` | `<name>.log` | Log file path, e.g. `logs/app.log`. Missing directories are created automatically. A bare file name is placed inside `log_dir`. Defaults to the logger name. |
| `log_dir` | `LOG_DIR` | `LOG_DIR` | `"logs"` | Directory used when `log_file` has no directory part |
| `color` | `LOG_COLOR` | `LOG_COLOR` | `True` | Colorize console output. Python: `True`/`False` only. Env/YAML: `true`/`false` only. |
| `json_mode` | `LOG_JSON` | `LOG_JSON` | `False` | Emit each line as JSON. Mutually exclusive with `color` — `json_mode` wins if both are set. |
| `mask` | `LOG_MASK` | `LOG_MASK` | `True` | Redact passwords, tokens, and secrets in all output. |

#### File Rotation Settings

| Option | Env Variable | YAML Key | Default | Constraint | Description |
|--------|--------------|----------|---------|------------|-------------|
| `max_bytes` | `LOG_MAX_BYTES` | `LOG_MAX_BYTES` | `10000000` | int, >= 1 | Rotate the file when it reaches this size in bytes. |
| `backup_count` | `LOG_BACKUP_COUNT` | `LOG_BACKUP_COUNT` | `5` | int, >= 0 | Number of rotated backup files to keep. `0` keeps none. |

#### Remote HTTP Settings

| Option | Env Variable | YAML Key | Default | Constraint | Description |
|--------|--------------|----------|---------|------------|-------------|
| `remote_url` | `LOG_REMOTE` | `LOG_REMOTE` | `None` | str | HTTP endpoint URL |
| `remote_timeout` | `LOG_REMOTE_TIMEOUT` | `LOG_REMOTE_TIMEOUT` | `5` | int, >= 1 | Request timeout in seconds |
| `max_remote_retries` | `LOG_REMOTE_RETRIES` | `LOG_REMOTE_RETRIES` | `3` | int, >= 0 | Failures before the remote handler self-disables |
| `remote_headers` | `LOG_REMOTE_HEADERS` | `LOG_REMOTE_HEADERS` | `{"Content-Type": "application/json"}` | dict[str, str] | Custom HTTP headers. In env/`.env`: JSON string. In YAML: nested mapping. |

#### Kafka Settings

| Option | Env Variable | YAML Key | Default | Description |
|--------|--------------|----------|---------|-------------|
| `kafka_servers` | `LOG_KAFKA_SERVERS` | `LOG_KAFKA_SERVERS` | `None` | Kafka bootstrap servers. `str` or `list[str]`. |
| `kafka_topic` | `LOG_KAFKA_TOPIC` | `LOG_KAFKA_TOPIC` | `"logs"` | Kafka topic name |
| `schema_registry_url` | `LOG_SCHEMA_REGISTRY` | `LOG_SCHEMA_REGISTRY` | `None` | Schema Registry URL |
| `schema_compatibility` | `LOG_SCHEMA_COMPATIBILITY` | `LOG_SCHEMA_COMPATIBILITY` | `"BACKWARD"` | Schema compatibility mode. One of: `BACKWARD` `BACKWARD_TRANSITIVE` `FORWARD` `FORWARD_TRANSITIVE` `FULL` `FULL_TRANSITIVE` `NONE`. |

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

Logifyx writes logs to several destinations simultaneously. Which ones exist depends on
your configuration — you never register handlers manually.

| Handler | Description | Enabled when |
|---------|-------------|--------------|
| **Console** | Colored terminal output | `output` is `console` or `both` *(default)* |
| **File** | Rotating file with backups | `output` is `file` or `both` *(default)* |
| **Remote HTTP** | POST to HTTP endpoint | `remote_url` is set |
| **Kafka** | Stream to Kafka topic | `kafka_servers` is set |

See [Output Modes](#output-modes) for how to turn the console or file destination off.

### Console Handler

**Enabled by default** (`output="both"`). Writes to the terminal with optional color coding.
Set `output="file"` or `output="none"` to remove it entirely.

Like the standard library's `StreamHandler`, records are written to `stderr`.

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
2026-06-11 19:45:17 | INFO     | myapp:<module>:42 - Server started
2026-06-11 19:45:18 | WARNING  | myapp:<module>:56 - High memory usage
2026-06-11 19:45:19 | ERROR    | myapp:handle_request:78 - Connection failed
```

### File Handler

**Enabled by default** (`output="both"`). Writes to a rotating file with automatic backup
management. Set `output="console"` or `output="none"` to skip opening a file at all.

#### Features

- **Rotating files**: Automatically rotates when file reaches size limit
- **Backup management**: Keeps N backup files, deletes oldest
- **Concurrent-safe**: Uses `ConcurrentRotatingFileHandler`, which takes an inter-process
  lock around every write — safe across threads *and* processes
- **Auto-creates directories**: Creates the log directory, including nested parents
- **UTF-8**: Files are always written as UTF-8, regardless of system locale

```python
log = Logifyx(
    name="myapp",
    output="file",              # file only - no terminal output
    log_file="logs/myapp.log",  # path; directories created as needed
    max_bytes=10_000_000,       # 10MB max file size
    backup_count=5              # Keep 5 backup files
)
```

`log_file` accepts either a full path or a bare file name:

```python
log_file="logs/myapp.log"                  # -> logs/myapp.log
log_dir="/var/log/myapp", log_file="a.log" # -> /var/log/myapp/a.log
# nothing set                              # -> logs/<logger name>.log
```


#### One file, or one file per logger?

This is decided by whether anything names the log file:

```python
# Omit log_file -> each logger writes its own file, named after itself
configure_logging(output="file", log_dir="logs")

get_logify_logger("billing").info("...")     # logs/billing.log
get_logify_logger("auth").info("...")        # logs/auth.log
```

```python
# Name it -> every logger shares that one file
configure_logging(output="file", log_dir="logs", log_file="app.log")

get_logify_logger("billing").info("...")     # logs/app.log
get_logify_logger("auth").info("...")        # logs/app.log
```

Naming the file is treated as a deliberate instruction, so Logifyx does not
substitute the logger name into it. Dotted logger names become dotted file names:
`get_logify_logger("app.billing")` writes `logs/app.billing.log`.

Sharing one file is safe. Each logger gets its own handler pointing at the same
path, and `ConcurrentRotatingFileHandler` takes an inter-process lock around
every write, so records interleave cleanly across threads and processes. Every
line carries the logger name, so a shared file stays greppable:

```
2026-09-20 22:14:01 | INFO | billing:charge:88 - payment captured
2026-09-20 22:14:01 | INFO | auth:login:24    - session opened
```

One caveat: `max_bytes` and `backup_count` apply to the combined stream, so a
chatty logger rotates the quiet ones' history out faster.

For a custom layout, give each logger its own path — directories are created
as needed:

```python
get_logify_logger("billing", log_file="logs/money/billing.log")
get_logify_logger("auth",    log_file="logs/security/auth.log")
```

Or keep a shared default and carve out exceptions, since a per-logger kwarg
outranks the `configure_logging()` default:

```python
configure_logging(output="file", log_file="logs/app.log")   # everything here...
get_logify_logger("audit", log_file="logs/audit.log")       # ...except this
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

See [Kafka Streaming](#kafka-streaming) section for detailed documentation.

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

log = Logifyx(name="auth")

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
    image: obsidiandynamics/kafka
    restart: "no"
    ports:
      - "2181:2181"
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_LISTENERS: "INTERNAL://:29092,EXTERNAL://:9092"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka:29092,EXTERNAL://localhost:9092"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: "INTERNAL"
      KAFKA_ZOOKEEPER_SESSION_TIMEOUT: "6000"
      KAFKA_RESTART_ATTEMPTS: "10"
      KAFKA_RESTART_DELAY: "5"
      ZOOKEEPER_AUTOPURGE_PURGE_INTERVAL: "0"

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
    "output": "both",
    "log_dir": "logs",
    "log_file": "logs/app.log",
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

#### `logifyx --output <mode>`

Preview the resolved configuration with an output mode applied, and see exactly where log
records would land:

```bash
logifyx --output file
logifyx --output both
logifyx --output file --log-file logs/app.log --level DEBUG
```

**Output (tail):**

```
Destinations:

   console: disabled - nothing is written to stdout/stderr
   file:    /srv/myapp/logs/app.log
```

`--output`, `--log-file`, and `--level` imply `--config`, so you do not have to pass both.
They only preview a configuration — they do not write to `logifyx.yaml`.

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
    level: int | str = logging.NOTSET,    # Log level
    output: str = None,                   # console | file | both | none
    log_file: str = None,                 # Log file path, e.g. "logs/app.log"
    log_dir: str = None,                  # Directory when log_file has no dir part
    json_mode: bool = None,               # JSON output
    remote_url: str = None,               # HTTP endpoint
    mask: bool = None,                    # Mask sensitive data (default: True)
    color: bool = None,                   # Colored output
    backup_count: int = None,             # Backup files count
    max_bytes: int = None,                # Max file size
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
| `configure(**kwargs)` | Configure the logger with all options. Pass `replace=True` to rebuild existing Logifyx handlers |
| `set_output(output, log_file=None, log_dir=None)` | Switch this logger's destination at runtime |
| `reload()` | Reload logger configuration and handlers |
| `reload_from_file()` | Reload configuration from `logifyx.yaml` |

| Property | Description |
|----------|-------------|
| `output` | The resolved output mode: `"console"`, `"file"`, `"both"`, or `"none"` |

`reload()`, `reload_from_file()`, `set_output()` and `configure(replace=True)` only replace
handlers Logifyx created. Handlers your application attached are left untouched.

### `configure_logging()` Function

Configure Logifyx for the whole process. The recommended entry point — call once at startup.

```python
from logifyx import configure_logging

configure_logging(
    level: int | str = None,       # Minimum level
    output: str = None,            # console | file | both | none
    log_file: str = None,          # e.g. "logs/app.log"; dirs created automatically
    log_dir: str = None,           # Directory when log_file has no dir part
    color: bool = None,            # Colorize console output
    json_mode: bool = None,        # Single-line JSON records
    mask: bool = None,             # Redact passwords/tokens/secrets
    max_bytes: int = None,         # Rotate at this size
    backup_count: int = None,      # Rotated backups to keep
    remote_url: str = None,        # HTTP endpoint (async)
    remote_timeout: int = None,
    max_remote_retries: int = None,
    remote_headers: dict = None,
    kafka_servers: str = None,
    kafka_topic: str = None,
    schema_registry_url: str = None,
    schema_compatibility: str = None,
    config_dir: str = None,
    env_file: str = None,
    yaml_file: str = None,
    reset: bool = False            # Discard previous defaults instead of merging
)
```

It registers Logifyx as the logger class (so `setup_logify()` is not needed separately),
stores the settings as process-wide defaults, and re-applies them to every Logifyx logger
that already exists.

**Safe to call repeatedly** — each call replaces Logifyx's handlers rather than adding to
them, so log lines are never duplicated.

**Raises:**

| Exception | When |
|-----------|------|
| `TypeError` | A value has the wrong type |
| `LogifyxConfigurationError` | A value is out of range, or `output` is not a valid mode. Also a `ValueError`. |
| `LogifyxFileError` | The log file or its directory cannot be created. Also a `RuntimeError`. |

### `reset_logging()` Function

Clear the process-wide defaults and detach every Logifyx-owned handler. Handlers your
application attached are left in place. Mainly useful in test suites.

```python
from logifyx import reset_logging

reset_logging()
```

### `get_global_config()` Function

Return a copy of the process-wide defaults set by `configure_logging()`.

```python
from logifyx import get_global_config

get_global_config()   # {"output": "file", "log_file": "logs/app.log"}
```

### Exceptions

```python
from logifyx import LogifyxError, LogifyxConfigurationError, LogifyxFileError
```

| Exception | Base classes | Raised for |
|-----------|--------------|------------|
| `LogifyxError` | `Exception` | Base class for every Logifyx error |
| `LogifyxConfigurationError` | `LogifyxError`, `ValueError` | Invalid configuration values |
| `LogifyxFileError` | `LogifyxError`, `RuntimeError` | Log file/directory cannot be created |

Each subclass also inherits the builtin exception Logifyx raised before this hierarchy
existed, so existing `except ValueError` / `except RuntimeError` code keeps working.

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
    level: int | str = None,     # Minimum level
    output: str = None,          # console | file | both | none
    log_file: str = None,        # e.g. "logs/auth.log"
    **kwargs                     # Same options as the Logifyx constructor
)
```

**Requires `configure_logging()` or `setup_logify()` first** — either one
registers Logifyx as the logger class. Without one, this raises `TypeError`.

**One instance per name — the first call wins.** Every later call with the same
name returns that same configured object and *ignores* the kwargs:

```python
log = get_logify_logger("billing", log_file="logs/a.log")   # creates it
log = get_logify_logger("billing", log_file="logs/b.log")   # kwargs ignored,
                                                            # still logs/a.log
```

That is what lets `get_logify_logger("billing")` return the same logger from
anywhere in your codebase. The practical consequence: put per-logger settings on
the first call — usually at module import in the module that owns the logger.
To change one afterwards, use `set_output()` rather than calling
`get_logify_logger()` again:

```python
log.set_output("file", log_file="logs/money/billing.log")
```

### `setup_logify()` Function

Register Logifyx as the global logger class, and nothing else.

```python
from logifyx import setup_logify

setup_logify()  # Call once at app startup
```

#### `setup_logify()` vs `configure_logging()`

| | `setup_logify()` | `configure_logging()` |
|---|---|---|
| Registers `Logifyx` as the logger class | ✅ | ✅ |
| Stores process-wide defaults | ❌ | ✅ |
| Rebuilds handlers on existing loggers | ❌ | ✅ |

`configure_logging()` does the registration too, so you never need both.

Reach for `configure_logging()` in an application — one logging policy for the
process is normally what you want. Reach for `setup_logify()` when each logger
should configure itself, or **inside a library**, which must not overwrite the
logging settings of the application using it.

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

### Output Modes Demo

A runnable walkthrough of every mode lives in
[`examples/output_modes.py`](examples/output_modes.py):

```bash
python examples/output_modes.py
```

### Basic Demo

```python
from logifyx import Logifyx, ContextLoggerAdapter, get_logify_logger, setup_logify, flush

# Direct instantiation
log = Logifyx(
    name="auth",
    log_file="logs/auth.log",
    color=True,
    mask=True
)

log.info("Server started")
log.warning("password=123456 token=abcd123")  # Masked
log.error("Login failed")

# Global registration
setup_logify()
api_log = get_logify_logger("api", log_file="logs/api.log")
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
├── core.py          # Logifyx class, configure_logging(), logger registry
├── config.py        # Configuration loading (env / .env / YAML)
├── output.py        # Output modes + handler ownership
├── exceptions.py    # LogifyxError hierarchy
├── handler.py       # Handler factory
├── formatter.py     # Log formatters
├── filters.py       # Sensitive data masking
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

**Made with ❤️ by [Madhur Prakash](https://github.com/Madhur-Prakash)**

[Report Bug](https://github.com/Madhur-Prakash/Logifyx-Py/issues) • [Request Feature](https://github.com/Madhur-Prakash/Logifyx-Py/discussions)

</div>
