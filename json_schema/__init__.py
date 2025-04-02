#!/usr/bin/env python3
"""
JSON Configuration Validator

This package validates JSON configuration files against a provided JSON schema,
with additional custom validation rules for project configuration files.
"""

import logging
from typing import Dict, List, Optional, Union, Any

from .schema_validator import JsonSchemaValidator
from .config_validator import ConfigValidator
from .version import __version__

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger("json_schema")

# Export public classes and functions
__all__ = ["JsonSchemaValidator", "ConfigValidator"]
