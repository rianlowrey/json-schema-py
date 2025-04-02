#!/usr/bin/env python3
"""
Command-line interface for the JSON validator.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .config_validator import ConfigValidator
from .version import __version__

logger = logging.getLogger("json_schema")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate JSON configuration files against a schema."
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
        "--check-files",
        action="store_true",
        help="Verify that referenced files exist on disk"
    )
    parser.add_argument(
        "--cmake-var",
        action="append",
        metavar="NAME=VALUE",
        help="Define a CMake variable for path expansion (can be used multiple times)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    return parser.parse_args(args)


def main() -> int:
    """Main entry point for the script."""
    args = parse_args()

    # Set base directory to the data file's directory for relative file path checking
    data_file_path = Path(args.data_file)
    base_dir = data_file_path.parent if data_file_path.is_file() else Path.cwd()

    # Parse any CMake variables provided
    cmake_vars = {}
    if args.cmake_var:
        for var_def in args.cmake_var:
            if "=" in var_def:
                name, value = var_def.split("=", 1)
                cmake_vars[name] = value

    # Create the validator
    validator = ConfigValidator(
        check_file_existence=args.check_files,
        verbose=args.verbose,
        base_dir=base_dir,
        cmake_vars=cmake_vars
    )

    # Perform validation
    errors = validator.validate(args.data_file, args.schema_file)

    # Report results
    if errors:
        logger.error("Validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1

    logger.info("Validation successful!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
