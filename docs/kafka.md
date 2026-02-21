# 📡 Kafka Streaming Guide

Stream your logs to Apache Kafka with Avro serialization and Schema Registry support for enterprise-grade log aggregation.

---

## Overview

Logifyx's Kafka handler provides:

- **Async Producer**: Non-blocking log delivery using `aiokafka`
- **Avro Serialization**: Efficient binary format with schema validation
- **Schema Registry**: Confluent Schema Registry integration
- **Schema Evolution**: BACKWARD, FORWARD, FULL compatibility modes
- **Circuit Breaker**: Automatic disable after repeated failures
- **Compression**: Gzip compression for efficient network usage

---

## Quick Start

### 1. Install Dependencies

```bash
pip install aiokafka fastavro
```

### 2. Start Kafka (Docker)

```bash
cd examples
docker-compose up -d
```

### 3. Use Kafka Logging

```python
from logifyx import Logifyx

log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs"
)

log.info("This message goes to Kafka!")
```

---

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `kafka_servers` | Kafka bootstrap servers | Required |
| `kafka_topic` | Topic to publish logs | `"logs"` |
| `schema_registry_url` | Schema Registry URL | `None` |
| `schema_compatibility` | Schema compatibility mode | `"BACKWARD"` |

### Python Configuration

```python
log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD"
)
```

### YAML Configuration

```yaml
# logifyx.yaml
LOG_KAFKA_SERVERS: localhost:9092
LOG_KAFKA_TOPIC: app-logs
LOG_SCHEMA_REGISTRY: http://localhost:8081
LOG_SCHEMA_COMPATIBILITY: BACKWARD
```

### Environment Variables

```bash
export LOG_KAFKA_SERVERS=localhost:9092
export LOG_KAFKA_TOPIC=app-logs
export LOG_SCHEMA_REGISTRY=http://localhost:8081
export LOG_SCHEMA_COMPATIBILITY=BACKWARD
```

---

## Avro Schema

Logs are serialized using this Avro schema (v1):

```json
{
  "type": "record",
  "name": "LogRecord",
  "namespace": "com.logifyx.logs",
  "doc": "Log record schema v1",
  "fields": [
    {
      "name": "level",
      "type": "string",
      "doc": "Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    },
    {
      "name": "message",
      "type": "string",
      "doc": "Log message"
    },
    {
      "name": "service",
      "type": "string",
      "doc": "Service/logger name"
    },
    {
      "name": "timestamp",
      "type": "string",
      "doc": "ISO8601 timestamp"
    },
    {
      "name": "file",
      "type": ["null", "string"],
      "default": null,
      "doc": "Source file path"
    },
    {
      "name": "line",
      "type": ["null", "int"],
      "default": null,
      "doc": "Line number"
    },
    {
      "name": "function",
      "type": ["null", "string"],
      "default": null,
      "doc": "Function name"
    },
    {
      "name": "exception",
      "type": ["null", "string"],
      "default": null,
      "doc": "Exception traceback if any"
    },
    {
      "name": "extra",
      "type": ["null", "string"],
      "default": null,
      "doc": "Extra JSON data"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version for evolution"
    }
  ]
}
```

---

## Schema Compatibility Modes

When using Schema Registry, you can enforce schema evolution rules:

| Mode | Description | Use Case |
|------|-------------|----------|
| `BACKWARD` | New schema can read old data | Adding optional fields |
| `BACKWARD_TRANSITIVE` | All previous schemas | Strict backward compatibility |
| `FORWARD` | Old schema can read new data | Removing optional fields |
| `FORWARD_TRANSITIVE` | All future schemas | Strict forward compatibility |
| `FULL` | Both backward and forward | Most restrictive |
| `FULL_TRANSITIVE` | All versions both ways | Maximum compatibility |
| `NONE` | No compatibility checks | Development only |

### Recommended: BACKWARD Compatibility

```python
log = Logifyx(
    name="myapp",
    kafka_servers="localhost:9092",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD"  # New readers can read old data
)
```

**BACKWARD compatibility allows:**
- ✅ Adding new optional fields (with defaults)
- ✅ Adding new fields with default values
- ❌ Removing fields
- ❌ Changing field types

---

## Docker Setup

### docker-compose.yml

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

### Starting the Stack

```bash
# Start Kafka and Schema Registry
docker-compose up -d

# Wait for services to be ready (about 30-60 seconds)
docker-compose ps

# Check Kafka is healthy
docker-compose logs kafka | tail -20
```

---

## Consuming Logs

### Python Consumer

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
            # Parse Avro or JSON
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

### Kafka Console Consumer

```bash
# View raw messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic app-logs \
  --from-beginning
```

---

## Production Considerations

### Multiple Kafka Brokers

```python
log = Logifyx(
    name="myapp",
    kafka_servers="kafka1:9092,kafka2:9092,kafka3:9092",
    kafka_topic="app-logs"
)
```

### Authentication (SASL/SSL)

The Kafka handler supports additional kwargs passed to `aiokafka`:

```python
from logifyx import Logifyx

# Note: For advanced Kafka config, configure the handler directly
# or extend the KafkaHandler class
```

### Topic Partitioning

Logs are partitioned by service name (key):

```python
# Messages with same service name go to same partition
# This ensures ordering per service
await producer.send_and_wait(
    topic,
    value=serialized_log,
    key=record.name.encode('utf-8')  # Service name as key
)
```

### Circuit Breaker

The handler automatically disables after 5 consecutive failures:

```python
# Internal behavior:
self.max_failures = 5
self.failures = 0
self.disabled = False

# On each failure:
self.failures += 1
if self.failures >= self.max_failures:
    self.disabled = True  # No more attempts
```

---

## Troubleshooting

### Connection Errors

```
KafkaConnectionError: Unable to bootstrap from localhost:9092
```

**Solutions:**
1. Ensure Kafka is running: `docker-compose ps`
2. Check network: `telnet localhost 9092`
3. Verify `KAFKA_ADVERTISED_LISTENERS` in docker-compose

### Schema Registry Errors

```
Schema registry connection failed
```

**Solutions:**
1. Check Schema Registry is running: `curl http://localhost:8081`
2. Verify Kafka is healthy first (Schema Registry depends on it)
3. Wait 30-60 seconds after startup

### Import Errors

```
ImportError: aiokafka is required for Kafka logging
```

**Solution:**
```bash
pip install aiokafka fastavro
```

---

## Example: Full Demo

```python
"""
Kafka Logging Demo - examples/kafka_demo.py
"""

from logifyx import Logifyx

log = Logifyx(
    name="kafka-demo",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD",
    color=True
)

# Send test logs
log.info("Application started")
log.debug("Debug message")
log.warning("Warning message")

try:
    1 / 0
except Exception:
    log.error("Exception occurred", exc_info=True)

log.info("Application finished")
print("✅ Logs sent to Kafka!")
```

---

## Next Steps

- [Configuration Guide](configuration.md) - All configuration options
- [Handlers Reference](handlers.md) - All output handlers
- [CLI Reference](cli.md) - Command line tools
