"""
Enhanced JSON Schema Validator Package

A modern, object-oriented JSON schema validator with a focus on
maintainability, clarity, and robust error reporting.
"""

from .api import ErrorCode, JsonValidator, ValidationError, ValidationResult
from .schema_compiler import SchemaCompiler
from .validator import Validator
from .utils import JsonPointer
from .version import __version__

__all__ = [
    "ErrorCode",
    "JsonPointer",
    "JsonValidator",
    "SchemaCompiler",
    "ValidationError",
    "ValidationResult",
    "Validator"
]
