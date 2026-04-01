# Changelog

All notable changes to Logifyx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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


