import argparse
import json
import os
from pathlib import Path

from .config import load_config


def main():

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
        "--runtime",
        action="store_true",
        help="Show runtime config (from last Logifyx instance)"
    )

    args = parser.parse_args()

    # If --config is passed (show env/yaml/defaults)
    if args.config:
        config_dir = args.config_dir or os.getcwd()
        config = load_config(config_dir=config_dir, env_file=args.env_file, yaml_file=args.yaml_file)
        resolved_dir = Path(config_dir).expanduser().resolve()
        yaml_path = Path(args.yaml_file).expanduser().resolve() if args.yaml_file else resolved_dir / "logifyx.yaml"
        env_path = Path(args.env_file).expanduser().resolve() if args.env_file else resolved_dir / ".env"

        yaml_status = "found" if yaml_path.is_file() else "not found"
        env_status = "found" if env_path.is_file() else "not found"

        print(f"\n📦 Logifyx Configuration (config dir: {resolved_dir}):\n")
        print(f".env: {env_status} ({env_path})")
        print(f"logifyx.yaml: {yaml_status} ({yaml_path})\n")
        print(json.dumps(config, indent=4))
        return

    parser.print_help()
