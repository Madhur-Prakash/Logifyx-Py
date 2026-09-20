import argparse
import json
import os
import sys
from pathlib import Path
from .config import load_config
from .output import VALID_OUTPUTS, normalize_output, resolve_log_target


def _use_utf8_stdout():
    """
    Let the banner emoji through on consoles that default to a legacy codepage.

    Windows terminals often use cp1252, where printing the section headers
    raises UnicodeEncodeError and takes the whole command down.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass


def main():

    _use_utf8_stdout()

    parser = argparse.ArgumentParser(
        prog="logifyx",
        description="Logifyx CLI Tool"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Show resolved Logifyx configuration (from logifyx.yaml + env)"
    )

    parser.add_argument(
        "--config-dir",
        help="Load .env and logifyx.yaml from a specific directory"
    )

    parser.add_argument(
        "--env-file",
        help="Load environment variables from a specific .env file"
    )

    parser.add_argument(
        "--yaml-file",
        help="Load Logifyx YAML configuration from a specific file"
    )

    parser.add_argument(
        "--output",
        choices=list(VALID_OUTPUTS),
        help="Preview the resolved config with this output mode applied: "
             "console, file (no terminal output), both, or none"
    )

    parser.add_argument(
        "--log-file",
        help="Preview the resolved config with this log file path applied"
    )

    parser.add_argument(
        "--level",
        help="Preview the resolved config with this log level applied"
    )

    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Show runtime config (from last Logifyx instance)"
    )

    args = parser.parse_args()

    # The override flags are only meaningful against a resolved config, so they
    # imply --config rather than requiring the user to pass both.
    overrides = {
        "output": normalize_output(args.output, source="--output") if args.output else None,
        "log_file": args.log_file,
        "log_dir": args.log_dir,
        "level": args.level.upper() if args.level else None,
    }
    has_overrides = any(v is not None for v in overrides.values())

    # If --config is passed (show env/yaml/defaults)
    if args.config or has_overrides:
        config_dir = args.config_dir or os.getcwd()
        config = load_config(config_dir=config_dir, env_file=args.env_file, yaml_file=args.yaml_file)
        resolved_dir = Path(config_dir).expanduser().resolve()
        yaml_path = Path(args.yaml_file).expanduser().resolve() if args.yaml_file else resolved_dir / "logifyx.yaml"
        env_path = Path(args.env_file).expanduser().resolve() if args.env_file else resolved_dir / ".env"

        yaml_status = "found" if yaml_path.is_file() else "not found"
        env_status = "found" if env_path.is_file() else "not found"

        for key, value in overrides.items():
            if value is not None:
                config[key] = value

        print(f"\n📦 Logifyx Configuration (config dir: {resolved_dir}):\n")
        print(f".env: {env_status} ({env_path})")
        print(f"logifyx.yaml: {yaml_status} ({yaml_path})\n")
        if has_overrides:
            applied = ", ".join(f"{k}={v!r}" for k, v in overrides.items() if v is not None)
            print(f"CLI overrides applied: {applied}\n")
        print(json.dumps(config, indent=4))

        _print_destinations(config)
        return

    parser.print_help()


def _print_destinations(config):
    """Spell out where log records would actually land under this config."""
    output = config.get("output", "both")
    log_dir, filename = resolve_log_target(config.get("log_dir"), config.get("log_file"))
    path = os.path.join(log_dir, filename) if log_dir else filename

    print("\n🎯 Destinations:\n")
    if output in ("console", "both"):
        print("   console: enabled")
    else:
        print("   console: disabled — nothing is written to stdout/stderr")

    if output in ("file", "both"):
        print(f"   file:    {Path(path).resolve()}")
    else:
        print("   file:    disabled — no log file is opened")

    if config.get("remote_url"):
        print(f"   remote:  {config['remote_url']}")
    if config.get("kafka_servers"):
        print(f"   kafka:   {config['kafka_servers']} (topic: {config.get('kafka_topic')})")
    print()
