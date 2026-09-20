# Changelog

All notable changes to Logifyx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.1.3...v2.0.0) - 2026-09-20

### Added

#### Configurable output destinations ([`output.py`](logifyx/output.py), [`handler.py`](logifyx/handler.py), [`core.py`](logifyx/core.py))

Logs can now be sent to the console, a file, both, or nowhere — the headline addition being **file-only logging with no terminal output at all**.

```python
from logifyx import configure_logging, get_logify_logger

configure_logging(level="INFO", output="file", log_file="logs/app.log")

logger = get_logify_logger("my_app")
logger.info("Application started")   # -> logs/app.log, nothing on stdout/stderr
```

| `output` | Console | File |
|----------|---------|------|
| `"both"` *(default)* | yes | yes |
| `"file"` | no | yes |
| `"console"` | yes | no |
| `"none"` | no | no |

`"both"` is the default, so existing behaviour is unchanged until you opt in. Aliases `console_only`, `file_only`, `console_and_file`, `off` and `disabled` are accepted, case-insensitively. `output` governs the console and file destinations only — remote HTTP and Kafka delivery are still controlled by `remote_url` / `kafka_servers`.

In `"none"` mode Logifyx attaches a `NullHandler`, so Python's `lastResort` fallback — which prints WARNING and above to stderr — cannot leak output.

Configurable everywhere: `output=` kwarg, `LOG_OUTPUT` / `LOGIFYX_OUTPUT` env var, `LOG_OUTPUT` in `logifyx.yaml`, and `logifyx --output file` on the CLI.

#### `configure_logging()` — process-wide configuration ([`core.py`](logifyx/core.py))

A single entry point that registers Logifyx as the logger class, stores settings as process-wide defaults, and re-applies them to every Logifyx logger that already exists.

```python
configure_logging(output="both", log_file="logs/app.log")
logger.info("test 1")        # terminal + file

configure_logging(output="file", log_file="logs/app.log")
logger.info("test 2")        # file only - the console handler is removed
```

Safe to call repeatedly. Each call **replaces** Logifyx-owned handlers instead of appending, so three identical calls still produce exactly one handler and one copy of each log line.

New priority chain:

```
per-logger kwargs > configure_logging() > env / .env > logifyx.yaml > defaults
```

Bad destinations are reported at the `configure_logging()` call site rather than at the first log call, and a rejected call leaves no half-applied state.

#### Handler ownership tracking ([`output.py`](logifyx/output.py))

Every handler Logifyx creates is stamped `_logifyx_managed` plus a role (`console`, `file`, `remote`, `kafka`, `queue`, `null`). Reconfiguration only ever touches stamped handlers, so handlers your application or a third-party library attached are never removed, closed, or reformatted.

Roles replace `isinstance` dispatch in `_build()`. Since `logging.FileHandler` subclasses `logging.StreamHandler`, the old check relied on a negative isinstance test to tell the two apart; role-based dispatch states the intent directly and cannot misclassify a future handler type.

#### Other additions

- `Logifyx.set_output(output, log_file=None, log_dir=None)` — switch a single logger's destination at runtime.
- `Logifyx.output` property — the resolved mode.
- `Logifyx.configure(..., replace=True)` — rebuild Logifyx handlers instead of no-opping.
- `reset_logging()` — clear process-wide defaults and detach Logifyx handlers. Useful in test suites.
- `get_global_config()` — read back the defaults set by `configure_logging()`.
- Exception hierarchy: `LogifyxError`, `LogifyxConfigurationError` (also a `ValueError`), `LogifyxFileError` (also a `RuntimeError`).
- `LOGIFYX_LEVEL`, `LOGIFYX_OUTPUT`, `LOGIFYX_LOG_FILE`, `LOGIFYX_LOG_DIR` env aliases, for environments where a bare `LOG_LEVEL` already belongs to another tool.
- CLI: `logifyx --output`, `--log-file`, `--level`, plus a destination summary showing exactly where records would land.
- `examples/output_modes.py` demonstrating every mode.

### Changed

#### **BREAKING:** `file` removed in favour of `log_file` ([`core.py`](logifyx/core.py), [`config.py`](logifyx/config.py))

The `file` kwarg was a filename resolved inside `log_dir`. `log_file` does the same job and more — it accepts a full path, creates missing directories, and still falls back to `log_dir` when given a bare file name — so the redundant parameter is gone.

```python
# Before (1.x)
Logifyx("api", log_dir="logs", file="api.log")

# After (2.0) - either form
Logifyx("api", log_file="logs/api.log")
Logifyx("api", log_dir="logs", log_file="api.log")
```

**Migration:**

| 1.x | 2.0 |
|-----|-----|
| `file="api.log"` | `log_file="api.log"` (still resolved inside `log_dir`) |
| `log_dir="logs", file="api.log"` | `log_file="logs/api.log"` |
| `config["file"]` | `config["log_file"]` |

Passing `file=` now raises `TypeError`. The `LOG_FILE` env var and YAML key keep their name and now map to `log_file`; the only behavioural difference is that a value carrying a directory part (`LOG_FILE=sub/api.log`) is treated as a path relative to the working directory rather than being nested inside `LOG_DIR`.

#### Log files are written as UTF-8

`ConcurrentRotatingFileHandler` is now created with `encoding="utf-8"` instead of inheriting the system locale encoding. Non-ASCII log messages no longer raise `UnicodeEncodeError` on Windows.

#### Handler teardown is ownership-aware

`reload()` and `reload_from_file()` previously removed and closed **every** handler on the logger, including ones the application had attached. They now only tear down Logifyx-owned handlers.

#### Misconfigured config paths warn instead of passing silently

`config_dir`, `env_file`, and `yaml_file` have always fallen back to auto-discovery when the path does not exist. That fallback is kept (removing it would break callers who rely on it), but an explicitly supplied path that does not resolve now emits a `RuntimeWarning` naming the bad value:

```python
configure_logging(config_dir="/etc/myap")   # typo for /etc/myapp

# RuntimeWarning: config_dir='/etc/myap' was given but is not an existing
# directory. Falling back to the current working directory (/app). Any .env or
# logifyx.yaml under '/etc/myap' will NOT be applied.
```

Previously a typo in a deployment silently loaded whatever happened to be in the working directory — usually nothing — and the only symptom was wrong log levels in production.

The warning is raised once per distinct bad path — `load_config()` runs once per logger plus once for eager validation, so a single typo would otherwise print several times — and is attributed to the caller's own line rather than to whichever Logifyx internal happened to call `load_config()`:

```
main.py:6: RuntimeWarning: config_dir='etc-myap' was given but is not an existing directory...
  configure_logging(config_dir="etc-myap", log_file="logs/app.log")
```

Warnings go through `warnings`, never through the logging system, which is still being configured at that point. `reset_logging()` clears the warned-path cache. Omitting the paths entirely, or pointing at a valid directory that simply has no `.env` / `logifyx.yaml`, is the normal zero-config case and stays silent.

#### Configuration errors raise the typed exception

Every invalid configuration value — from kwargs, env vars, `.env`, or `logifyx.yaml` — now raises `LogifyxConfigurationError` instead of a bare `ValueError`, so `except LogifyxError` catches all of them as the documentation describes. It subclasses `ValueError`, so existing `except ValueError` handlers are unaffected. Type errors continue to raise `TypeError`.

#### Async listener no longer drops other loggers' handlers

Reconfiguring one logger used to stop the shared `QueueListener` outright, silently disabling remote/Kafka delivery for every other logger. The listener now tracks its handler set and is rebuilt around it, so only the reconfigured logger's async handlers are detached.

### Fixed

#### `logger.exception()` silently dropped the traceback ([`formatter.py`](logifyx/formatter.py))

**Symptom:** the message was logged, the traceback was not — in both text and JSON mode.

```python
try:
    raise ValueError("boom")
except ValueError:
    log.exception("Something failed")

# BEFORE: 2026-09-20 18:30:12 | ERROR | app:main:4 - Something failed
# AFTER:  2026-09-20 18:30:12 | ERROR | app:main:4 - Something failed
#         Traceback (most recent call last):
#           ...
#         ValueError: boom
```

**Root cause:** `LogifyxFormatter.format()` and `PlainLogifyxFormatter.format()` returned `_format_line(...)` directly, bypassing the `record.exc_info` / `record.stack_info` tail that `logging.Formatter.format()` appends. `CompactJsonFormatter.format()` built a fixed dict that never included the traceback either.

**Fix:** both text formatters now append exception and stack text via a shared `_append_traceback()` helper, and the JSON formatter adds `"exception"` and `"stack_info"` keys. `json.dumps` escapes the newlines, so JSON records stay one line each and remain parseable line-by-line.

#### `level=` was ignored when passed to the constructor ([`core.py`](logifyx/core.py))

**Symptom:** `Logifyx("app", level="DEBUG")` emitted nothing below INFO.

```python
log = Logifyx("app", level="DEBUG")
log.debug("never appeared")     # dropped
```

**Root cause:** `level` is positional on `logging.Logger`, so `__init__` passed it to `super().__init__()` but never added it to `_init_params`. `configure()` then overwrote the level with the value from env/YAML/defaults.

**Fix:** an explicitly passed `level` (anything other than `NOTSET`) is now forwarded to `configure()`, where it takes priority as documented.

#### CLI crashed on legacy Windows codepages ([`cli.py`](logifyx/cli.py))

`logifyx --config` raised `UnicodeEncodeError` on terminals using cp1252, because the section banner contains non-ASCII characters. stdout is now reconfigured to UTF-8 with `errors="replace"` where the platform allows it.

### Tests

- New `tests/test_output_modes.py` — 84 tests covering console/file/both/none, reconfiguration, duplicate configuration, user-handler preservation, nested directory creation, multi-threaded writes, exception logging, JSON output, env/YAML config, priority, third-party logger isolation, error handling, and backward compatibility.
- The pre-existing suite has been brought back in line with the current API. It had been failing since the `mode="dev"/"prod"/"simple"` presets and the colorlog/python-json-logger formatter classes were removed in an earlier release. Full suite: **177 passed**, up from 54 passed / 36 failed.

---

## [1.1.3](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.1.2...v1.1.3) - 2026-07-29

### Fixed

#### `ContextLoggerAdapter` context fields silently dropped in JSON mode ([`formatter.py`](logifyx/formatter.py))

**Symptom:** Using `ContextLoggerAdapter` with a `json_mode=True` logger produced JSON output with no context fields at all:

```python
request_log = ContextLoggerAdapter(log, {"request_id": "req-abc123", "user_id": 42})
request_log.info("User authenticated")
# ❌ {"timestamp": "...", "level": "INFO", ..., "message": "User authenticated"}
# ✅ {"timestamp": "...", "level": "INFO", ..., "message": "User authenticated", "request_id": "req-abc123", "user_id": 42}
```

**Root cause:** `CompactJsonFormatter.format()` built a hardcoded 6-field dict (`timestamp`, `level`, `logger`, `function`, `line`, `message`). `ContextLoggerAdapter.process()` correctly merges context into `kwargs["extra"]`, which the logging machinery writes as extra attributes on the `LogRecord` — but the hardcoded formatter never read `record.__dict__`, so all context was silently discarded.

The same issue affected any field passed via `extra={"key": value}` on any log call — they appeared on the record but were never included in the output.

**Fix:** After building the base 6-field dict, the formatter now scans `record.__dict__` for any key that is not a standard `LogRecord` attribute and not underscore-prefixed, and includes it in the output:

```python
for key, value in record.__dict__.items():
    if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
        out[key] = value
```

`json.dumps` now also uses `default=str` so non-JSON-serialisable values (custom objects, datetimes) are converted to strings instead of crashing the formatter.

---

#### `MaskFilter` crashed on args that don't match format specifiers ([`filters.py`](logifyx/filters.py))

**Symptom:** Calling `log.info("User authenticated", some_value)` when masking was enabled raised `TypeError: not all arguments converted during string formatting` at the call site — even if the message had no `%s` placeholder.

**Root cause:** `MaskFilter.filter()` calls `record.getMessage()` to get the fully-formatted string before masking it. `filter()` is called by `Handler.handle()` — *outside* the `try/except` block that wraps `Handler.emit()`. So when `getMessage()` raised (because `"User authenticated" % (4,)` fails — no format specifier), the `TypeError` propagated all the way back to the original `log.info(...)` call site rather than being swallowed by the handler.

**Fix:** Wrap `getMessage()` in a `try/except TypeError` and fall back to `str(record.msg)` if formatting fails:

```python
try:
    msg = record.getMessage()
except TypeError:
    msg = str(record.msg)
```

---

#### `log.info("msg", value)` without a format specifier crashed instead of appending value ([`core.py`](logifyx/core.py))

**Symptom:** Passing a positional value for quick debugging — `log.info("User authenticated", user_id)` — crashed with `TypeError` because there was no `%s` placeholder in the message. Standard Python logging requires every positional arg to match a `%` format specifier.

**Fix:** `Logifyx` now overrides `_log()` to catch this case. If the args cannot be formatted into the message string, they are appended as a bracketed repr suffix and `args` is cleared before the record is created:

```python
log.info("User authenticated", user_id)
# → "User authenticated [42]"

log.info("port %d started", 8080)
# → "port 8080 started"  (standard % formatting, unchanged)
```

`%`-style formatting is fully preserved — the override only activates when `msg % args` would raise.

---

## [1.1.2](https://github.com/Madhur-Prakash/Logifyx-Py/compare/v1.1.1...v1.1.2) - 2026-07-17

### Added

#### Strict argument validation in `configure()` ([`core.py`](logifyx/core.py))

Every argument passed to `Logifyx()` or `get_logify_logger()` is now strictly validated before any configuration is applied. Previously, wrong types were silently accepted and either ignored or caused cryptic errors deep inside handlers.

- **str params** (`config_dir`, `env_file`, `yaml_file`, `remote_url`, `log_dir`, `file`, `kafka_topic`, `schema_registry_url`) — raises `TypeError` if not a `str`.
- **bool params** (`color`, `mask`, `json_mode`) — raises `TypeError` if not exactly `True` or `False`. Strings like `"true"`, integers like `1`, and other truthy values are rejected.
- **int params** with range enforcement:
  - `max_bytes` — must be `int`, `>= 1`
  - `backup_count` — must be `int`, `>= 0`
  - `remote_timeout` — must be `int`, `>= 1`
  - `max_remote_retries` — must be `int`, `>= 0`
  - `bool` is rejected for all int params (`isinstance(True, int)` is `True` in Python, so this is checked explicitly)
- **`kafka_servers`** — must be a `str` or `list[str]`. List entries are individually checked.
- **`remote_headers`** — must be `dict[str, str]`. Both keys and values are checked.
- **`schema_compatibility`** — must be one of `BACKWARD`, `BACKWARD_TRANSITIVE`, `FORWARD`, `FORWARD_TRANSITIVE`, `FULL`, `FULL_TRANSITIVE`, `NONE`. Raises `ValueError` for anything else.
- **`level`** — must be a valid level name (`str`) or a plain `int`. `bool` is rejected. Invalid strings raise `ValueError`.

#### Strict validation for env var and YAML values in `load_config()` ([`config.py`](logifyx/config.py))

- **Bool env vars** (`LOG_COLOR`, `LOG_MASK`, `LOG_JSON`) — now only accept `"true"` or `"false"` (case-insensitive). Previously accepted `"1"`, `"0"`, `"yes"`, `"no"`, `"on"`, `"off"`. Invalid values now raise `ValueError` instead of silently defaulting.
- **Int env vars** (`LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`, `LOG_REMOTE_TIMEOUT`, `LOG_REMOTE_RETRIES`) — non-numeric values raise `ValueError`. Out-of-range values raise `ValueError` with the minimum stated.
- **`LOG_LEVEL`** — validated against the set of valid level names. Invalid values raise `ValueError`.
- **`LOG_SCHEMA_COMPATIBILITY`** — validated against the seven valid compatibility modes. Invalid values raise `ValueError`.
- **`LOG_REMOTE_HEADERS`** — invalid JSON now raises `ValueError` instead of silently falling back to the default. A non-object JSON value (e.g. a list) also raises. In YAML, a non-mapping value raises.

---

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


