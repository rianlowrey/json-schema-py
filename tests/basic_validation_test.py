#!/usr/bin/env python3
"""
Tests for basic validation features like types, enums, and const values.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_schema_validator_basic():
    """Test basic schema validation."""
    validator = JsonSchemaValidator()

    # Valid case
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    data = {"name": "test"}
    errors = validator.validate(data, schema)
    assert len(errors) == 0

    # Invalid type
    data = {"name": 123}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Expected string" in error for error in errors)

    # Test enum validation
    schema = {"type": "string", "enum": ["red", "green", "blue"]}
    assert len(validator.validate("red", schema)) == 0
    assert len(validator.validate("yellow", schema)) > 0


def test_type_validation():
    """Test type validation edge cases in the schema validator."""
    validator = JsonSchemaValidator()

    # Test boolean vs number/integer distinction
    schema_number = {"type": "number"}
    schema_integer = {"type": "integer"}
    schema_boolean = {"type": "boolean"}

    # Boolean should not be valid as a number
    assert len(validator.validate(True, schema_number)) > 0
    # Boolean should not be valid as an integer
    assert len(validator.validate(True, schema_integer)) > 0
    # Boolean should be valid as a boolean
    assert len(validator.validate(True, schema_boolean)) == 0

    # Integer should be valid as a number
    assert len(validator.validate(42, schema_number)) == 0
    # Integer should be valid as an integer
    assert len(validator.validate(42, schema_integer)) == 0
    # Integer should not be valid as a boolean
    assert len(validator.validate(42, schema_boolean)) > 0

    # Float should be valid as a number
    assert len(validator.validate(3.14, schema_number)) == 0
    # Float should not be valid as an integer
    assert len(validator.validate(3.14, schema_integer)) > 0
    # Float should not be valid as a boolean
    assert len(validator.validate(3.14, schema_boolean)) > 0


def test_const_validation():
    """Test const validation in the schema validator."""
    validator = JsonSchemaValidator()

    schema = {"const": 42}

    # Valid - matches const value
    assert len(validator.validate(42, schema)) == 0

    # Invalid - doesn't match const value
    errors = validator.validate("not 42", schema)
    assert len(errors) > 0
    assert any("Expected constant value" in error for error in errors)


def test_reference_resolution():
    """Test reference resolution in the schema validator."""
    validator = JsonSchemaValidator()

    schema = {
        "definitions": {
            "positiveInteger": {
                "type": "integer",
                "minimum": 1
            }
        },
        "type": "object",
        "properties": {
            "count": {"$ref": "#/definitions/positiveInteger"}
        }
    }

    # Valid data
    data = {"count": 5}
    errors = validator.validate(data, schema)
    assert len(errors) == 0

    # Invalid data (negative number)
    data = {"count": -5}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("minimum is 1" in error for error in errors)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
