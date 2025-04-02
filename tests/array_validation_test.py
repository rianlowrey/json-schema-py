#!/usr/bin/env python3
"""
Tests for array-specific validation features.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on


class TestArrayValidation:
    """Tests for array-specific schema validation."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_array_constraints(self):
        """Test array-specific constraints."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
            "uniqueItems": True
        }

        # Valid array
        result = self.validator.validate(["red", "green", "blue"], schema)
        assert result.valid

        # Empty array (violates minItems)
        result = self.validator.validate([], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_TOO_SHORT
        assert "minimum" in result.errors[0].message

        # Too many items (violates maxItems)
        result = self.validator.validate(
            ["one", "two", "three", "four", "five", "six"], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_TOO_LONG
        assert "maximum" in result.errors[0].message

        # Non-unique items
        result = self.validator.validate(["red", "green", "red"], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_ITEMS_NOT_UNIQUE
        assert "unique" in result.errors[0].message

        # Wrong item type
        result = self.validator.validate(["red", 123, "blue"], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR
        assert "string" in result.errors[0].message

    def test_array_in_object(self):
        """Test array validation within an object."""
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
        result = self.validator.validate(
            {"tags": ["red", "green", "blue"]}, schema)
        assert result.valid

        # Empty array (violates minItems)
        result = self.validator.validate({"tags": []}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_TOO_SHORT

        # Non-unique items
        result = self.validator.validate(
            {"tags": ["red", "green", "red"]}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_ITEMS_NOT_UNIQUE

        # Wrong item type
        result = self.validator.validate(
            {"tags": ["red", 123, "blue"]}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_array_standalone_constraints(self):
        """Test standalone array constraints without explicit type."""
        schema = {
            "minItems": 2,
            "maxItems": 5
        }

        # Valid - array with 3 items
        result = self.validator.validate([1, 2, 3], schema)
        assert result.valid

        # Invalid - array too short
        result = self.validator.validate([1], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_TOO_SHORT

        # Invalid - array too long
        result = self.validator.validate([1, 2, 3, 4, 5, 6], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ARRAY_TOO_LONG

        # Test non-array values with array schema (shouldn't be applied)
        result = self.validator.validate("not an array", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_nested_arrays(self):
        """Test validation of nested arrays."""
        schema = {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"type": "integer"}
            }
        }

        # Valid - array of arrays of integers
        result = self.validator.validate([[1, 2], [3, 4], [5, 6]], schema)
        assert result.valid

        # Invalid - contains non-integer
        result = self.validator.validate([[1, 2], [3, "4"], [5, 6]], schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR
        assert "integer" in result.errors[0].message

        # Invalid - contains non-array
        result = self.validator.validate([[1, 2], 3, [5, 6]], schema)

        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR
        assert "array" in result.errors[0].message

    def test_complex_array_validation(self):
        """Test complex array validation with object items."""
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["id", "name"]
            }
        }

        # Valid data
        valid_data = [
            {"id": 1, "name": "Item 1", "tags": ["tag1", "tag2"]},
            {"id": 2, "name": "Item 2", "tags": ["tag3"]}
        ]
        result = self.validator.validate(valid_data, schema)
        assert result.valid

        # Invalid data - missing required property
        invalid_data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "tags": ["tag3"]}  # Missing "name"
        ]
        result = self.validator.validate(invalid_data, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.REQUIRED_PROPERTY_MISSING

        # Invalid data - wrong type in nested array
        invalid_data = [
            {"id": 1, "name": "Item 1", "tags": [
                "tag1", 123]}  # Number in tags array
        ]
        result = self.validator.validate(invalid_data, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
