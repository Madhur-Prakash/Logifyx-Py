# Changelog

All notable changes to Logifyx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.1.0...v1.1.1) - 2026-07-09

### Fixed

#### `get_logify_logger()` silently dropped kwargs ([`core.py`](logifyx/core.py))

**Symptom:** Calling `get_logify_logger("auth", log_dir="/custom", file="auth.log")` always
wrote logs to the default location (`./logs/auth.log`) regardless of what you passed.
Config kwargs were accepted without error but had no effect.

**Root cause:** Python's logging registry constructs the logger class by calling
`Logifyx(name)` with **only the name** — the stdlib manager has no mechanism to
forward extra parameters. This meant the sequence inside `get_logify_logger` was:

1. `logging.getLogger("auth")` fires. The registry sees the name for the first time and
   calls `Logifyx("auth")` — no kwargs, all parameters are sentinels.
2. Inside `__init__`, `provided` is empty, so `configure()` runs with pure defaults and
   builds handlers immediately.
3. Control returns to `get_logify_logger`. It checks `if not logger.handlers` — but
   handlers already exist from step 2. Both `configure()` and `__init__` contain an
   early-exit guard (`if self.handlers: return`) to prevent double-configuration.
   The user's kwargs hit that guard and are silently discarded.

The kwargs arrived one step too late. By the time `get_logify_logger` could apply them,
the logger was already fully built and locked.

**Fix:** A module-level dict `_init_kwargs` acts as a one-shot hand-off. Before calling
`logging.getLogger()`, `get_logify_logger` stores the caller's kwargs in that dict.
`__init__` pops them and merges them into `_init_params` before `configure()` runs,
so the user's values win. A `try/finally` block ensures the dict is always cleaned up —
for existing loggers the registry returns a cached instance without calling `__init__`,
so the entry is removed in the `finally` rather than inside `__init__`.

---

#### `MaskFilter` crashed on `%`-style log calls ([`filters.py`](logifyx/filters.py))

**Symptom:** Any standard `%`-style log call with positional args — e.g.
`log.info("Server started on port %d", 8080)` — raised
`TypeError: not all arguments converted during string formatting` whenever masking
was enabled (`mask=True`, which is the default). The exception propagated to the
call site rather than being swallowed quietly, crashing the caller.

**Root cause:** Python's logging stores the message template and its arguments
separately on the `LogRecord` (`record.msg` and `record.args`) and only combines
them when something calls `record.getMessage()`. `MaskFilter.filter()` called
`getMessage()` to get the final formatted string, masked it, and wrote it back to
`record.msg` — but never cleared `record.args`:

```python
# before fix
msg = record.getMessage()   # "pid=%d" % (1234,) → "pid=1234"
record.msg = msg            # plain string, no % placeholders remaining
# record.args = (1234,)     # ← never cleared
```

Later, the formatter called `record.getMessage()` a second time to build the log
line. `record.msg` was now a plain string with zero `%` placeholders, but
`record.args` was still `(1234,)`. Python's `%` operator raised because there were
leftover arguments with nothing to consume them.

The crash was not a quiet logging error: `Handler.handle()` calls `self.filter()`
before the `try/except` that wraps `emit()`, so the `TypeError` propagated all the
way back to the original `log.info(...)` call site.

**Fix:** Clear `record.args` immediately after rewriting `record.msg`:

```python
# after fix
record.msg = msg
record.args = None   # no second substitution attempted by the formatter
```

With `record.args = None`, `getMessage()` short-circuits to returning `record.msg`
directly — no `%` operation, no crash. Every handler sees the already-masked string.

## [1.1.0](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.6...v1.1.0) - 2026-06-11

### Changed

- **New log format** — output is now pipe-separated for both console and file:
  ```
  2026-06-11 19:45:17 | INFO     | myapp:handle_request:42 - User logged in
  ```
- **Color on by default** — no need to pass `color=True`; colored output is the default. Pass `color=False` to opt out (e.g. when piping to a file).
- **Full-line coloring** — when color is enabled, the entire log line is colored: date in green, level in its level color, `name:func:line` in blue, message in level color.
- **Removed preset/mode system** — the `mode` parameter (`dev`, `prod`, `simple`) has been removed from all APIs. Configure behavior directly via `color`, `level`, and `json_mode` kwargs or env vars.

### Fixed

- **`json_mode=True`** now outputs actual single-line JSON objects instead of the same text as plain mode. Each line is a valid JSON record: `{"timestamp": "...", "level": "...", "logger": "...", "function": "...", "line": N, "message": "..."}`.
- **`<module>` in JSON output** — top-level code no longer shows `"function": "<module>"`. The filename (without `.py`) is used instead.
- **`mask` config override bug** — `LOG_MASK=false` in `.env` or `logifyx.yaml` was silently ignored because `mask: bool = True` in `configure()` always overrode it. Changed to `mask: Optional[bool] = None` so env/yaml values are respected. Default behavior (masking on) is unchanged.
- **`LOG_REMOTE_HEADERS` env var** was undocumented despite being fully supported. Corrected in all docs.

### Documentation

- Comprehensive rewrite of all five documentation files:
  - **configuration.md** — full env var reference table with defaults, priority order, format diagram, config method examples
  - **handlers.md** — handler activation conditions, format examples, async architecture explained
  - **kafka.md** — what Avro is, what Schema Registry is, Docker Compose setup, all Kafka CLI commands, Python Avro consumer with wire format decoding, troubleshooting table
  - **cli.md** — complete env var quick reference, use-case examples, debug tips
  - **docs/README.md** — "Where to start" guide with cross-links between all docs

## [1.0.6](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.5...v1.0.6) - 2026-04-20

### Fixed

- Accepted lowercase log levels in `Logifyx`, e.g. `level="debug"` now works like `"DEBUG"`.
- Added clear validation errors for invalid level names with the list of supported values.

### Developer Experience

- Updated level type hints to accept both integer and string-based log levels.

## [1.0.5](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.4...v1.0.5) - 2026-04-14

### Release Notes

Logifyx 1.0.5 improves the default log file naming behavior so it now follows the logger name when no explicit file is configured.

### Highlights

- `Logifyx(name="billing-service")` now writes to `billing-service.log` by default.
- Explicit file configuration still wins, including `file=...`, `LOG_FILE`, `.env`, and `logifyx.yaml` values.
- Configuration loading now tracks whether the file name was explicitly provided, so name-based fallback only applies when it should.

### Compatibility

- Existing setups that already set a log file keep the same filename.
- This change only affects the default path used when no file name is configured anywhere.

## [1.0.4](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.3...v1.0.4) - 2026-04-14

### Fixed

- Unified configuration loading behavior between CLI and code usage.
- Added explicit config path support for both APIs and CLI:
  - Code: `Logifyx(..., config_dir=..., env_file=..., yaml_file=...)`
  - Code: `get_logify_logger(..., config_dir=..., env_file=..., yaml_file=...)`
  - CLI: `logifyx --config --config-dir ... --env-file ... --yaml-file ...`
- Default root behavior is now consistent: if no explicit path is passed, current working directory is used as config root.
- Fixed `.env` leakage between consecutive config loads in the same process by reading dotenv values directly for merge logic.
- Updated type stubs and docs to reflect the new path parameters and resolution rules.

### Root Cause

- CLI and runtime code paths were using different assumptions when discovering config files, causing mismatched behavior.
- Config loading relied on process-level dotenv mutation, which could preserve values across subsequent loads and produce confusing results.

### Verification

- Verified cwd-default config loading (`.env` + `logifyx.yaml`) in code path.
- Verified explicit `env_file`/`yaml_file` path loading in code path.
- Verified precedence remains `environment > .env > yaml > defaults`.

## [1.0.3](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.2...v1.0.3) - 2026-04-14

### Fixed

- Zero-config logger instantiation no longer skips setup when no optional keyword arguments are passed.
- `Logifyx(name="...")` now always attaches the console and file handlers, so `INFO` messages are emitted instead of falling through to Python's last-resort warning-only behavior.
- `get_logify_logger()` now also configures an uninitialized logger even when the caller only provides the logger name.

### Root Cause

- The constructor only called `configure()` when at least one explicit parameter was supplied.
- Passing `color=True` happened to make the `provided` map non-empty, which accidentally triggered configuration and made the issue look color-related.
- Without any explicit kwargs, no handlers were attached, so `INFO` logs were dropped while `WARNING` and above still appeared through the logging fallback path.

### Verification

- Confirmed that a plain `Logifyx(name="...")` instance now creates handlers and writes `INFO` messages to disk.
- Confirmed that the behavior matches the documented zero-config promise in the README.

## [1.0.2](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.1...v1.0.2) - 2026-04-02

### Changed

- Improved formatter output to ensure consistent and structured log formatting across all handlers.
- Better consistency in logging output across JSON and standard modes.

## [1.0.1](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.0.0...v1.0.1) - 2026-04-02

### Changed

- Refined CLI command descriptions for better clarity and usability.
- Enhanced configuration documentation with clearer explanations of available options.

### Documentation

- Updated README examples to provide a clearer and faster quick-start experience.
- Improved overall documentation structure for better readability and navigation.

## [1.0.0](https://github.com/Madhur-Prakash/Logifyx-Py/releases/tag/v1.0.0) - 2026-02-22

### Added

- **Core Logging**
  - `Logifyx` class extending `logging.Logger` with production-ready defaults
  - `ContextLoggerAdapter` for injecting request context (request_id, user_id, etc.)
  - Global registration via `setup_logify()` and `get_logify_logger()`
  - Hot reload support with `reload()` and `reload_from_file()` methods

- **Handlers**
  - Colored console output with `colorlog`
  - Rotating file handler with configurable size limits and backup count
  - `RemoteHandler` for HTTP log streaming with retry logic and auto-disable
  - `KafkaHandler` for Apache Kafka streaming with Avro serialization

- **Filters**
  - `MaskFilter` for automatic sensitive data masking (passwords, tokens, API keys)

- **Configuration**
  - YAML configuration via `logifyx.yaml`
  - Environment variable overrides
  - Preset modes: `dev`, `prod`, `simple`
  - JSON mode for structured logging

- **Architecture**
  - Thread-safe queue-based async logging for remote/Kafka handlers
  - Non-blocking log delivery with `QueueHandler` and `QueueListener`
  - Graceful shutdown with automatic flush via `atexit`
  - `flush()` and `shutdown()` functions for explicit control

- **CLI**
  - `logifyx config` - Display current configuration
  - `logifyx validate` - Validate YAML configuration file

- **Documentation**
  - Comprehensive README with examples
  - Handler documentation
  - Configuration guide
  - Kafka streaming guide


