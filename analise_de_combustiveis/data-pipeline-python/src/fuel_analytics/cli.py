from __future__ import annotations

import argparse
import json

from fuel_analytics.flows import bootstrap_flow, pipeline_flow
from fuel_analytics.logging import configure_logging, logger


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Fuel analytics pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap")
    subparsers.add_parser("run")

    args = parser.parse_args()
    logger.info("CLI command received: {}", args.command)
    if args.command == "bootstrap":
        result = bootstrap_flow()
        logger.info("Bootstrap command finished with {} rows", result)
        print(result)
        return
    result = pipeline_flow()
    logger.info("Run command finished")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
