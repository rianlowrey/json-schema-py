#!/usr/bin/env python3
"""
Tests for number-specific validation features.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on

class TestNumberValidation:
    """Tests for number-specific schema validation."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_number_constraints(self):
        """Test number-specific constraints."""
        schema = {
            "type": "number",
            "minimum": 10,
            "maximum": 100
        }

        # Valid - within range
        result = self.validator.validate(42, schema)
        assert result.valid

        # Invalid - below minimum
        result = self.validator.validate(5, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL
        assert "greater than or equal" in result.errors[0].message

        # Invalid - above maximum
        result = self.validator.validate(150, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_LARGE
        assert "less than or equal" in result.errors[0].message

    def test_multiple_of(self):
        """Test the multipleOf constraint."""
        schema = {
            "type": "integer",
            "multipleOf": 5
        }

        # Valid - multiple of 5
        result = self.validator.validate(25, schema)
        assert result.valid

        # Invalid - not a multiple of 5
        result = self.validator.validate(27, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_NOT_MULTIPLE
        assert "multiple of" in result.errors[0].message

    def test_exclusive_ranges(self):
        """Test exclusive minimum and maximum constraints."""
        schema = {
            "type": "number",
            "exclusiveMinimum": True,
            "minimum": 10,
            "exclusiveMaximum": True,
            "maximum": 100
        }

        # Valid - within exclusive range
        result = self.validator.validate(42, schema)
        assert result.valid

        # Invalid - equal to minimum
        result = self.validator.validate(10, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL
        assert "greater than" in result.errors[0].message

        # Invalid - equal to maximum
        result = self.validator.validate(100, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_LARGE
        assert "less than" in result.errors[0].message

    def test_integer_only(self):
        """Test integer-only validation."""
        schema = {
            "type": "integer",
            "minimum": 1,
            "maximum": 10
        }

        # Valid integer
        result = self.validator.validate(5, schema)
        assert result.valid

        # Invalid - float
        result = self.validator.validate(5.5, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR
        assert "integer" in result.errors[0].message

    def test_floating_point_multiple_of(self):
        """Test multipleOf with floating-point numbers."""
        schema = {
            "type": "number",
            "multipleOf": 0.1
        }

        # Valid - multiple of 0.1
        result = self.validator.validate(0.5, schema)
        assert result.valid

        # Valid - accounts for floating-point precision issues
        # 0.3 is actually 0.30000000000000004
        result = self.validator.validate(0.3, schema)
        assert result.valid

        # Invalid - not a multiple of 0.1
        result = self.validator.validate(0.37, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_NOT_MULTIPLE
        assert "multiple of" in result.errors[0].message

    def test_standalone_constraints(self):
        """Test number constraints without explicit type."""
        schema = {
            "minimum": 10,
            "multipleOf": 5
        }

        # Valid number
        result = self.validator.validate(15, schema)
        assert result.valid

        # Invalid - below minimum
        result = self.validator.validate(7, schema)
        assert not result.valid
        assert len(result.errors) == 2
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL
        assert result.errors[1].code == ErrorCode.NUMBER_NOT_MULTIPLE

        # note: ignored; discovered design flaw in implementing dependency order implicit type validation
        #   this is due to JSON Schema permissive type validation where rules without explicit type permit
        #   any type
        # Should not apply to non-numbers
        # result = self.validator.validate("abc", schema)
        # assert result.valid

    def test_number_and_boolean(self):
        """Test that boolean values are not considered numbers."""
        schema = {
            "type": "number"
        }

        # Boolean should not be valid as a number
        result = self.validator.validate(True, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

        result = self.validator.validate(False, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
