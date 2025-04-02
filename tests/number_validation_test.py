#!/usr/bin/env python3
"""
Tests for number-specific validation features.
"""
import pytest
from pathlib import Path

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_number_constraints():
    """Test number-specific constraints in the schema validator."""
    validator = JsonSchemaValidator()

    # Test minimum and maximum
    schema = {
        "type": "number",
        "minimum": 10,
        "maximum": 100
    }

    # Valid - within range
    assert len(validator.validate(42, schema)) == 0

    # Invalid - below minimum
    errors = validator.validate(5, schema)
    assert len(errors) > 0
    assert any("minimum is 10" in error for error in errors)

    # Invalid - above maximum
    errors = validator.validate(150, schema)
    assert len(errors) > 0
    assert any("maximum is 100" in error for error in errors)

    # Test multipleOf
    multiple_schema = {
        "type": "integer",
        "multipleOf": 5
    }

    # Valid - multiple of 5
    assert len(validator.validate(25, multiple_schema)) == 0

    # Invalid - not a multiple of 5
    errors = validator.validate(27, multiple_schema)
    assert len(errors) > 0
    assert any("not a multiple of 5" in error for error in errors)

    # Test standalone constraints (no type specified)
    standalone_schema = {
        "minimum": 10,
        "multipleOf": 5
    }

    # Number should be validated even without type
    assert len(validator.validate(15, standalone_schema)) == 0
    errors = validator.validate(7, standalone_schema)
    assert len(errors) > 0
    assert any("minimum is 10" in error for error in errors)

    # Boolean should not be treated as a number in standalone constraints
    errors = validator.validate(True, standalone_schema)
    assert len(errors) == 0  # Should not trigger number validations

    # String should not trigger number validations
    errors = validator.validate("abc", standalone_schema)
    assert len(errors) == 1
    assert any("Expected integer, got str" in error for error in errors)


def test_number_type_edge_cases():
    """Test edge cases for number and integer types."""
    validator = JsonSchemaValidator()

    # Test number type with various values
    number_schema = {"type": "number"}

    # Valid numbers
    assert len(validator.validate(0, number_schema)) == 0
    assert len(validator.validate(-1, number_schema)) == 0
    assert len(validator.validate(3.14, number_schema)) == 0
    assert len(validator.validate(1e10, number_schema)) == 0

    # Invalid numbers
    assert len(validator.validate("123", number_schema)
               ) > 0  # String, not number
    assert len(validator.validate(True, number_schema)
               ) > 0   # Boolean, not number
    # Array, not number
    assert len(validator.validate([1, 2, 3], number_schema)) > 0

    # Test integer type with various values
    integer_schema = {"type": "integer"}

    # Valid integers
    assert len(validator.validate(0, integer_schema)) == 0
    assert len(validator.validate(-10, integer_schema)) == 0
    assert len(validator.validate(42, integer_schema)) == 0

    # Invalid integers
    assert len(validator.validate(3.14, integer_schema)
               ) > 0  # Float, not integer
    assert len(validator.validate("42", integer_schema)
               ) > 0  # String, not integer
    assert len(validator.validate(True, integer_schema)
               ) > 0  # Boolean, not integer


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
