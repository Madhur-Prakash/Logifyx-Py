[← Docs Index](README.md) · [Configuration](configuration.md) · [Handlers](handlers.md) · [Kafka](kafka.md) · [README](../README.md)

---

# CLI Reference

Logifyx ships a `logifyx` command that lets you inspect the fully resolved configuration from the terminal — useful for verifying settings before deployment or debugging why a value isn't what you expect.

---

## Installation

The CLI is installed automatically with the package:

```bash
pip install logifyx
logifyx --help
```

---

## Commands

### `logifyx --config`

Print the merged configuration that Logifyx would use if started from the current directory. Combines system env vars, `.env`, `logifyx.yaml`, and defaults — applying them in priority order.

```bash
logifyx --config
```

Example output:

```
Logifyx Configuration (logifyx.yaml: found):

{
    "level": "INFO",
    "color": true,
    "max_bytes": 10000000,
    "backup_count": 5,
    "log_dir": "logs",
    "file": "app.log",
    "json_mode": false,
    "mask": true,
    "remote_url": null,
    "remote_timeout": 5,
    "max_remote_retries": 3,
    "remote_headers": {"Content-Type": "application/json"},
    "kafka_servers": null,
    "kafka_topic": "logs",
    "schema_registry_url": null,
    "schema_compatibility": "BACKWARD"
}
```

### `logifyx --config-dir <path>`

Read `.env` and `logifyx.yaml` from a specific directory instead of the current working directory:

```bash
logifyx --config --config-dir ./services/auth
```

### `logifyx --env-file <path>` and `--yaml-file <path>`

Point to explicit file paths instead of relying on directory scanning:

```bash
logifyx --config --env-file ./deploy/prod.env --yaml-file ./deploy/logifyx.yaml
```

### `logifyx --help`

```bash
logifyx --help
```

---

## Environment Variable Reference

Every setting that can be in `.env` or `logifyx.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Minimum log level. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_COLOR` | `true` | Color console output by level. Set `false` for plain text. |
| `LOG_JSON` | `false` | Emit JSON lines instead of pipe-separated text. Incompatible with `LOG_COLOR`. |
| `LOG_MASK` | `true` | Auto-mask `password=`, `token=`, `secret=`, `api_key=` values. |
| `LOG_FILE` | `<name>.log` | Log file name inside `LOG_DIR`. |
| `LOG_DIR` | `logs` | Directory for log files. Created if it does not exist. |
| `LOG_MAX_BYTES` | `10000000` | Rotate the log file after it reaches this many bytes (10 MB). |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated backup files to keep. |
| `LOG_REMOTE` | `None` | HTTP(S) URL to POST log records to. Leave unset to disable. |
| `LOG_REMOTE_TIMEOUT` | `5` | HTTP request timeout in seconds. |
| `LOG_REMOTE_RETRIES` | `3` | Consecutive failures before the remote handler disables itself. |
| `LOG_REMOTE_HEADERS` | `{"Content-Type": "application/json"}` | JSON string of extra HTTP headers (e.g. `Authorization`). |
| `LOG_KAFKA_SERVERS` | `None` | Kafka bootstrap servers. Leave unset to disable. Example: `localhost:9092`. |
| `LOG_KAFKA_TOPIC` | `logs` | Kafka topic to publish log records to. |
| `LOG_SCHEMA_REGISTRY` | `None` | Confluent Schema Registry URL. Enables Confluent wire format. |
| `LOG_SCHEMA_COMPATIBILITY` | `BACKWARD` | Schema evolution rule. Options: `BACKWARD`, `FORWARD`, `FULL`, `NONE`. |

---

## Use Cases

### Verify config before deploying

```bash
export LOG_LEVEL=INFO
export LOG_KAFKA_SERVERS=kafka.prod:9092

logifyx --config
# Visually confirm all values are what you expect
```

### Check a specific setting

```bash
# Is Kafka configured?
logifyx --config | grep kafka_servers

# What log level will be used?
logifyx --config | grep level
```

### Compare dev vs prod

```bash
logifyx --config --env-file .env.dev  > config-dev.json
logifyx --config --env-file .env.prod > config-prod.json
diff config-dev.json config-prod.json
```

### Debug why a value is wrong

If a value is not what you expect, check the [priority order](configuration.md#configuration-guide):

1. Is it set as a real shell env var? (`echo $LOG_LEVEL`)
2. Is it in `.env`? (Does the file have duplicate keys? Last one wins.)
3. Is it in `logifyx.yaml`?
4. If none of the above, the default applies.

---

## See also

- [Configuration Guide](configuration.md) — complete env var reference with defaults and descriptions
- [Handlers Reference](handlers.md) — what gets enabled once config is applied
- [Kafka Streaming](kafka.md) — Kafka-specific CLI commands (topic, Schema Registry)
- [README](../README.md) — quick-start examples
