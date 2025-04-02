#!/usr/bin/env python3
"""
Enhanced JSON Schema Validator

This script validates JSON data against a JSON Schema using
the enhanced validator implementation.

Usage:
    python enhanced_validator_main.py <data_file> <schema_file> [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List

from .api import JsonValidator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger("enhanced_validator")


def load_json(filepath: Path) -> Dict[str, Any]:
    """
    Load JSON from a file.

    Args:
        filepath: Path to the JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """

    if filepath and (isinstance(filepath, str) and len(filepath) > 0) and not Path(filepath).exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON in {filepath}: {e}")
            raise


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate JSON data against a JSON Schema."
    )
    parser.add_argument(
        "data_file",
        type=str,
        help="Path to the JSON data file to validate"
    )
    parser.add_argument(
        "schema_file",
        type=str,
        help="Path to the JSON schema file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for the script."""
    args = parse_args()

    data_file_path = Path(args.data_file)
    schema_file_path = Path(args.schema_file)

    # Load JSON files
    try:
        data = load_json(data_file_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(str(e))
        return 1

    try:
        schema = load_json(schema_file_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Schema error: {str(e)}")
        return 1

    # Create validator
    validator = JsonValidator(verbose=args.verbose)

    # Validate data
    result = validator.validate(data, schema)

    # Report results
    if result.valid:
        logger.info("Validation successful!")
        return 0
    else:
        logger.error("Validation failed:")
        for error in result.errors:
            logger.error(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
