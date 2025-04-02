#!/usr/bin/env python3
"""
JSON Configuration Validator

This script validates JSON configuration files against a provided JSON schema,
with additional custom validation rules for project configuration files.

Usage:
    python json_schema.py <data_file> <schema_file> [--check-files] [--verbose]
"""

import sys

from json_schema.cli import main

if __name__ == "__main__":
    sys.exit(main())
