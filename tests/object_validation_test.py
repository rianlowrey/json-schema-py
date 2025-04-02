#!/usr/bin/env python3
"""
Tests for object-specific validation features.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_object_constraints():
    """Test object-specific constraints in the schema validator."""
    validator = JsonSchemaValidator()

    # Test required properties
    schema = {
        "type": "object",
        "required": ["name", "age"]
    }

    # Valid - has all required properties
    data = {"name": "John", "age": 30}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - missing required property
    data = {"name": "John"}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Missing required property 'age'" in error for error in errors)

    # Test properties with specific types
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        }
    }

    # Valid - properties have correct types
    data = {"name": "John", "age": 30}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - wrong property type
    data = {"name": 123, "age": "thirty"}
    errors = validator.validate(data, schema)
    assert len(errors) >= 2

    # Test non-object with object schema
    errors = validator.validate("not an object", schema)
    assert len(errors) > 0
    assert any("Expected object" in error for error in errors)


def test_property_names_validation():
    """Test property names validation."""
    validator = JsonSchemaValidator()

    # Test schema with propertyNames constraint
    schema = {
        "type": "object",
        "propertyNames": {
            "pattern": "^[a-z][a-z0-9_]*$"
        }
    }

    # Valid - all property names match pattern
    data = {"name": "value", "age23": 42, "user_id": "abc123"}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - some property names don't match pattern
    data = {"Name": "value", "123age": 42, "user-id": "abc123"}
    errors = validator.validate(data, schema)
    # Should have at least 3 errors (one for each invalid property name)
    assert len(errors) >= 3
    assert any("'Name' does not match pattern" in error for error in errors)
    assert any("'123age' does not match pattern" in error for error in errors)
    assert any("'user-id' does not match pattern" in error for error in errors)

    # Test with other propertyNames constraints
    schema = {
        "type": "object",
        "propertyNames": {
            "maxLength": 5
        }
    }

    # Valid - all property names are short enough
    data = {"a": 1, "ab": 2, "abc": 3, "abcd": 4, "abcde": 5}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - some property names are too long
    data = {"short": 1, "toolong": 2}
    errors = validator.validate(data, schema)
    assert len(errors) >= 1
    assert any("toolong" in error and "maximum is 5" in error for error in errors)


def test_property_names_error_formatting():
    """Test error message formatting in propertyNames validation."""
    validator = JsonSchemaValidator()

    # Schema with various constraints on property names
    schema = {
        "type": "object",
        "propertyNames": {
            "type": "string",
            "minLength": 3,
            "maxLength": 10,
            "pattern": "^[a-z]+$"
        }
    }

    # Test data with invalid property names
    data = {
        "a": 1,           # Too short
        "UPPERCASE": 2,   # Wrong pattern
        "very_long_name": 3,  # Too long
        "valid": 4        # This one is fine
    }

    errors = validator.validate(data, schema)

    # Check for proper error message formatting
    assert len(errors) >= 3  # Should have at least 3 errors

    # Check that error messages use "Property name" format
    property_name_errors = [e for e in errors if "Property name" in e]
    assert len(property_name_errors) >= 3

    # Check specific error messages for each property
    assert any("Property name 'a'" in e and "minimum is 3" in e for e in errors)
    assert any(
        "Property name 'UPPERCASE'" in e and "does not match pattern" in e for e in errors)
    assert any(
        "Property name 'very_long_name'" in e and "maximum is 10" in e for e in errors)

    # Check that path is properly formatted (should reference the parent object path)
    for error in errors:
        # The path should not include the property name as a path segment
        if "Property name 'a'" in error:
            assert not "/a:" in error
        elif "Property name 'UPPERCASE'" in error:
            assert not "/UPPERCASE:" in error
        elif "Property name 'very_long_name'" in error:
            assert not "/very_long_name:" in error


def test_dependencies_validation():
    """Test property dependencies validation."""
    validator = JsonSchemaValidator()

    # Test schema with dependencies
    schema = {
        "type": "object",
        "properties": {
            "credit_card": {"type": "string"},
            "billing_address": {"type": "string"},
            "shipping_address": {"type": "string"}
        },
        "dependencies": {
            "credit_card": ["billing_address"],
            "shipping_address": ["billing_address"]
        }
    }

    # Valid - no dependent properties present
    data = {}
    assert len(validator.validate(data, schema)) == 0

    # Valid - credit_card with required dependency
    data = {"credit_card": "1234-5678-9012-3456",
            "billing_address": "123 Main St"}
    assert len(validator.validate(data, schema)) == 0

    # Valid - shipping_address with required dependency
    data = {"shipping_address": "123 Main St",
            "billing_address": "123 Main St"}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - credit_card without required dependency
    data = {"credit_card": "1234-5678-9012-3456"}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("depends on 'billing_address'" in error for error in errors)

    # Invalid - shipping_address without required dependency
    data = {"shipping_address": "123 Main St"}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("depends on 'billing_address'" in error for error in errors)

    # Complex case - multiple dependencies
    data = {
        "credit_card": "1234-5678-9012-3456",
        "shipping_address": "123 Main St"
        # Missing billing_address which is required by both
    }
    errors = validator.validate(data, schema)
    # Should have at least 2 errors (one for each dependency)
    assert len(errors) >= 2


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
