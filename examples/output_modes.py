"""
Output Modes Demo - where Logifyx sends your logs.

Run it:

    python examples/output_modes.py

Watch the terminal: only the console and both sections print anything. The
file-only section writes to demo_logs/file_only.log and stays completely silent.
"""

from pathlib import Path

from logifyx import configure_logging, get_logify_logger, reset_logging

LOG_DIR = Path(__file__).parent / "demo_logs"


def show(path):
    print(f"\n   --- {path.name} ---")
    for line in path.read_text(encoding="utf-8").splitlines():
        print(f"   {line}")


# ===========================================================================
# 1. File only - the terminal stays silent
# ===========================================================================
print("\n[1] output='file' - nothing below this line until section 2\n")

file_only = LOG_DIR / "file_only.log"
configure_logging(level="INFO", output="file", log_file=str(file_only))

log = get_logify_logger("my_app")
log.info("Application started")
log.error("Something failed")

# Nothing was printed. The records are in the file:
show(file_only)


# ===========================================================================
# 2. Console only - no log file is opened at all
# ===========================================================================
print("\n[2] output='console' - prints below, writes no file\n")

configure_logging(output="console", color=True)

console_log = get_logify_logger("console_app")
console_log.info("Only the terminal sees this")


# ===========================================================================
# 3. Both - the default, and how Logifyx has always behaved
# ===========================================================================
print("\n[3] output='both' - prints AND writes\n")

both_file = LOG_DIR / "both.log"
configure_logging(output="both", log_file=str(both_file), color=True)

both_log = get_logify_logger("both_app")
both_log.info("This goes to the terminal and the file")

show(both_file)


# ===========================================================================
# 4. Switching at runtime - the console handler is removed, not muted
# ===========================================================================
print("\n[4] switching both -> file at runtime\n")

switch_file = LOG_DIR / "switch.log"
configure_logging(output="both", log_file=str(switch_file), color=False)
switch_log = get_logify_logger("switch_app")
switch_log.info("first - terminal + file")

configure_logging(output="file", log_file=str(switch_file))
switch_log.info("second - file only, nothing printed")

show(switch_file)


# ===========================================================================
# 5. Calling configure_logging repeatedly never duplicates handlers
# ===========================================================================
print("\n[5] three identical configure_logging calls\n")

once_file = LOG_DIR / "once.log"
for _ in range(3):
    configure_logging(output="file", log_file=str(once_file))

once_log = get_logify_logger("once_app")
once_log.info("logged exactly once")

show(once_file)
print(f"\n   occurrences of 'logged exactly once': "
      f"{once_file.read_text(encoding='utf-8').count('logged exactly once')}")


# ===========================================================================
# 6. JSON stays JSON in file-only mode
# ===========================================================================
print("\n[6] output='file' with json_mode=True\n")

json_file = LOG_DIR / "structured.log"
configure_logging(output="file", log_file=str(json_file), json_mode=True, color=False)

json_log = get_logify_logger("json_app")
json_log.info("Application started", extra={"request_id": "req-abc123"})

show(json_file)

reset_logging()
print(f"\nDone. Log files are in {LOG_DIR}\n")
