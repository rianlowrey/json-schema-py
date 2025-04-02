#!/usr/bin/env python3
"""
Tests for JSON Schema reference resolution and validation.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on


class TestReferenceValidation:
    """Tests for JSON Schema reference resolution and validation."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_basic_reference(self):
        """Test basic reference resolution."""
        schema = {
            "definitions": {
                "positiveInteger": {
                    "type": "integer",
                    "minimum": 1
                }
            },
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

        # Invalid data (wrong type)
        result = self.validator.validate({"count": "5"}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_nested_references(self):
        """Test nested reference resolution."""
        schema = {
            "definitions": {
                "positiveInteger": {
                    "type": "integer",
                    "minimum": 1
                },
                "count": {
                    "$ref": "#/definitions/positiveInteger"
                },
                "countArray": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/count"
                    }
                }
            },
            "properties": {
                "counts": {"$ref": "#/definitions/countArray"}
            }
        }

        # Valid data
        result = self.validator.validate({"counts": [1, 2, 3]}, schema)
        assert result.valid

        # Invalid data (array with negative number)
        result = self.validator.validate({"counts": [1, -2, 3]}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL

        # Invalid data (array with wrong type)
        result = self.validator.validate({"counts": [1, "2", 3]}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_reference_in_logical_operators(self):
        """Test reference resolution within logical operators."""
        schema = {
            "definitions": {
                "positiveInteger": {
                    "type": "integer",
                    "minimum": 1
                },
                "evenInteger": {
                    "type": "integer",
                    "multipleOf": 2
                }
            },
            "properties": {
                "count": {
                    "allOf": [
                        {"$ref": "#/definitions/positiveInteger"},
                        {"$ref": "#/definitions/evenInteger"}
                    ]
                }
            }
        }

        # Valid data (positive even integer)
        result = self.validator.validate({"count": 2}, schema)
        assert result.valid

        # Invalid data (positive odd integer)
        result = self.validator.validate({"count": 3}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_NOT_MULTIPLE

        # Invalid data (negative even integer)
        result = self.validator.validate({"count": -2}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.NUMBER_TOO_SMALL

    def test_reference_non_existent(self):
        """Test handling of non-existent references."""
        schema = {
            "properties": {
                "count": {"$ref": "#/definitions/nonExistent"}
            }
        }

        # Should report a reference resolution error
        result = self.validator.validate({"count": 5}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.REFERENCE_RESOLUTION_FAILED
        assert "No resolver provided for reference" in result.errors[0].message

    def test_circular_reference(self):
        """Test handling of circular references."""
        schema = {
            "definitions": {
                "node": {
                    "type": "object",
                    "properties": {
                        "child": {"$ref": "#/definitions/node"}
                    }
                }
            },
            "properties": {
                "root": {"$ref": "#/definitions/node"}
            }
        }

        # Valid nested data
        result = self.validator.validate({
            "root": {
                "child": {
                    "child": {}
                }
            }
        }, schema)
        assert result.valid

        # Invalid data (wrong type at nested level)
        result = self.validator.validate({
            "root": {
                "child": "not an object"
            }
        }, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.TYPE_ERROR

    def test_external_reference_forbidden(self):
        """Test that external references are forbidden."""
        schema = {
            "properties": {
                "count": {"$ref": "https://example.com/schema.json"}
            }
        }

        # Should report a reference resolution error
        result = self.validator.validate({"count": 5}, schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].code == ErrorCode.REFERENCE_RESOLUTION_FAILED
        assert "No resolver provided for reference" in result.errors[0].message


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
