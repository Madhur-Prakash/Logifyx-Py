[← Docs Index](README.md) · [Configuration](configuration.md) · [Handlers](handlers.md) · [CLI](cli.md) · [README](../README.md)

---

# Kafka Streaming Guide

Stream logs to Apache Kafka with Avro serialization and optional Schema Registry support.

---

## What is Avro and why does Logifyx use it?

**Avro** is a binary serialization format. Instead of sending logs as plain JSON text, Logifyx converts each log record into a compact binary blob using a fixed schema. This means:

- **Smaller messages** — binary is more compact than JSON text
- **Schema enforcement** — every producer and consumer agrees on exactly what fields exist and their types
- **Schema evolution** — you can add optional fields to the schema later without breaking existing consumers

When you also set `schema_registry_url`, Logifyx registers its schema with Confluent Schema Registry on startup. Each message then gets a 5-byte header (magic byte `0x00` + 4-byte schema ID) prepended — this is called the **Confluent wire format**. Consumers can use the schema ID to look up the schema and deserialize the message correctly even if the schema changes over time.

Without `schema_registry_url`, Logifyx still serializes in Avro binary, just without the header.

---

## What is Schema Registry?

The **Confluent Schema Registry** is a separate service (you run it alongside Kafka) that stores a versioned history of your Avro schemas. Its roles:

1. **Single source of truth** — producers register their schema once; consumers fetch it by ID
2. **Compatibility enforcement** — rejects schema changes that would break existing consumers (controlled by `schema_compatibility`)
3. **Decoupling** — producers and consumers don't need to share schema files manually

You do **not** need Schema Registry to use Kafka logging. If `schema_registry_url` is `None`, Logifyx sends raw Avro binary and consumers must have the schema themselves.

---

## Quick Start

### 1. Install dependencies

```bash
# Minimal Kafka support
pip install aiokafka fastavro

# Or install everything at once
pip install logifyx[kafka]
```

### 2. Start Kafka (Docker)

Save this as `docker-compose.yml` in your project:

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
# Start both services
docker compose up -d

# Watch startup (Schema Registry takes ~30 seconds after Kafka is healthy)
docker compose logs -f

# Verify Kafka is up
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Verify Schema Registry is up
curl http://localhost:8081/subjects
# Expected: [] (empty list, no schemas yet)
```

### 3. Use Kafka logging

```python
from logifyx import Logifyx

log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",  # optional but recommended
    schema_compatibility="BACKWARD",
)

log.info("Application started")
log.warning("High memory usage")
log.error("Connection refused", exc_info=True)
```

---

## Configuration

### Python

```python
log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",          # required to enable Kafka
    kafka_topic="app-logs",                  # default: "logs"
    schema_registry_url="http://localhost:8081",  # default: None (no registry)
    schema_compatibility="BACKWARD",         # default: "BACKWARD"
)
```

### .env

```env
LOG_KAFKA_SERVERS=localhost:9092
LOG_KAFKA_TOPIC=app-logs
LOG_SCHEMA_REGISTRY=http://localhost:8081
LOG_SCHEMA_COMPATIBILITY=BACKWARD
```

### logifyx.yaml

```yaml
LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

---

## Avro Schema

Each log record is serialized using this schema:

```json
{
  "type": "record",
  "name": "LogRecord",
  "namespace": "com.logifyx.logs",
  "fields": [
    {"name": "level",          "type": "string",           "doc": "DEBUG / INFO / WARNING / ERROR / CRITICAL"},
    {"name": "message",        "type": "string",           "doc": "The log message"},
    {"name": "service",        "type": "string",           "doc": "Logger name"},
    {"name": "timestamp",      "type": "string",           "doc": "ISO 8601 UTC timestamp"},
    {"name": "file",           "type": ["null", "string"], "default": null, "doc": "Source file path"},
    {"name": "line",           "type": ["null", "int"],    "default": null, "doc": "Line number"},
    {"name": "function",       "type": ["null", "string"], "default": null, "doc": "Function name"},
    {"name": "exception",      "type": ["null", "string"], "default": null, "doc": "Full exception traceback, if any"},
    {"name": "extra",          "type": ["null", "string"], "default": null, "doc": "Any extra fields as a JSON string"},
    {"name": "schema_version", "type": "int",              "default": 1,    "doc": "Schema version for evolution tracking"}
  ]
}
```

---

## Schema Compatibility Modes

Set via `schema_compatibility` / `LOG_SCHEMA_COMPATIBILITY`.

| Mode | What it means | When to use |
|------|--------------|-------------|
| `BACKWARD` *(default)* | New schema can read data written by the **old** schema | Adding new optional fields with defaults |
| `BACKWARD_TRANSITIVE` | New schema can read data written by **any previous** version | Strict long-term backward compat |
| `FORWARD` | Old schema can read data written by the **new** schema | Removing optional fields |
| `FORWARD_TRANSITIVE` | Any old schema can read data written by the new schema | Strict long-term forward compat |
| `FULL` | Both BACKWARD and FORWARD | Most restrictive, safest for shared schemas |
| `FULL_TRANSITIVE` | FULL across all historical versions | Maximum safety |
| `NONE` | No checks | Development / prototyping only |

**Rule of thumb:** Use `BACKWARD` unless you have a specific reason not to. It lets you add new optional fields to the schema without breaking any existing consumer that is already running.

---

## CLI Commands

### Inspect the topic

```bash
# List all topics
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list

# Describe a topic (partitions, replication, etc.)
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe --topic app-logs

# Create a topic manually (Logifyx creates it automatically if auto.create.topics.enable=true)
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic app-logs --partitions 3 --replication-factor 1
```

### Read messages from the topic

```bash
# Read all messages from the beginning (raw bytes — Avro will not be human-readable)
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic app-logs \
  --from-beginning

# Read only new messages
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic app-logs
```

### Inspect Schema Registry

```bash
# List all registered subjects (one per topic-value by default)
curl http://localhost:8081/subjects

# Get all versions of a subject
curl http://localhost:8081/subjects/app-logs-value/versions

# Get the latest schema for a subject
curl http://localhost:8081/subjects/app-logs-value/versions/latest

# Check the compatibility mode set for a subject
curl http://localhost:8081/config/app-logs-value
```

---

## Consuming Messages (Python)

```python
import asyncio
import io
import json
import fastavro
from aiokafka import AIOKafkaConsumer
from fastavro.schema import parse_schema
from logifyx.kafka import LOG_SCHEMA_V1

PARSED_SCHEMA = parse_schema(LOG_SCHEMA_V1)

async def consume():
    consumer = AIOKafkaConsumer(
        "app-logs",
        bootstrap_servers="localhost:9092",
        auto_offset_reset="earliest",
        group_id="log-viewer",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            raw = msg.value

            # Confluent wire format: first byte is 0x00, next 4 bytes are schema ID
            if raw[0] == 0:
                raw = raw[5:]  # strip the 5-byte header before deserializing

            record = fastavro.schemaless_reader(io.BytesIO(raw), PARSED_SCHEMA)
            print(f"[{record['level']}] {record['service']} — {record['message']}")
    finally:
        await consumer.stop()

asyncio.run(consume())
```

---

## Production Setup

### Multiple brokers

```python
log = Logifyx(
    name="myapp",
    kafka_servers="kafka1:9092,kafka2:9092,kafka3:9092",
    kafka_topic="app-logs",
)
```

### Circuit breaker

The handler disables itself after 5 consecutive send failures to avoid blocking or flooding a broken broker. Once disabled it stays disabled until the process restarts — check your broker health if you see logs stop flowing to Kafka.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `KafkaConnectionError` | Kafka not running or wrong address | `docker compose ps` — verify broker is healthy |
| Schema Registry `500` on startup | Kafka not ready yet | Wait 30–60 s after Kafka starts, then retry |
| Messages look like binary garbage in console consumer | Avro binary format | Use the Python consumer above to deserialize |
| `ImportError: aiokafka` | Kafka extras not installed | `pip install aiokafka fastavro` |
| Logs stop going to Kafka silently | Circuit breaker tripped (5 failures) | Check broker connectivity; restart the process |

---

## See also

- [Configuration Guide](configuration.md) — full `LOG_KAFKA_*` env var reference with defaults
- [Handlers Reference](handlers.md) — how the Kafka handler fits alongside Console, File, and HTTP handlers
- [CLI Reference](cli.md) — verify Kafka settings are resolved correctly before deploying
- [README](../README.md) — quick-start examples
