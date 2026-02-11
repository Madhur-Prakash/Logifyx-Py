import argparse
import json
import os
from .config import load_config, RUNTIME_CONFIG_FILE, CONFIG_FILE


def main():

    parser = argparse.ArgumentParser(
        prog="logify",
        description="Logify CLI Tool"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Show resolved Logify configuration (from logify.yaml + env)"
    )

    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Show runtime config (from last Logify instance)"
    )

    args = parser.parse_args()

    # If --config is passed (show env/yaml/defaults)
    if args.config:
        config = load_config()
        yaml_status = "found" if os.path.exists(CONFIG_FILE) else "not found"
        print(f"\n📦 Logify Configuration (logify.yaml: {yaml_status}):\n")
        print(json.dumps(config, indent=4))
        return

    # If --runtime is passed (show actual runtime config from last run)
    if args.runtime:
        if os.path.exists(RUNTIME_CONFIG_FILE):
            with open(RUNTIME_CONFIG_FILE) as f:
                runtime_config = json.load(f)
            print("\n🚀 Logify Runtime Configuration (last instance):\n")
            print(json.dumps(runtime_config, indent=4))
        else:
            print("\n⚠️  No runtime config found. Run your app with Logify first.")
        return

    parser.print_help()
