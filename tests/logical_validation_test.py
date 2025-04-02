#!/usr/bin/env python3
"""
Tests for logical validation operators (allOf, anyOf, oneOf, not).
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on

class TestLogicalValidation:
    """Tests for logical schema validation operators."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_any_of_validation(self):
        """Test anyOf validation."""
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "boolean"}
            ]
        }

        # Valid - matches first schema (string)
        result = self.validator.validate("test", schema)
        assert result.valid

        # Valid - matches second schema (number)
        result = self.validator.validate(42, schema)
        assert result.valid

        # Valid - matches third schema (boolean)
        result = self.validator.validate(True, schema)
        assert result.valid

        # Invalid - matches no schemas
        result = self.validator.validate(None, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ANY_OF_NO_MATCH
        assert "does not match any" in result.errors[0].message

    def test_any_of_with_constraints(self):
        """Test anyOf with type-specific constraints."""
        schema = {
            "anyOf": [
                {
                    "type": "string",
                    "minLength": 3
                },
                {
                    "type": "number",
                    "minimum": 10
                }
            ]
        }

        # Valid - matches first schema
        result = self.validator.validate("test", schema)
        assert result.valid

        # Valid - matches second schema
        result = self.validator.validate(42, schema)
        assert result.valid

        # Invalid - doesn't match either schema
        result = self.validator.validate(
            "ab", schema)  # Too short for first schema
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ANY_OF_NO_MATCH

        result = self.validator.validate(
            5, schema)  # Too small for second schema
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ANY_OF_NO_MATCH

    def test_all_of_validation(self):
        """Test allOf validation."""
        schema = {
            "allOf": [
                {"type": "number"},
                {"minimum": 10},
                {"maximum": 100}
            ]
        }

        # Valid - matches all schemas
        result = self.validator.validate(42, schema)
        assert result.valid

        # Invalid - wrong type
        result = self.validator.validate("test", schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

        # Invalid - below minimum
        result = self.validator.validate(5, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL

        # Invalid - above maximum
        result = self.validator.validate(200, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_LARGE

        # Test boolean vs number distinction
        result = self.validator.validate(True, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_all_of_with_objects(self):
        """Test allOf with object constraints."""
        schema = {
            "allOf": [
                {
                    "type": "object",
                    "required": ["name"]
                },
                {
                    "type": "object",
                    "required": ["age"]
                }
            ]
        }

        # Valid - has all required properties
        result = self.validator.validate({"name": "John", "age": 30}, schema)
        assert result.valid

        # Invalid - missing a required property
        result = self.validator.validate({"name": "John"}, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.REQUIRED_PROPERTY_MISSING

        result = self.validator.validate({"age": 30}, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.REQUIRED_PROPERTY_MISSING

    def test_one_of_validation(self):
        """Test oneOf validation."""
        schema = {
            "oneOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "boolean"}
            ]
        }

        # Valid - matches exactly one schema (string)
        result = self.validator.validate("test", schema)
        assert result.valid

        # Valid - matches exactly one schema (number)
        result = self.validator.validate(42, schema)
        assert result.valid

        # Valid - matches exactly one schema (boolean)
        result = self.validator.validate(True, schema)
        assert result.valid

        # Invalid - matches no schemas
        result = self.validator.validate(None, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ONE_OF_NO_MATCH
        assert "does not match any" in result.errors[0].message

    def test_one_of_multiple_matches(self):
        """Test oneOf validation with multiple matching schemas."""
        schema = {
            "oneOf": [
                {"type": "number"},
                {"type": "integer"},
                {"type": "string", "pattern": "^[0-9]+$"}
            ]
        }

        # Valid - matches exactly one schema (the string pattern only)
        result = self.validator.validate("123", schema)
        assert result.valid

        # Valid - string doesn't match pattern, so matches one schema
        result = self.validator.validate("abc", schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ONE_OF_NO_MATCH

        # Invalid - matches multiple schemas (integer matches both number and integer)
        result = self.validator.validate(42, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ONE_OF_MULTIPLE_MATCHES
        assert "matches" in result.errors[0].message and "schemas" in result.errors[0].message

    def test_not_validation(self):
        """Test 'not' validation."""
        schema = {
            "not": {"type": "string"}
        }

        # Valid - not a string
        result = self.validator.validate(42, schema)
        assert result.valid

        result = self.validator.validate(True, schema)
        assert result.valid

        result = self.validator.validate(None, schema)
        assert result.valid

        # Invalid - is a string
        result = self.validator.validate("test", schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.NOT_SCHEMA_MATCHED
        assert "should not validate" in result.errors[0].message

    def test_not_with_complex_schema(self):
        """Test 'not' with a complex schema."""
        schema = {
            "not": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }

        # Valid - not an object with required name property
        result = self.validator.validate(
            {"id": 123}, schema)  # Object without name
        assert result.valid

        result = self.validator.validate("test", schema)  # Not an object
        assert result.valid

        # Invalid - is an object with name
        result = self.validator.validate({"name": "John"}, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.NOT_SCHEMA_MATCHED

    def test_combined_logical_operators(self):
        """Test combinations of logical operators."""
        schema = {
            "anyOf": [
                {
                    "type": "object",
                    "allOf": [
                        {"required": ["name"]},
                        {"required": ["age"]}
                    ]
                },
                {
                    "type": "string",
                    "not": {"pattern": "^[0-9]"}
                }
            ]
        }

        # Valid - matches first anyOf (object with name and age)
        result = self.validator.validate({"name": "John", "age": 30}, schema)
        assert result.valid

        # Valid - matches second anyOf (string not starting with a number)
        result = self.validator.validate("abc", schema)
        assert result.valid

        # Invalid - object missing required property
        result = self.validator.validate({"name": "John"}, schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ANY_OF_NO_MATCH

        # Invalid - string starting with a number
        result = self.validator.validate("123", schema)
        assert not result.valid
        assert len(result.errors) >= 1
        assert result.errors[0].code == ErrorCode.ANY_OF_NO_MATCH


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
