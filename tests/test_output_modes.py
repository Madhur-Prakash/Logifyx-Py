"""
Tests for configurable output destinations: console / file / both / none.

The central guarantee under test is that ``output="file"`` writes to the log
file and emits nothing at all to the terminal — not via stdout, not via stderr,
and not through a duplicate handler left behind by an earlier configuration.
"""

import contextlib
import io
import json
import logging
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logifyx import (
    LogifyxConfigurationError,
    LogifyxFileError,
    Logifyx,
    configure_logging,
    get_logify_logger,
    get_global_config,
    reset_logging,
    setup_logify,
)
from logifyx.core import _instances, _stop_queue_listener
from logifyx.output import (
    ROLE_CONSOLE,
    ROLE_FILE,
    is_owned,
    resolve_log_target,
    role_of,
)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def clean_logifyx_state():
    """Give every test a pristine process-wide logging state."""
    original_class = logging.getLoggerClass()

    reset_logging()
    _instances.clear()
    _stop_queue_listener()
    logging.Logger.manager.loggerDict.clear()
    logging.setLoggerClass(logging.Logger)

    yield

    reset_logging()
    _instances.clear()
    _stop_queue_listener()
    logging.Logger.manager.loggerDict.clear()
    logging.setLoggerClass(original_class)


@contextlib.contextmanager
def captured_console():
    """
    Capture everything Logifyx would print to the terminal.

    Both streams are swapped *before* any handler is built, because
    logging.StreamHandler() binds to whatever sys.stderr is at construction
    time — redirecting afterwards would silently miss real console output and
    make a broken file-only mode look like it passed.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


def console_text(out, err):
    return out.getvalue() + err.getvalue()


def read_log(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def log_path(tmp_path):
    """A log file path inside a directory that does not exist yet."""
    return str(tmp_path / "logs" / "app.log")


# --------------------------------------------------------------------------- #
# Test 1 — Console only
# --------------------------------------------------------------------------- #


class TestConsoleOnly:

    def test_console_only_writes_to_terminal_not_file(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="console", log_file=log_path, color=False)
            log = get_logify_logger("t1_console")
            log.info("hello")

        assert "hello" in console_text(out, err)
        assert not os.path.exists(log_path), "console mode must not open a log file"

    def test_console_only_creates_no_file_handler(self, log_path):
        with captured_console():
            configure_logging(output="console", log_file=log_path)
            log = get_logify_logger("t1_roles")

        roles = {role_of(h) for h in log.handlers}
        assert ROLE_CONSOLE in roles
        assert ROLE_FILE not in roles


# --------------------------------------------------------------------------- #
# Test 2 — File only (the headline feature)
# --------------------------------------------------------------------------- #


class TestFileOnly:

    def test_file_only_writes_to_file_and_nothing_to_terminal(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="file", log_file=log_path, level="INFO")
            log = get_logify_logger("t2_file")
            log.info("hello")

        assert out.getvalue() == "", "file-only mode wrote to stdout"
        assert err.getvalue() == "", "file-only mode wrote to stderr"
        assert "hello" in read_log(log_path)

    def test_file_only_silences_every_level(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="file", log_file=log_path, level="DEBUG")
            log = get_logify_logger("t2_levels")
            log.debug("d")
            log.info("i")
            log.warning("w")
            log.error("e")
            log.critical("c")

        assert console_text(out, err) == ""
        content = read_log(log_path)
        for msg in ("d", "i", "w", "e", "c"):
            assert msg in content

    def test_file_only_has_no_stream_handler(self, log_path):
        with captured_console():
            configure_logging(output="file", log_file=log_path)
            log = get_logify_logger("t2_handlers")

        roles = [role_of(h) for h in log.handlers]
        assert roles == [ROLE_FILE]
        # Belt and braces: no bare StreamHandler snuck in under another name.
        for handler in log.handlers:
            assert not (
                isinstance(handler, logging.StreamHandler)
                and not isinstance(handler, logging.FileHandler)
            )

    def test_file_only_does_not_propagate_to_root(self, log_path):
        """A root handler must not become a backdoor to the terminal."""
        root_stream = io.StringIO()
        root_handler = logging.StreamHandler(root_stream)
        logging.root.addHandler(root_handler)
        try:
            with captured_console() as (out, err):
                configure_logging(output="file", log_file=log_path)
                log = get_logify_logger("t2_propagate")
                log.info("no leaking")

            assert console_text(out, err) == ""
            assert root_stream.getvalue() == ""
        finally:
            logging.root.removeHandler(root_handler)

    def test_direct_instantiation_supports_file_only(self, log_path):
        with captured_console() as (out, err):
            log = Logifyx("t2_direct", output="file", log_file=log_path)
            log.info("direct")

        assert console_text(out, err) == ""
        assert "direct" in read_log(log_path)
        assert log.output == "file"


# --------------------------------------------------------------------------- #
# Test 3 — Both
# --------------------------------------------------------------------------- #


class TestBoth:

    def test_both_writes_to_terminal_and_file(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="both", log_file=log_path, color=False)
            log = get_logify_logger("t3_both")
            log.info("hello")

        assert "hello" in console_text(out, err)
        assert "hello" in read_log(log_path)

    def test_both_is_the_default(self, log_path):
        with captured_console() as (out, err):
            configure_logging(log_file=log_path, color=False)
            log = get_logify_logger("t3_default")
            log.info("defaulted")

        assert log.output == "both"
        assert "defaulted" in console_text(out, err)
        assert "defaulted" in read_log(log_path)


# --------------------------------------------------------------------------- #
# Test 4 — Reconfiguration
# --------------------------------------------------------------------------- #


class TestReconfiguration:

    def test_both_then_file_stops_terminal_output(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="both", log_file=log_path, color=False)
            log = get_logify_logger("t4_switch")
            log.info("first")

            first_console = console_text(out, err)

            configure_logging(output="file", log_file=log_path)
            log.info("second")

            final_console = console_text(out, err)

        assert "first" in first_console
        assert "second" not in final_console, "console handler survived the switch to file"

        content = read_log(log_path)
        assert "first" in content
        assert "second" in content

    def test_console_then_file_stops_terminal_output(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="console", color=False)
            log = get_logify_logger("t4_c2f")
            log.info("on console")

            configure_logging(output="file", log_file=log_path)
            log.info("on file")

        text = console_text(out, err)
        assert "on console" in text
        assert "on file" not in text
        assert "on file" in read_log(log_path)

    def test_file_then_both_restores_terminal_output(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="file", log_file=log_path, color=False)
            log = get_logify_logger("t4_f2b")
            log.info("quiet")

            configure_logging(output="both", log_file=log_path, color=False)
            log.info("loud")

        text = console_text(out, err)
        assert "quiet" not in text
        assert "loud" in text

    def test_set_output_switches_a_single_logger(self, log_path):
        with captured_console() as (out, err):
            log = Logifyx("t4_set", log_file=log_path, color=False)
            log.info("before")
            log.set_output("file")
            log.info("after")

        text = console_text(out, err)
        assert "before" in text
        assert "after" not in text
        assert "after" in read_log(log_path)

    def test_reload_keeps_a_single_handler_set(self, log_path):
        with captured_console():
            log = Logifyx("t4_reload", output="file", log_file=log_path)
            before = len(log.handlers)
            log.reload()
            log.reload()

        assert len(log.handlers) == before


# --------------------------------------------------------------------------- #
# Test 5 — Duplicate configuration
# --------------------------------------------------------------------------- #


class TestDuplicateConfiguration:

    def test_repeated_configure_logging_logs_once(self, log_path):
        with captured_console():
            configure_logging(output="file", log_file=log_path)
            configure_logging(output="file", log_file=log_path)
            configure_logging(output="file", log_file=log_path)
            log = get_logify_logger("t5_dupe")
            log.info("hello")

        assert read_log(log_path).count("hello") == 1

    def test_repeated_configure_logging_leaves_one_handler(self, log_path):
        with captured_console():
            setup_logify()
            log = get_logify_logger("t5_handlers")
            for _ in range(5):
                configure_logging(output="file", log_file=log_path)

        assert [role_of(h) for h in log.handlers] == [ROLE_FILE]

    def test_repeated_get_logify_logger_does_not_stack_handlers(self, log_path):
        with captured_console():
            configure_logging(output="file", log_file=log_path)
            first = get_logify_logger("t5_repeat")
            count = len(first.handlers)
            for _ in range(5):
                again = get_logify_logger("t5_repeat")
            again.info("only once")

        assert again is first
        assert len(again.handlers) == count
        assert read_log(log_path).count("only once") == 1

    def test_repeated_configure_calls_are_noops(self, log_path):
        with captured_console():
            log = Logifyx("t5_configure", output="file", log_file=log_path)
            count = len(log.handlers)
            log.configure(output="file", log_file=log_path)
            log.configure(output="file", log_file=log_path)
            log.info("single")

        assert len(log.handlers) == count
        assert read_log(log_path).count("single") == 1

    def test_configure_logging_before_and_after_logger_creation(self, log_path):
        """Configuring both before and after creation must not double up."""
        with captured_console():
            configure_logging(output="file", log_file=log_path)
            log = get_logify_logger("t5_order")
            configure_logging(output="file", log_file=log_path)
            log.info("exactly once")

        assert read_log(log_path).count("exactly once") == 1


# --------------------------------------------------------------------------- #
# Test 6 — Existing user handler
# --------------------------------------------------------------------------- #


class TestUserHandlerPreservation:

    def test_user_handler_survives_configure_logging(self, log_path):
        user_stream = io.StringIO()
        user_handler = logging.StreamHandler(user_stream)

        with captured_console():
            setup_logify()
            log = get_logify_logger("t6_user")
            log.addHandler(user_handler)

            configure_logging(output="file", log_file=log_path)

            assert user_handler in log.handlers
            log.info("seen by user handler")

        assert "seen by user handler" in user_stream.getvalue()
        assert user_handler.stream is user_stream, "user handler was reconfigured"

    def test_user_handler_survives_reload(self, log_path):
        user_handler = logging.StreamHandler(io.StringIO())

        with captured_console():
            log = Logifyx("t6_reload", output="file", log_file=log_path)
            log.addHandler(user_handler)
            log.reload()

        assert user_handler in log.handlers
        assert not user_handler.stream.closed, "reload closed a handler it does not own"

    def test_user_handler_survives_reset_logging(self, log_path):
        user_handler = logging.StreamHandler(io.StringIO())

        with captured_console():
            log = Logifyx("t6_reset", output="file", log_file=log_path)
            log.addHandler(user_handler)
            reset_logging()

        assert log.handlers == [user_handler]

    def test_user_formatter_is_not_overwritten(self, log_path):
        user_handler = logging.StreamHandler(io.StringIO())
        user_format = logging.Formatter("USER:%(message)s")
        user_handler.setFormatter(user_format)

        with captured_console():
            setup_logify()
            log = get_logify_logger("t6_fmt")
            log.addHandler(user_handler)
            configure_logging(output="file", log_file=log_path)
            log.info("mine")

        assert user_handler.formatter is user_format
        assert user_handler.stream.getvalue().strip() == "USER:mine"

    def test_logifyx_handlers_are_marked_and_user_handlers_are_not(self, log_path):
        user_handler = logging.StreamHandler(io.StringIO())

        with captured_console():
            log = Logifyx("t6_marks", output="both", log_file=log_path)
            log.addHandler(user_handler)

        assert not is_owned(user_handler)
        assert all(is_owned(h) for h in log.handlers if h is not user_handler)


# --------------------------------------------------------------------------- #
# Test 7 — Automatic directory creation
# --------------------------------------------------------------------------- #


class TestDirectoryCreation:

    def test_nested_directories_are_created(self, tmp_path):
        target = str(tmp_path / "logs" / "subdir" / "app.log")
        assert not os.path.exists(os.path.dirname(target))

        with captured_console():
            configure_logging(output="file", log_file=target)
            get_logify_logger("t7_nested").info("created")

        assert os.path.isdir(os.path.dirname(target))
        assert "created" in read_log(target)

    def test_deeply_nested_directories_are_created(self, tmp_path):
        target = str(tmp_path / "a" / "b" / "c" / "d" / "deep.log")

        with captured_console():
            configure_logging(output="file", log_file=target)
            get_logify_logger("t7_deep").info("deep")

        assert "deep" in read_log(target)

    def test_bare_filename_lands_in_log_dir(self, tmp_path):
        log_dir = str(tmp_path / "custom")

        with captured_console():
            configure_logging(output="file", log_dir=log_dir, log_file="named.log")
            get_logify_logger("t7_bare").info("in log_dir")

        assert "in log_dir" in read_log(os.path.join(log_dir, "named.log"))

    def test_log_file_directory_beats_log_dir(self, tmp_path):
        ignored = str(tmp_path / "ignored")
        used = str(tmp_path / "used" / "app.log")

        with captured_console():
            configure_logging(output="file", log_dir=ignored, log_file=used)
            get_logify_logger("t7_precedence").info("here")

        assert "here" in read_log(used)
        assert not os.path.exists(ignored)

    def test_default_filename_is_logger_name(self, tmp_path):
        log_dir = str(tmp_path / "named")

        with captured_console():
            configure_logging(output="file", log_dir=log_dir)
            get_logify_logger("t7_by_name").info("named after logger")

        assert "named after logger" in read_log(
            os.path.join(log_dir, "t7_by_name.log")
        )

    def test_resolve_log_target_forms(self):
        assert resolve_log_target("logs", "logs/app.log") == ("logs", "app.log")
        assert resolve_log_target("logs", "app.log") == ("logs", "app.log")
        assert resolve_log_target("logs", None) == ("logs", "app.log")
        assert resolve_log_target("/var/log/x", "api.log") == ("/var/log/x", "api.log")


# --------------------------------------------------------------------------- #
# Test 8 — Multiple threads
# --------------------------------------------------------------------------- #


class TestThreadSafety:

    def test_concurrent_writes_are_not_interleaved(self, log_path):
        thread_count, per_thread = 8, 40

        with captured_console() as (out, err):
            configure_logging(output="file", log_file=log_path, level="INFO", mask=False)
            log = get_logify_logger("t8_threads")

            def worker(tid):
                for i in range(per_thread):
                    log.info("thread-%d-msg-%03d", tid, i)

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            for handler in log.handlers:
                handler.flush()

        assert console_text(out, err) == ""

        lines = [ln for ln in read_log(log_path).splitlines() if ln.strip()]
        assert len(lines) == thread_count * per_thread

        # Every line must be a complete, well-formed record — a torn write would
        # show up as a line missing its prefix or carrying two messages.
        for line in lines:
            assert line.count(" | ") == 2, f"corrupted line: {line!r}"
            assert line.count("thread-") == 1, f"interleaved line: {line!r}"

        for tid in range(thread_count):
            for i in range(per_thread):
                assert f"thread-{tid}-msg-{i:03d}" in "\n".join(lines)


# --------------------------------------------------------------------------- #
# Test 9 — Exception logging
# --------------------------------------------------------------------------- #


class TestExceptionLogging:

    def test_exception_writes_traceback_to_file(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="file", log_file=log_path)
            log = get_logify_logger("t9_exc")
            try:
                raise ValueError("boom")
            except ValueError:
                log.exception("Something failed")

        assert console_text(out, err) == ""
        content = read_log(log_path)
        assert "Something failed" in content
        assert "Traceback (most recent call last):" in content
        assert "ValueError: boom" in content

    def test_exc_info_flag_writes_traceback(self, log_path):
        with captured_console():
            configure_logging(output="file", log_file=log_path)
            log = get_logify_logger("t9_flag")
            try:
                1 / 0
            except ZeroDivisionError:
                log.error("divide failed", exc_info=True)

        content = read_log(log_path)
        assert "ZeroDivisionError" in content
        assert "Traceback" in content

    def test_exception_traceback_in_json_mode(self, log_path):
        with captured_console():
            configure_logging(
                output="file", log_file=log_path, json_mode=True, color=False
            )
            log = get_logify_logger("t9_json_exc")
            try:
                raise KeyError("missing")
            except KeyError:
                log.exception("lookup failed")

        line = read_log(log_path).strip()
        record = json.loads(line)
        assert record["message"] == "lookup failed"
        assert "KeyError" in record["exception"]
        assert "Traceback" in record["exception"]


# --------------------------------------------------------------------------- #
# Test 10 — JSON logging
# --------------------------------------------------------------------------- #


class TestJsonOutput:

    def test_file_only_json_is_valid(self, log_path):
        with captured_console() as (out, err):
            configure_logging(
                output="file", log_file=log_path, json_mode=True, color=False
            )
            log = get_logify_logger("t10_json")
            log.info("Application started")
            log.error("Something failed")

        assert console_text(out, err) == ""

        lines = [ln for ln in read_log(log_path).splitlines() if ln.strip()]
        assert len(lines) == 2

        first = json.loads(lines[0])
        assert first["level"] == "INFO"
        assert first["logger"] == "t10_json"
        assert first["message"] == "Application started"
        assert "timestamp" in first

        assert json.loads(lines[1])["level"] == "ERROR"

    def test_json_mode_is_not_downgraded_to_plain_text(self, log_path):
        with captured_console():
            configure_logging(
                output="file", log_file=log_path, json_mode=True, color=False
            )
            get_logify_logger("t10_shape").info("structured")

        # Would raise if the file handler had fallen back to the text formatter.
        json.loads(read_log(log_path).strip())

    def test_json_extra_fields_reach_the_file(self, log_path):
        with captured_console():
            configure_logging(
                output="file", log_file=log_path, json_mode=True, color=False
            )
            log = get_logify_logger("t10_extra")
            log.info("with context", extra={"request_id": "abc123"})

        record = json.loads(read_log(log_path).strip())
        assert record["request_id"] == "abc123"


# --------------------------------------------------------------------------- #
# output="none"
# --------------------------------------------------------------------------- #


class TestNoneOutput:

    def test_none_emits_nothing_anywhere(self, log_path):
        with captured_console() as (out, err):
            configure_logging(output="none", log_file=log_path)
            log = get_logify_logger("t11_none")
            log.info("invisible")
            log.warning("also invisible")
            log.error("still invisible")

        assert console_text(out, err) == ""
        assert not os.path.exists(log_path)

    def test_none_suppresses_the_last_resort_handler(self):
        """
        With zero handlers, logging falls back to lastResort and prints
        WARNING+ to stderr. output="none" must not leak that way.
        """
        with captured_console() as (out, err):
            configure_logging(output="none")
            log = get_logify_logger("t11_lastresort")
            log.warning("must not appear")

        assert console_text(out, err) == ""
        assert log.handlers, "a NullHandler should absorb records"
        assert isinstance(log.handlers[0], logging.NullHandler)


# --------------------------------------------------------------------------- #
# Mode parsing and validation
# --------------------------------------------------------------------------- #


class TestOutputValidation:

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("console", "console"),
            ("CONSOLE", "console"),
            ("console_only", "console"),
            ("console-only", "console"),
            ("file", "file"),
            ("FILE", "file"),
            ("file_only", "file"),
            ("both", "both"),
            ("console_and_file", "both"),
            ("  Both  ", "both"),
            ("none", "none"),
            ("off", "none"),
            ("disabled", "none"),
        ],
    )
    def test_accepted_spellings(self, value, expected, log_path):
        with captured_console():
            log = Logifyx(f"t12_{expected}_{abs(hash(value))}", output=value, log_file=log_path)
        assert log.output == expected

    @pytest.mark.parametrize("bad", ["stdout", "terminal_only", "yes", ""])
    def test_invalid_mode_raises(self, bad):
        with pytest.raises(LogifyxConfigurationError):
            configure_logging(output=bad)

    def test_invalid_mode_is_also_a_value_error(self):
        """LogifyxConfigurationError subclasses ValueError for compatibility."""
        with pytest.raises(ValueError):
            configure_logging(output="nope")

    def test_non_string_mode_raises(self):
        with pytest.raises(LogifyxConfigurationError):
            configure_logging(output=True)

    def test_error_message_lists_valid_modes(self):
        with pytest.raises(LogifyxConfigurationError) as exc:
            configure_logging(output="nope")
        message = str(exc.value)
        for mode in ("console", "file", "both", "none"):
            assert mode in message


# --------------------------------------------------------------------------- #
# Environment / YAML configuration
# --------------------------------------------------------------------------- #


class TestEnvAndYamlConfiguration:

    def test_log_output_env_var(self, tmp_path, monkeypatch):
        target = str(tmp_path / "env.log")
        monkeypatch.setenv("LOG_OUTPUT", "file")
        monkeypatch.setenv("LOG_FILE", target)

        with captured_console() as (out, err):
            log = Logifyx("t13_env")
            log.info("from env")

        assert console_text(out, err) == ""
        assert "from env" in read_log(target)

    def test_logifyx_prefixed_env_vars(self, tmp_path, monkeypatch):
        target = str(tmp_path / "prefixed.log")
        monkeypatch.setenv("LOGIFYX_OUTPUT", "file")
        monkeypatch.setenv("LOGIFYX_LOG_FILE", target)
        monkeypatch.setenv("LOGIFYX_LEVEL", "WARNING")

        with captured_console() as (out, err):
            log = Logifyx("t13_prefixed")
            log.info("filtered out")
            log.warning("kept")

        assert console_text(out, err) == ""
        content = read_log(target)
        assert "filtered out" not in content
        assert "kept" in content

    def test_yaml_output_setting(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LOG_OUTPUT", raising=False)
        monkeypatch.delenv("LOG_FILE", raising=False)

        target = tmp_path / "yaml.log"
        yaml_file = tmp_path / "logifyx.yaml"
        yaml_file.write_text(
            f"LOG_OUTPUT: file\nLOG_FILE: {target.as_posix()}\n", encoding="utf-8"
        )

        with captured_console() as (out, err):
            log = Logifyx("t13_yaml", yaml_file=str(yaml_file))
            log.info("from yaml")

        assert console_text(out, err) == ""
        assert "from yaml" in read_log(str(target))

    def test_invalid_env_output_raises(self, monkeypatch):
        monkeypatch.setenv("LOG_OUTPUT", "nonsense")
        with pytest.raises(LogifyxConfigurationError):
            Logifyx("t13_bad_env")


# --------------------------------------------------------------------------- #
# Configuration priority
# --------------------------------------------------------------------------- #


class TestConfigurationPriority:

    def test_explicit_kwarg_beats_configure_logging(self, tmp_path):
        target = str(tmp_path / "priority.log")

        with captured_console() as (out, err):
            configure_logging(output="file", log_file=target, color=False)
            explicit = Logifyx("t14_explicit", output="console", color=False)
            explicit.info("stays on console")

        assert "stays on console" in console_text(out, err)

    def test_configure_logging_beats_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOG_OUTPUT", "console")
        target = str(tmp_path / "wins.log")

        with captured_console() as (out, err):
            configure_logging(output="file", log_file=target)
            log = get_logify_logger("t14_globals")
            log.info("explicit python config wins")

        assert console_text(out, err) == ""
        assert "explicit python config wins" in read_log(target)

    def test_global_config_is_readable(self, tmp_path):
        target = str(tmp_path / "readable.log")
        configure_logging(output="file", log_file=target, level="WARNING")

        globals_ = get_global_config()
        assert globals_["output"] == "file"
        assert globals_["log_file"] == target
        assert globals_["level"] == "WARNING"

    def test_reset_clears_global_config(self, tmp_path):
        configure_logging(output="file", log_file=str(tmp_path / "x.log"))
        assert get_global_config()
        reset_logging()
        assert get_global_config() == {}

    def test_reset_kwarg_discards_previous_defaults(self, tmp_path):
        configure_logging(output="file", log_file=str(tmp_path / "a.log"), level="ERROR")
        configure_logging(output="console", reset=True)

        globals_ = get_global_config()
        assert globals_ == {"output": "console"}


# --------------------------------------------------------------------------- #
# Third-party loggers must keep working
# --------------------------------------------------------------------------- #


class TestThirdPartyLoggersUnaffected:

    def test_stdlib_loggers_keep_their_handlers(self, log_path):
        urllib3 = logging.getLogger("urllib3")
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        urllib3.addHandler(handler)
        urllib3.setLevel(logging.INFO)

        try:
            with captured_console():
                configure_logging(output="file", log_file=log_path)
                urllib3.info("third party still logging")

            assert handler in urllib3.handlers
            assert "third party still logging" in captured.getvalue()
        finally:
            urllib3.removeHandler(handler)

    def test_root_logger_gets_no_logifyx_handlers(self, log_path):
        before = list(logging.root.handlers)

        with captured_console():
            configure_logging(output="file", log_file=log_path)
            get_logify_logger("t15_root").info("scoped")

        assert logging.root.handlers == before
        assert not any(is_owned(h) for h in logging.root.handlers)

    def test_root_level_is_untouched(self, log_path):
        before = logging.root.level

        with captured_console():
            configure_logging(output="file", log_file=log_path, level="ERROR")

        assert logging.root.level == before


# --------------------------------------------------------------------------- #
# Error handling
# --------------------------------------------------------------------------- #


class TestErrorHandling:

    def test_directory_collision_raises_file_error(self, tmp_path):
        blocker = tmp_path / "blocked"
        blocker.write_text("i am a file, not a directory", encoding="utf-8")
        target = str(blocker / "app.log")

        with pytest.raises(LogifyxFileError) as exc:
            configure_logging(output="file", log_file=target)

        assert "blocked" in str(exc.value)

    def test_file_error_is_also_a_runtime_error(self, tmp_path):
        blocker = tmp_path / "blocker2"
        blocker.write_text("x", encoding="utf-8")

        with pytest.raises(RuntimeError):
            configure_logging(output="file", log_file=str(blocker / "app.log"))

    @pytest.mark.parametrize("bad", [os.sep, "/"])
    def test_log_file_without_a_name_raises(self, bad):
        with pytest.raises(LogifyxConfigurationError):
            resolve_log_target("logs", bad)

    def test_bad_types_still_raise_type_error(self):
        with pytest.raises(TypeError):
            configure_logging(log_file=123)
        with pytest.raises(TypeError):
            configure_logging(max_bytes="big")
        with pytest.raises(TypeError):
            configure_logging(color="yes")

    def test_config_errors_do_not_log_through_broken_handler(self, tmp_path):
        """A failed setup must raise, not silently route through the logger."""
        blocker = tmp_path / "blocker3"
        blocker.write_text("x", encoding="utf-8")

        with captured_console() as (out, err):
            with pytest.raises(LogifyxFileError):
                configure_logging(output="file", log_file=str(blocker / "app.log"))

        assert console_text(out, err) == ""


# --------------------------------------------------------------------------- #
# Backward compatibility
# --------------------------------------------------------------------------- #


class TestBackwardCompatibility:

    def test_zero_config_still_writes_to_console_and_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with captured_console() as (out, err):
            log = Logifyx("t16_zero", color=False)
            log.info("default behaviour")

        assert "default behaviour" in console_text(out, err)
        assert "default behaviour" in read_log(
            str(tmp_path / "logs" / "t16_zero.log")
        )

    def test_get_logify_logger_without_configure_logging(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_logify()

        with captured_console() as (out, err):
            log = get_logify_logger("t16_classic", color=False)
            log.info("classic path")

        assert "classic path" in console_text(out, err)

    def test_log_dir_still_works(self, tmp_path):
        log_dir = str(tmp_path / "legacy")

        with captured_console():
            log = Logifyx("t16_dir", log_dir=log_dir, color=False)
            log.info("legacy dir")

        assert "legacy dir" in read_log(os.path.join(log_dir, "t16_dir.log"))

    def test_rotation_settings_apply_in_file_only_mode(self, tmp_path):
        target = str(tmp_path / "rotate.log")

        with captured_console():
            log = Logifyx(
                "t16_rotate",
                output="file",
                log_file=target,
                max_bytes=1024,
                backup_count=2,
            )

        file_handler = log.handlers[0]
        assert file_handler.maxBytes == 1024
        assert file_handler.backupCount == 2

    def test_rotation_actually_rotates_in_file_only_mode(self, tmp_path):
        target = str(tmp_path / "rot.log")

        with captured_console() as (out, err):
            log = Logifyx(
                "t16_rotates",
                output="file",
                log_file=target,
                max_bytes=1024,
                backup_count=3,
                mask=False,
            )
            for i in range(200):
                log.info("padding message %03d %s", i, "x" * 60)
            for handler in log.handlers:
                handler.flush()

        assert console_text(out, err) == ""
        rotated = list(tmp_path.glob("rot.log*"))
        assert len(rotated) > 1, "rotation did not produce backup files"

    def test_masking_still_applies_in_file_only_mode(self, log_path):
        with captured_console():
            configure_logging(output="file", log_file=log_path, mask=True)
            get_logify_logger("t16_mask").info("login password=hunter2")

        content = read_log(log_path)
        assert "hunter2" not in content
        assert "****" in content

    def test_file_kwarg_is_gone(self, log_path):
        """`file` was removed in 2.0 in favour of log_file."""
        with pytest.raises(TypeError):
            Logifyx("t16_removed", file="app.log")
        with pytest.raises(TypeError):
            configure_logging(file="app.log")
