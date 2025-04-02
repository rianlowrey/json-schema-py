"""
Public API for the Enhanced JSON Schema Validator.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Tuple


class ErrorCode(Enum):
    """Enumeration of validation error codes."""
    TYPE_ERROR = auto()
    REQUIRED_PROPERTY_MISSING = auto()
    ADDITIONAL_PROPERTY_NOT_ALLOWED = auto()
    STRING_TOO_SHORT = auto()
    STRING_TOO_LONG = auto()
    PATTERN_MISMATCH = auto()
    NUMBER_TOO_SMALL = auto()
    NUMBER_TOO_LARGE = auto()
    NUMBER_NOT_MULTIPLE = auto()
    ARRAY_TOO_SHORT = auto()
    ARRAY_TOO_LONG = auto()
    ARRAY_ITEMS_NOT_UNIQUE = auto()
    ARRAY_ITEM_INVALID = auto()
    OBJECT_TOO_FEW_PROPERTIES = auto()
    OBJECT_TOO_MANY_PROPERTIES = auto()
    PROPERTY_NAME_INVALID = auto()
    DEPENDENCY_MISSING = auto()
    ENUM_MISMATCH = auto()
    CONST_MISMATCH = auto()
    NOT_SCHEMA_MATCHED = auto()
    ONE_OF_NO_MATCH = auto()
    ONE_OF_MULTIPLE_MATCHES = auto()
    ANY_OF_NO_MATCH = auto()
    ALL_OF_FAILED = auto()
    REFERENCE_RESOLUTION_FAILED = auto()
    SCHEMA_INVALID = auto()
    UNSUPPORTED_FEATURE = auto()
    CUSTOM_ERROR = auto()


@dataclass
class ValidationError:
    """
    Represents a validation error with structured information.

    Attributes:
        code: The error code identifying the type of error
        path: JSON Pointer to the value that failed validation
        message: Human-readable error message
        schema_path: JSON Pointer to the schema location that triggered the error
        value: The value that failed validation
        constraint: The constraint that was violated
    """
    code: ErrorCode
    path: str
    message: str
    schema_path: Optional[str] = None
    value: Any = None
    constraint: Any = None

    def __str__(self) -> str:
        return f"Error at '{self.path}': {self.message}"


@dataclass
class ValidationResult:
    """
    Result of schema validation.

    Attributes:
        valid: Whether the validation was successful
        errors: List of validation errors (if any)
    """
    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


class JsonValidator:
    """
    Main entrypoint class for JSON schema validation.

    This class provides a simple API for validating JSON data
    against a JSON Schema.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize a new JSON validator.

        Args:
            verbose: Whether to include additional details in error messages
        """
        from .schema_compiler import SchemaCompiler
        from .validator import Validator

        self.verbose = verbose
        self.schema_compiler = SchemaCompiler()
        self.validator = Validator(verbose=verbose)

    def validate(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """
        Validate data against a JSON schema.

        Args:
            data: The data to validate
            schema: The JSON schema to validate against

        Returns:
            ValidationResult containing validation status and any errors
        """
        # Compile the schema into a constraint tree
        compiled_schema = self.schema_compiler.compile(schema)

        # Validate the data against the compiled schema
        return self.validator.validate(data, compiled_schema)
