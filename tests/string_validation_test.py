#!/usr/bin/env python3
"""
Tests for string-specific validation features.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_string_constraints():
    """Test string-specific constraints in the schema validator."""
    validator = JsonSchemaValidator()

    # Test minLength and maxLength
    schema = {
        "type": "string",
        "minLength": 3,
        "maxLength": 10
    }

    # Valid - within length constraints
    assert len(validator.validate("test", schema)) == 0

    # Invalid - too short
    errors = validator.validate("ab", schema)
    assert len(errors) > 0
    assert any("minimum is 3" in error for error in errors)

    # Invalid - too long
    errors = validator.validate("this_is_too_long", schema)
    assert len(errors) > 0
    assert any("maximum is 10" in error for error in errors)

    # Test pattern
    pattern_schema = {
        "type": "string",
        "pattern": "^[a-z]+$"
    }

    # Valid - matches pattern
    assert len(validator.validate("abcdef", pattern_schema)) == 0

    # Invalid - doesn't match pattern
    errors = validator.validate("123abc", pattern_schema)
    assert len(errors) > 0
    assert any("does not match pattern" in error for error in errors)

    # Test standalone constraints (no type specified)
    standalone_schema = {
        "minLength": 3,
        "pattern": "^[A-Z]"
    }

    # String should be validated even without type
    assert len(validator.validate("Abc", standalone_schema)) == 0
    errors = validator.validate("ab", standalone_schema)
    assert len(errors) > 0
    assert any("minimum is 3" in error for error in errors)

    # Non-string value should not trigger string validations
    errors = validator.validate(123, standalone_schema)
    assert len(errors) == 1
    assert any("Expected string, got int" in error for error in errors)


def test_pattern_validation():
    """Test pattern-based validation in various contexts."""
    validator = JsonSchemaValidator()

    # Basic pattern validation
    schema = {"pattern": "^[A-Z][a-z]+$"}

    # Valid - matches pattern
    assert len(validator.validate("Hello", schema)) == 0

    # Invalid - doesn't match pattern
    # Doesn't start with uppercase
    errors = validator.validate("hello", schema)
    assert len(errors) > 0
    assert any("does not match pattern" in error for error in errors)

    # Not lowercase after first letter
    errors = validator.validate("HELLO", schema)
    assert len(errors) > 0

    # Pattern in property validation
    schema = {
        "type": "object",
        "properties": {
            "email": {"pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
            "phone": {"pattern": "^\\+?[0-9\\s()\\-]{8,20}$"}
        }
    }

    # Valid data
    data = {
        "email": "user@example.com",
        "phone": "+1 (555) 123-4567"
    }
    assert len(validator.validate(data, schema)) == 0

    # Invalid data
    data = {
        "email": "invalid-email",
        "phone": "555"
    }
    errors = validator.validate(data, schema)
    assert len(errors) >= 2

    # Non-string values with pattern
    schema = {"type": "string", "pattern": "^\\d+$"}
    errors = validator.validate(42, schema)
    assert len(errors) > 0
    assert any("Expected string, got int" in error for error in errors)

    # Pattern in patternProperties
    schema = {
        "type": "object",
        "patternProperties": {
            "^user_[0-9]+$": {"type": "object"},
            "^data_[a-z]+$": {"type": "array"}
        },
        "additionalProperties": False
    }

    # Valid - all properties match patterns
    data = {
        "user_123": {"name": "John"},
        "user_456": {"name": "Jane"},
        "data_items": [1, 2, 3]
    }
    assert len(validator.validate(data, schema)) == 0

    # Invalid - some properties don't match patterns
    data = {
        "user123": {"name": "John"},  # Missing underscore
        "data-items": [1, 2, 3]       # Has hyphen instead of underscore
    }
    errors = validator.validate(data, schema)
    assert len(errors) >= 2
    assert any(
        "Additional property 'user123' not allowed" in error for error in errors)
    assert any(
        "Additional property 'data-items' not allowed" in error for error in errors)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
