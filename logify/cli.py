import argparse
import json

from .config import load_config


def main():

    parser = argparse.ArgumentParser(
        prog="logify",
        description="Logify CLI Tool"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Show resolved Logify configuration"
    )

    parser.add_argument(
        "--config-file",
        type=str,
        help="Path to YAML config file"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config_file)

    # If --config is passed
    if args.config:
        print("\n📦 Logify Configuration:\n")
        print(json.dumps(config, indent=4))
