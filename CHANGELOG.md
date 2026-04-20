# Changelog

All notable changes to Logifyx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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


