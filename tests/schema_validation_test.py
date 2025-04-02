#!/usr/bin/env python3
"""
Tests for schema combination validators (allOf, anyOf, oneOf, not).
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator
# autopep8: on


def test_schema_validator_complex():
    """Test more complex schema validation."""
    validator = JsonSchemaValidator()

    # Test nested objects
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
    data = {"person": {"name": "John", "age": 30}}
    assert len(validator.validate(data, schema)) == 0

    # Missing required property
    data = {"person": {"age": 30}}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Missing required property 'name'" in error for error in errors)

    # Value below minimum
    data = {"person": {"name": "John", "age": -5}}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("minimum is 0" in error for error in errors)


def test_anyof_validation():
    """Test anyOf validation in the schema validator."""
    validator = JsonSchemaValidator()

    schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"}
        ]
    }

    # Valid - matches first schema (string)
    assert len(validator.validate("test", schema)) == 0

    # Valid - matches second schema (number)
    assert len(validator.validate(42, schema)) == 0

    # Valid - matches third schema (boolean)
    assert len(validator.validate(True, schema)) == 0

    # Invalid - matches no schemas
    errors = validator.validate(None, schema)
    assert len(errors) > 0
    assert any(
        "doesn't match any of the required schemas" in error for error in errors)

    # Test anyOf with type-specific constraints
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
    errors = validator.validate("test", schema)
    assert len(errors) == 0

    # Valid - matches second schema
    errors = validator.validate(42, schema)
    assert len(errors) == 0

    # Invalid - doesn't match either schema
    errors = validator.validate("ab", schema)  # Too short for first schema
    assert len(errors) > 0

    errors = validator.validate(5, schema)  # Too small for second schema
    assert len(errors) > 0


def test_allof_validation():
    """Test allOf validation in the schema validator."""
    validator = JsonSchemaValidator()

    schema = {
        "allOf": [
            {"type": "number"},
            {"minimum": 10},
            {"maximum": 100}
        ]
    }

    # Valid - matches all schemas
    assert len(validator.validate(42, schema)) == 0

    # Invalid - wrong type
    errors = validator.validate("test", schema)
    assert len(errors) > 0

    # Invalid - below minimum
    errors = validator.validate(5, schema)
    assert len(errors) > 0

    # Invalid - above maximum
    errors = validator.validate(200, schema)
    assert len(errors) > 0

    # Test boolean vs number distinction
    errors = validator.validate(True, schema)
    assert len(errors) > 0
    assert any("Expected number, got bool" in error for error in errors)

    # Test allOf with object constraints
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
    data = {"name": "John", "age": 30}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - missing a required property
    data = {"name": "John"}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any("Missing required property 'age'" in error for error in errors)


def test_oneof_validation():
    """Test oneOf validation in the schema validator."""
    validator = JsonSchemaValidator()

    schema = {
        "oneOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"}
        ]
    }

    # Valid - matches exactly one schema (string)
    assert len(validator.validate("test", schema)) == 0

    # Valid - matches exactly one schema (number)
    assert len(validator.validate(42, schema)) == 0

    # Valid - matches exactly one schema (boolean)
    assert len(validator.validate(True, schema)) == 0

    # Invalid - matches no schemas
    errors = validator.validate(None, schema)
    assert len(errors) > 0
    assert any(
        "doesn't match any of the required schemas in oneOf" in error for error in errors)

    # Test that number and boolean are properly distinguished
    schema_number_or_object = {
        "oneOf": [
            {"type": "number"},
            {"type": "object"}
        ]
    }

    # Boolean should not match either schema
    errors = validator.validate(True, schema_number_or_object)
    assert len(errors) > 0
    assert any(
        "doesn't match any of the required schemas in oneOf" in error for error in errors)


def test_expanded_one_of_validation():
    """Test expanded oneOf validation scenarios."""
    validator = JsonSchemaValidator()

    # Test oneOf with multiple matching schemas
    schema = {
        "oneOf": [
            {"type": "number"},
            {"type": "integer"},
            {"type": "string", "pattern": "^[0-9]+$"}
        ]
    }

    # Valid - matches exactly one schema (the string pattern only)
    assert len(validator.validate("123", schema)) == 0

    # Valid - string doesn't match pattern, so doesn't match any schema
    errors = validator.validate("abc", schema)
    assert len(errors) > 0
    assert any(
        "doesn't match any of the required schemas in oneOf" in error for error in errors)

    # Invalid - matches multiple schemas (integer matches both number and integer)
    errors = validator.validate(42, schema)
    assert len(errors) > 0
    assert any("matches" in error and "schemas" in error for error in errors)

    # Test complex oneOf with nested schemas
    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {"type": {"const": "person"}, "name": {"type": "string"}},
                "required": ["type", "name"]
            },
            {
                "type": "object",
                "properties": {"type": {"const": "company"}, "id": {"type": "integer"}},
                "required": ["type", "id"]
            }
        ]
    }

    # Valid - matches first schema only
    data = {"type": "person", "name": "John Doe"}
    assert len(validator.validate(data, schema)) == 0

    # Valid - matches second schema only
    data = {"type": "company", "id": 12345}
    assert len(validator.validate(data, schema)) == 0

    # Invalid - matches neither schema
    data = {"type": "unknown", "value": "test"}
    errors = validator.validate(data, schema)
    assert len(errors) > 0
    assert any(
        "doesn't match any of the required schemas in oneOf" in error for error in errors)


def test_not_validation():
    """Test 'not' validation in the schema validator."""
    validator = JsonSchemaValidator()

    schema = {
        "not": {"type": "string"}
    }

    # Valid - not a string
    assert len(validator.validate(42, schema)) == 0
    assert len(validator.validate(True, schema)) == 0
    assert len(validator.validate(None, schema)) == 0

    # Invalid - is a string
    errors = validator.validate("test", schema)
    assert len(errors) > 0
    assert any(
        "should not validate against 'not' schema" in error for error in errors)

    # Test complex not constraint
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
    # Object without name
    assert len(validator.validate({"id": 123}, schema)) == 0
    assert len(validator.validate("test", schema)) == 0  # Not an object

    # Invalid - is an object with name
    errors = validator.validate({"name": "John"}, schema)
    assert len(errors) > 0
    assert any(
        "should not validate against 'not' schema" in error for error in errors)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
