#!/usr/bin/env python3
"""
Tests for array-specific validation features.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_schema_validator_arrays():
    """Test array validation in the schema validator."""
    validator = JsonSchemaValidator()
    
    schema = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 5,
        "uniqueItems": True
    }
    
    # Valid array
    data = ["red", "green", "blue"]
    assert len(validator.validate(data, schema)) == 0
    
    # Empty array (violates minItems)
    data = []
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("minimum is 1" in error for error in errors)
    
    # Too many items (violates maxItems)
    data = ["one", "two", "three", "four", "five", "six"]
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("maximum is 5" in error for error in errors)
    
    # Non-unique items
    data = ["red", "green", "red"]
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("unique items" in error.lower() for error in errors)
    
    # Wrong item type
    data = ["red", 123, "blue"]
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Expected string" in error for error in errors)


def test_array_in_object():
    """Test array validation within an object."""
    validator = JsonSchemaValidator()
    
    schema = {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "uniqueItems": True
            }
        }
    }
    
    # Valid array
    data = {"tags": ["red", "green", "blue"]}
    assert len(validator.validate(data, schema)) == 0
    
    # Empty array (violates minItems)
    data = {"tags": []}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("minimum is 1" in error for error in errors)
    
    # Non-unique items
    data = {"tags": ["red", "green", "red"]}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("unique items" in error.lower() for error in errors)

    # Wrong item type
    data = {"tags": ["red", 123, "blue"]}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Expected string" in error for error in errors)

def test_array_standalone_constraints():
    """Test standalone array constraints without explicit type."""
    validator = JsonSchemaValidator()
    
    schema = {
        "minItems": 2,
        "maxItems": 5
    }
    
    # Valid - array with 3 items
    assert len(validator.validate([1, 2, 3], schema)) == 0
    
    # Invalid - array too short
    errors = validator.validate([1], schema)
    assert len(errors) > 0
    assert any("minimum is 2" in error for error in errors)
    
    # Invalid - array too long
    errors = validator.validate([1, 2, 3, 4, 5, 6], schema)
    assert len(errors) > 0
    assert any("maximum is 5" in error for error in errors)
    
    # Test non-array values with array schema
    errors = validator.validate("not an array", schema)
    assert len(errors) > 0
    assert any("Expected array" in error for error in errors)


def test_nested_arrays():
    """Test validation of nested arrays."""
    validator = JsonSchemaValidator()
    
    schema = {
        "type": "array",
        "items": {
            "type": "array",
            "items": {"type": "integer"}
        }
    }
    
    # Valid - array of arrays of integers
    data = [[1, 2], [3, 4], [5, 6]]
    assert len(validator.validate(data, schema)) == 0
    
    # Invalid - contains non-integer
    data = [[1, 2], [3, "4"], [5, 6]]
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Expected integer" in error for error in errors)
    
    # Invalid - contains non-array
    data = [[1, 2], 3, [5, 6]]
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Expected array" in error for error in errors)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])