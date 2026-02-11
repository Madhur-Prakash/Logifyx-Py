<div align="center">

#  Logify


![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Kafka](https://img.shields.io/badge/Kafka-Streaming-orange?logo=apache-kafka)
![Avro](https://img.shields.io/badge/Avro-Schema-red)

**A modern, production-ready Python logging framework with zero configuration.**

[Quick Start](#-quick-start)  [Features](#-features)  [Configuration](#-configuration)  [Kafka Streaming](#-kafka-streaming)  [Documentation](#-documentation)

</div>

---

##  Features

| Feature | Description |
|---------|-------------|
|  **Colored Console Output** | Beautiful, readable logs with color-coded levels |
|  **Rotating File Logs** | Auto-rotating log files with size limits and backup |
|  **Remote HTTP Streaming** | Send logs to any HTTP endpoint in real-time |
|  **Kafka Streaming** | Stream logs to Apache Kafka with Avro serialization |
|  **Sensitive Data Masking** | Auto-mask passwords, tokens, and API keys |
|  **JSON Mode** | Structured JSON logging for log aggregators |
|  **YAML + ENV Config** | Configure via file, environment, or code |
|  **Zero Config Mode** | Works out of the box with sensible defaults |
|  **Preset Modes** | Quick setup with `dev`, `prod`, and `simple` presets |
|  **CLI Tool** | Inspect configuration from command line |

---

##  Installation

```bash
pip install logify
```

For Kafka streaming support:
```bash
pip install logify[kafka]
# or
pip install aiokafka fastavro
```

---

##  Quick Start

### Basic Usage (Zero Config)

```python
from logify import Logify

log = Logify(name="myapp").get_logger()

log.info("Application started")
log.warning("This is a warning")
log.error("Something went wrong")
```

### With Presets

```python
from logify import Logify

# Development mode: DEBUG level, colored output
log = Logify(name="myapp", mode="dev").get_logger()

# Production mode: INFO level, JSON output
log = Logify(name="myapp", mode="prod").get_logger()
```

### Full Configuration

```python
from logify import Logify

log = Logify(
    name="auth-service",
    mode="prod",
    level="DEBUG",
    file="auth.log",
    log_dir="logs",
    color=True,
    mask=True,  # Auto-mask sensitive data
    remote_url="http://localhost:5000/logs",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs"
).get_logger()

log.info("Server started on port 8080")
log.warning("password=secret123 token=abc")  # Masked: **** ****
log.error("Authentication failed", exc_info=True)
```

---

##  Preset Modes

| Mode | Level | Color | JSON | Use Case |
|------|-------|-------|------|----------|
| `dev` | DEBUG |  |  | Local development |
| `prod` | INFO |  |  | Production environments |
| `simple` | INFO |  |  | Basic logging |

```python
# Switch between modes easily
log = Logify(name="myapp", mode="dev").get_logger()   # Colorful debug logs
log = Logify(name="myapp", mode="prod").get_logger()  # JSON production logs
```

---

##  Configuration

Logify supports multiple configuration sources with the following priority:

```
Python Code Arguments > Environment Variables > logify.yaml > Defaults
```

### Using logify.yaml

Create a `logify.yaml` in your project root:

```yaml
LOG_LEVEL: DEBUG
LOG_FILE: app.log
LOG_DIR: logs
LOG_COLOR: True
LOG_JSON: False
LOG_MASK: True
LOG_MODE: dev

# Remote HTTP streaming
LOG_REMOTE: http://localhost:5000/logs

# Kafka streaming
LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

### Using Environment Variables

```bash
export LOG_LEVEL=DEBUG
export LOG_FILE=app.log
export LOG_KAFKA_SERVERS=localhost:9092
```

### Configuration Options

| Option | Env Variable | Default | Description |
|--------|--------------|---------|-------------|
| `level` | `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `file` | `LOG_FILE` | `app.log` | Log file name |
| `log_dir` | `LOG_DIR` | `logs` | Directory for log files |
| `color` | `LOG_COLOR` | `False` | Enable colored console output |
| `json_mode` | `LOG_JSON` | `False` | Enable JSON log format |
| `mask` | `LOG_MASK` | `True` | Mask sensitive data |
| `mode` | `LOG_MODE` | `dev` | Preset mode (dev/prod/simple) |
| `max_bytes` | `LOG_MAX_BYTES` | `10000000` | Max log file size before rotation |
| `backup_count` | `LOG_BACKUP_COUNT` | `5` | Number of backup files to keep |
| `remote_url` | `LOG_REMOTE` | `None` | HTTP endpoint for remote logging |
| `kafka_servers` | `LOG_KAFKA_SERVERS` | `None` | Kafka bootstrap servers |
| `kafka_topic` | `LOG_KAFKA_TOPIC` | `logs` | Kafka topic for logs |

 [Full Configuration Guide ](docs/configuration.md)

---

##  Sensitive Data Masking

Logify automatically masks sensitive data patterns:

```python
log = Logify(name="auth", mask=True).get_logger()

log.info("User login password=secret123 token=abc123")
# Output: User login **** ****
```

**Masked patterns:**
- `password=...`
- `token=...`
- `secret=...`
- `api_key=...`
- `access_key=...`
- `access_token=...`

---

##  Remote HTTP Streaming

Send logs to any HTTP endpoint in real-time:

```python
log = Logify(
    name="myapp",
    remote_url="http://localhost:5000/logs"
).get_logger()
```

**Payload format:**
```json
{
  "level": "INFO",
  "message": "User logged in",
  "service": "myapp",
  "time": 1707666000.123,
  "file": "/app/main.py",
  "line": 42
}
```

 [Remote Logging Guide ](docs/handlers.md#remote-http-handler)

---

##  Kafka Streaming

Stream logs to Apache Kafka with Avro serialization and Schema Registry support:

```python
from logify import Logify

log = Logify(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD"
).get_logger()

log.info("This goes to Kafka!")
```

### Features

- **Async Producer**: Non-blocking log delivery with `aiokafka`
- **Avro Serialization**: Efficient binary format with schema validation
- **Schema Registry**: Confluent Schema Registry integration
- **Schema Evolution**: BACKWARD, FORWARD, FULL compatibility modes
- **Circuit Breaker**: Auto-disables after repeated failures

### Quick Start with Docker

```bash
# Start Kafka + Schema Registry
cd examples
docker-compose up -d

# Run the demo
python examples/kafka_demo.py

# View logs
python examples/kafka_consumer.py
```

 [Full Kafka Guide ](docs/kafka.md)

---

##  CLI Tool

Inspect your Logify configuration from the command line:

```bash
# Show resolved configuration
logify --config

# Output:
#  Logify Configuration (logify.yaml: found):
# {
#     "level": "DEBUG",
#     "color": true,
#     "log_dir": "logs",
#     ...
# }
```

 [CLI Reference ](docs/cli.md)

---

##  Output Handlers

Logify writes logs to multiple destinations simultaneously:

| Handler | Description | Auto-enabled |
|---------|-------------|--------------|
| **Console** | Colored stdout output |  Always |
| **File** | Rotating file with backups |  Always |
| **Remote HTTP** | POST to HTTP endpoint | When `remote_url` set |
| **Kafka** | Stream to Kafka topic | When `kafka_servers` set |

 [Handlers Documentation ](docs/handlers.md)

---

##  Documentation

| Document | Description |
|----------|-------------|
| [Configuration Guide](docs/configuration.md) | Detailed configuration options |
| [Handlers Reference](docs/handlers.md) | All output handlers explained |
| [Kafka Streaming](docs/kafka.md) | Kafka + Avro + Schema Registry |
| [CLI Reference](docs/cli.md) | Command line interface |

---

##  Project Structure

```
logify/
 __init__.py      # Package exports
 core.py          # Main Logify class
 config.py        # Configuration loading
 handler.py       # Handler factory
 formatter.py     # Log formatters
 filters.py       # Sensitive data masking
 presets.py       # Mode presets (dev/prod/simple)
 remote.py        # HTTP remote handler
 kafka.py         # Kafka + Avro handler
 cli.py           # CLI tool
```

---

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

##  License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with  by [Madhur Prakash](https://github.com/madhurprakash)**

</div>
