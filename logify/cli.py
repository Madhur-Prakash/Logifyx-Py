import argparse
import json
import os
from .config import load_config, CONFIG_FILE


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
        "--runtime",
        action="store_true",
        help="Show runtime config (from last Logifyx instance)"
    )

    args = parser.parse_args()

    # If --config is passed (show env/yaml/defaults)
    if args.config:
        config = load_config()
        yaml_status = "found" if os.path.exists(CONFIG_FILE) else "not found"
        print(f"\n📦 Logifyx Configuration (logifyx.yaml: {yaml_status}):\n")
        print(json.dumps(config, indent=4))
        return

    parser.print_help()
