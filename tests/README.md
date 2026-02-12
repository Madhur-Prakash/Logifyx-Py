# Logify Test Suite

This directory contains comprehensive tests for the Logify logging library.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=logify --cov-report=term-missing

# Run specific test file
pytest tests/test_core.py -v

# Run specific test class
pytest tests/test_core.py::TestLogifyPresets -v
```

## Test Files

### [test_core.py](test_core.py)
Tests for the main `Logify` class functionality:
- **TestLogifyDirectInstantiation**: Validates direct `log = Logify(...)` usage without `.get_logger()`
- **TestLogifyPresets**: Tests `dev`, `prod`, and `simple` preset modes
- **TestLogifyReload**: Tests the `reload()` method for reconfiguring loggers
- **TestSentinelPattern**: Verifies sentinel pattern correctly detects explicitly provided parameters
- **TestFileLogging**: Tests file handler creation and log file output
- **TestConflictResolution**: Tests automatic conflict resolution (e.g., JSON mode disabled when color enabled)

### [test_filters.py](test_filters.py)
Tests for the `MaskFilter` class that redacts sensitive data:
- **TestMaskFilter**: Tests masking of passwords, tokens, secrets, API keys, and access tokens
- **TestMaskPatterns**: Validates the regex patterns used for sensitive data detection

### [test_config.py](test_config.py)
Tests for configuration loading from environment variables:
- **TestLoadConfigDefaults**: Verifies all default configuration values
- **TestLoadConfigEnvOverride**: Tests environment variable overrides (`LOGIFY_LEVEL`, `LOGIFY_COLOR`, etc.)
- **TestConfigStructure**: Validates config dictionary structure and types

### [test_context_and_registration.py](test_context_and_registration.py)
Tests for context injection and global registration:
- **TestContextLoggerAdapter**: Tests `ContextLoggerAdapter` for adding request IDs, user IDs, etc. to log messages
- **TestGlobalRegistration**: Tests `setup_logify()` and `get_logify_logger()` functions
- **TestMultipleLoggers**: Tests multiple logger instances and hierarchical naming

### [test_remote_and_formatter.py](test_remote_and_formatter.py)
Tests for remote logging and formatters:
- **TestRemoteHandler**: Tests HTTP-based remote logging with thread safety, retry logic, and failure tracking
- **TestFormatter**: Tests default, JSON, and color formatters
- **TestHandlerPayload**: Validates the structure of payloads sent to remote endpoints

### [test_integration.py](test_integration.py)
End-to-end integration tests:
- **TestEndToEndLogging**: Full workflow tests including file logging, context injection, and global registration
- **TestErrorScenarios**: Tests error handling and edge cases
- **TestConcurrentLogging**: Tests thread-safe concurrent logging to the same file

### [conftest.py](conftest.py)
Shared pytest fixtures used across all test files:
- `reset_logging_state`: Cleans up logging state between tests
- `temp_log_dir`: Creates temporary directories for file logging tests
- `log_record`: Factory for creating mock `LogRecord` objects
- `mock_response`: Factory for creating mock HTTP responses

### [run_tests.py](run_tests.py)
Standalone test runner script for running tests outside of pytest CLI.

## Test Coverage

The test suite covers:
- ✅ Direct instantiation API
- ✅ Preset modes (dev, prod, simple)
- ✅ Configuration loading and environment overrides
- ✅ Sensitive data masking
- ✅ File logging with rotation
- ✅ Remote HTTP logging
- ✅ Context injection (request IDs, user IDs)
- ✅ Global registration pattern
- ✅ Singleton enforcement
- ✅ Thread safety
- ✅ Error handling and recovery

## Adding New Tests

1. Create a new test file or add to an existing one
2. Use fixtures from `conftest.py` for common setup
3. Follow the existing naming convention: `test_<feature>.py`
4. Group related tests in classes: `class Test<Feature>:`
5. Use descriptive test names: `def test_<what_it_tests>:`
