#!/usr/bin/env python3
"""
Advanced tests for property names validation to improve code coverage.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_property_names_type_error_formatting():
    """Test type error formatting in propertyNames validation."""
    validator = JsonSchemaValidator()

    # Schema with type constraint on property names
    schema = {
        "type": "object",
        "propertyNames": {
            "type": "integer"  # This will cause all string property names to fail type validation
        }
    }

    # Test data with string property names (which will fail integer type validation)
    data = {
        "prop1": 1,
        "prop2": 2
    }

    errors = validator.validate(data, schema)

    # Check for proper error message formatting
    # Should have at least 2 errors (one for each property)
    assert len(errors) >= 2

    # Check for the specific error format we're trying to test
    # This should trigger the branch with: f"got {type(prop).__name__}" in modified_error
    type_error_messages = [
        e for e in errors if "Property name" in e and "prop" in e]
    assert len(type_error_messages) >= 2

    # Verify the specific string replacements happened
    for prop in ["prop1", "prop2"]:
        assert any(f"Property name '{prop}'" in error for error in errors)
        # Verify "got str" was replaced with "Property name 'propX'"
        assert not any(f"got str" in error for error in errors)


def test_property_names_custom_error_formatting():
    """Test catch-all error formatting in propertyNames validation."""
    validator = JsonSchemaValidator()

    # Schema with enum constraint on property names
    schema = {
        "type": "object",
        "propertyNames": {
            "enum": ["allowed1", "allowed2"]  # Only these names are allowed
        }
    }

    # Test data with property names not in the enum
    data = {
        "not_allowed": 1,
        "another_invalid": 2
    }

    errors = validator.validate(data, schema)

    # Check for proper error message formatting
    assert len(errors) >= 2  # Should have at least 2 errors

    # Check for the specific error format we're trying to test
    # This should trigger the catch-all else branch
    for prop in ["not_allowed", "another_invalid"]:
        # The error should have the property name in it
        assert any(f"Property name '{prop}'" in error for error in errors)

        # The format is actually "Error at '': Property name 'prop'..."
        # which is what we expect based on the current implementation
        for error in errors:
            if prop in error:
                # Make sure the property name is included in the message
                assert f"Property name '{prop}'" in error

                # Verify the format follows our catch-all pattern
                assert "Error at ''" in error


def test_property_names_error_no_replacement():
    """Test error messages that don't need replacement in propertyNames validation."""
    validator = JsonSchemaValidator()

    # Create a test with a custom error message that doesn't have "Error at" prefix
    # We can do this by mocking the _validate_property_names method
    original_method = JsonSchemaValidator._validate_property_names

    try:
        # Replace with a mock implementation that returns a custom error
        def mock_validate_property_names(self, obj, schema, path, rootSchema):
            return ["Custom error: Property name already formatted"]

        # Apply the mock
        JsonSchemaValidator._validate_property_names = mock_validate_property_names

        # Run validation with our mock in place
        schema = {"type": "object", "propertyNames": {"type": "string"}}
        data = {"test": 1}

        errors = validator.validate(data, schema)

        # Check that our custom error message was passed through
        assert len(errors) == 1
        assert errors[0] == "Custom error: Property name already formatted"
    finally:
        # Restore the original method
        JsonSchemaValidator._validate_property_names = original_method


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
