#!/usr/bin/env python3
"""
Test runner for the JSON validator.

This script runs all tests for the JSON validator or a specific subset.
"""

import argparse
import pytest
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Run tests for the JSON validator")
    parser.add_argument(
        "--category", "-c",
        choices=["basic", "string", "number", "object", "array", "combinations", "integration", "all"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Run a specific test file"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Determine which tests to run
    test_dir = Path(__file__).parent.joinpath("tests")
    pytest_args = ["-xvs"] if args.verbose else []
    
    if args.file:
        # Run a specific test file
        test_file = test_dir / args.file
        if not test_file.exists():
            print(f"Test file not found: {test_file}")
            return 1
        pytest_args.append(str(test_file))
    else:
        # Run tests by category
        if args.category == "basic" or args.category == "all":
            pytest_args.append(str(test_dir / "basic_validation_test.py"))
        if args.category == "string" or args.category == "all":
            pytest_args.append(str(test_dir / "string_validation_test.py"))
        if args.category == "number" or args.category == "all":
            pytest_args.append(str(test_dir / "number_validation_test.py"))
        if args.category == "object" or args.category == "all":
            pytest_args.append(str(test_dir / "object_validation_test.py"))
        if args.category == "array" or args.category == "all":
            pytest_args.append(str(test_dir / "array_validation_test.py"))
        if args.category == "combinations" or args.category == "all":
            pytest_args.append(str(test_dir / "schema_validation_test.py"))
        if args.category == "integration" or args.category == "all":
            pytest_args.append(str(test_dir / "integration_test.py"))

    print(f"Running tests: {' '.join(pytest_args)}")

    import sys,os
    sys.path.append(os.pardir)

    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(main())