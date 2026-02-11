# 🔧 CLI Reference

Logify includes a command-line interface for inspecting and debugging your logging configuration.

---

## Installation

The CLI is automatically available after installing Logify:

```bash
pip install logify
```

---

## Commands

### `logify --config`

Display the resolved Logify configuration from all sources.

```bash
logify --config
```

**Output:**

```
📦 Logify Configuration (logify.yaml: found):

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

**What it shows:**
- All resolved configuration values
- Whether `logify.yaml` was found
- Merged values from env, yaml, and defaults

---

### `logify --help`

Display help information.

```bash
logify --help
```

**Output:**

```
usage: logify [-h] [--config]

Logify CLI Tool

options:
  -h, --help  show this help message and exit
  --config    Show resolved Logify configuration (from logify.yaml + env)
```

---

## Configuration Resolution

The `--config` command shows the fully resolved configuration, merging:

1. **Environment variables** (highest priority)
2. **logify.yaml** (if present)
3. **Default values** (lowest priority)

### Example: Debugging Configuration

**logify.yaml:**
```yaml
LOG_LEVEL: DEBUG
LOG_FILE: app.log
LOG_COLOR: True
```

**.env:**
```
LOG_LEVEL=WARNING
```

**CLI output:**
```bash
$ logify --config

📦 Logify Configuration (logify.yaml: found):

{
    "level": "WARNING",    # From .env (overrides yaml)
    "file": "app.log",     # From yaml
    "color": true,         # From yaml
    ...
}
```

---

## Use Cases

### 1. Verify Configuration Before Deployment

```bash
# On your production server
export LOG_LEVEL=INFO
export LOG_KAFKA_SERVERS=kafka.prod:9092

logify --config
# Verify all settings are correct
```

### 2. Debug Missing Configuration

```bash
logify --config
# Check if logify.yaml was found
# Verify expected values are set
```

### 3. CI/CD Pipeline Validation

```bash
# In your deployment script
logify --config | grep "kafka_servers"
# Ensure Kafka is configured for production
```

---

## Configuration File Detection

The CLI looks for `logify.yaml` in the current working directory:

```bash
# Shows "logify.yaml: found"
$ cd /path/to/project  # Contains logify.yaml
$ logify --config

📦 Logify Configuration (logify.yaml: found):
...

# Shows "logify.yaml: not found"
$ cd /tmp  # No logify.yaml
$ logify --config

📦 Logify Configuration (logify.yaml: not found):
...
```

---

## Environment Variable Reference

All configuration can be set via environment variables:

| Variable | Description |
|----------|-------------|
| `LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FILE` | Log file name |
| `LOG_DIR` | Log directory |
| `LOG_COLOR` | Enable colors (True/False) |
| `LOG_JSON` | Enable JSON mode (True/False) |
| `LOG_MASK` | Enable masking (True/False) |
| `LOG_MODE` | Preset mode (dev/prod/simple) |
| `LOG_MAX_BYTES` | Max file size before rotation |
| `LOG_BACKUP_COUNT` | Number of backup files |
| `LOG_REMOTE` | Remote HTTP endpoint URL |
| `LOG_KAFKA_SERVERS` | Kafka bootstrap servers |
| `LOG_KAFKA_TOPIC` | Kafka topic name |
| `LOG_SCHEMA_REGISTRY` | Schema Registry URL |
| `LOG_SCHEMA_COMPATIBILITY` | Schema compatibility mode |

---

## Tips

### Quick Environment Check

```bash
# See just Kafka settings
logify --config | grep kafka

# See just file settings  
logify --config | grep -E "file|dir"
```

### Export for Comparison

```bash
# Save config to file
logify --config > config-snapshot.json

# Compare environments
diff config-dev.json config-prod.json
```

---

## Next Steps

- [Configuration Guide](configuration.md) - All configuration options
- [Handlers Reference](handlers.md) - Output handlers explained
- [Kafka Streaming](kafka.md) - Kafka setup guide
