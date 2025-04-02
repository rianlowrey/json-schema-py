#!/usr/bin/env python3
"""
Tests for basic validation features like types, enums, and const values.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on


class TestBasicValidation:
    """Tests for basic schema validation."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_valid_object(self):
        """Test basic validation of a valid object."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        data = {"name": "test"}

        result = self.validator.validate(data, schema)
        assert result.valid
        assert not result.errors

    def test_invalid_type(self):
        """Test validation of an object with an invalid property type."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        data = {"name": 123}

        result = self.validator.validate(data, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR
        assert "Expected string" in result.errors[0].message

    def test_enum_validation(self):
        """Test validation against an enumeration."""
        schema = {"type": "string", "enum": ["red", "green", "blue"]}

        # Valid value
        result = self.validator.validate("red", schema)
        assert result.valid
        assert not result.errors

        # Invalid value
        result = self.validator.validate("yellow", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.ENUM_MISMATCH
        assert "not in enumeration" in result.errors[0].message

    def test_const_validation(self):
        """Test validation against a constant value."""
        schema = {"const": 42}

        # Valid value
        result = self.validator.validate(42, schema)
        assert result.valid
        assert not result.errors

        # Invalid value
        result = self.validator.validate("not 42", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.CONST_MISMATCH
        assert "Expected constant value" in result.errors[0].message

    def test_multiple_types(self):
        """Test validation against multiple types."""
        schema = {"type": ["string", "number"]}

        # Valid string
        result = self.validator.validate("test", schema)
        assert result.valid

        # Valid number
        result = self.validator.validate(123, schema)
        assert result.valid

        # Invalid type
        result = self.validator.validate(True, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_type_edge_cases(self):
        """Test edge cases in type validation."""
        # Boolean vs number/integer distinction
        schema_number = {"type": "number"}
        schema_integer = {"type": "integer"}
        schema_boolean = {"type": "boolean"}

        # Boolean shouldn't be valid as a number
        result = self.validator.validate(True, schema_number)
        assert not result.valid

        # Boolean shouldn't be valid as an integer
        result = self.validator.validate(True, schema_integer)
        assert not result.valid

        # Boolean should be valid as a boolean
        result = self.validator.validate(True, schema_boolean)
        assert result.valid

        # Integer should be valid as a number
        result = self.validator.validate(42, schema_number)
        assert result.valid

        # Integer should be valid as an integer
        result = self.validator.validate(42, schema_integer)
        assert result.valid

        # Integer shouldn't be valid as a boolean
        result = self.validator.validate(42, schema_boolean)
        assert not result.valid

        # Float should be valid as a number
        result = self.validator.validate(3.14, schema_number)
        assert result.valid

        # Float shouldn't be valid as an integer
        result = self.validator.validate(3.14, schema_integer)
        assert not result.valid

        # Float shouldn't be valid as a boolean
        result = self.validator.validate(3.14, schema_boolean)
        assert not result.valid

    def test_reference_resolution(self):
        """Test resolution of schema references."""
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
        result = self.validator.validate({"count": 5}, schema)
        assert result.valid

        # Invalid data (negative number)
        result = self.validator.validate({"count": -5}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL

    def test_nested_validation(self):
        """Test validation of nested objects."""
        schema = {
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer", "minimum": 0}
                    },
                    "required": ["name"]
                }
            }
        }

        # Valid data
        result = self.validator.validate(
            {"person": {"name": "John", "age": 30}}, schema)
        assert result.valid

        # Missing required property
        result = self.validator.validate({"person": {"age": 30}}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.REQUIRED_PROPERTY_MISSING

        # Value below minimum
        result = self.validator.validate(
            {"person": {"name": "John", "age": -5}}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
