#!/usr/bin/env python3
"""
Tests for string-specific validation features.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on


class TestStringValidation:
    """Tests for string-specific schema validation."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_string_constraints(self):
        """Test string-specific constraints."""
        schema = {
            "type": "string",
            "minLength": 3,
            "maxLength": 10
        }

        # Valid - within length constraints
        result = self.validator.validate("test", schema)
        assert result.valid

        # Invalid - too short
        result = self.validator.validate("ab", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.STRING_TOO_SHORT
        assert "minimum" in result.errors[0].message

        # Invalid - too long
        result = self.validator.validate("this_is_too_long", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.STRING_TOO_LONG
        assert "maximum" in result.errors[0].message

    def test_pattern_validation(self):
        """Test pattern-based validation."""
        schema = {
            "type": "string",
            "pattern": "^[a-z]+$"
        }

        # Valid - matches pattern
        result = self.validator.validate("abcdef", schema)
        assert result.valid

        # Invalid - doesn't match pattern
        result = self.validator.validate("123abc", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.PATTERN_MISMATCH
        assert "pattern" in result.errors[0].message

        result = self.validator.validate("ABCDEF", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.PATTERN_MISMATCH

    def test_email_pattern(self):
        """Test validation with a common email pattern."""
        schema = {
            "type": "string",
            "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        }

        # Valid - matches email pattern
        result = self.validator.validate("user@example.com", schema)
        assert result.valid

        # Invalid - doesn't match email pattern
        result = self.validator.validate("not-an-email", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.PATTERN_MISMATCH

    def test_invalid_pattern(self):
        """Test handling of invalid regex patterns."""
        schema = {
            "type": "string",
            "pattern": "["  # Invalid regex pattern
        }

        result = self.validator.validate("test", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.SCHEMA_INVALID
        assert "Invalid regex pattern" in result.errors[0].message

    def test_standalone_constraints(self):
        """Test string constraints without explicit type."""
        schema = {
            "minLength": 3,
            "pattern": "^[A-Z]"
        }

        # Valid string
        result = self.validator.validate("Abc", schema)
        assert result.valid

        # Invalid - too short
        result = self.validator.validate("Ab", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.STRING_TOO_SHORT

        # Invalid - doesn't match pattern
        result = self.validator.validate("abc", schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.PATTERN_MISMATCH

        # Invalid - hould not apply to non-strings
        result = self.validator.validate(123, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_nested_string_validation(self):
        """Test string validation in nested objects."""
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "minLength": 3,
                            "maxLength": 20,
                            "pattern": "^[a-zA-Z0-9_]+$"
                        },
                        "email": {
                            "type": "string",
                            "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                        }
                    }
                }
            }
        }

        # Valid data
        data = {
            "user": {
                "username": "johndoe",
                "email": "john@example.com"
            }
        }
        result = self.validator.validate(data, schema)
        assert result.valid

        # Invalid username (contains special characters)
        data = {
            "user": {
                "username": "john@doe",
                "email": "john@example.com"
            }
        }
        result = self.validator.validate(data, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.PATTERN_MISMATCH

        # Invalid email
        data = {
            "user": {
                "username": "johndoe",
                "email": "invalid-email"
            }
        }
        result = self.validator.validate(data, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.PATTERN_MISMATCH


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
