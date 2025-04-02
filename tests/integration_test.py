#!/usr/bin/env python3
"""
Integration tests for the JSON validator.
"""
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonSchemaValidator, ConfigValidator
# autopep8: on


@pytest.fixture
def valid_schema():
    """Create a valid schema for testing."""
    return {
        "$schema": "http://json-schema.org/draft-2020-12/schema#",
        "title": "Test Schema",
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "library": {"type": "boolean"},
                "executable": {"type": "boolean"},
                "includes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "platform": {"type": "string", "enum": ["any", "windows", "linux"]},
                            "public": {"type": "array", "items": {"type": "string"}},
                            "private": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["platform"]
                    }
                }
            }
        }
    }


@pytest.fixture
def valid_config():
    """Create a valid configuration for testing."""
    return {
        "test_project": {
            "library": True,
            "executable": False,
            "includes": [
                {
                    "platform": "any",
                    "public": ["include/header.h"]
                }
            ]
        }
    }


@pytest.fixture
def invalid_config():
    """Create an invalid configuration for testing."""
    return {
        "test_project": {
            "library": "yes",  # Should be boolean
            "executable": False,
            "includes": [
                {
                    # Missing required platform field
                    "public": ["include/header.h"]
                }
            ]
        }
    }


@pytest.fixture
def temp_files(valid_schema, valid_config):
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Create schema file
        schema_file = temp_dir_path / "schema.json"
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(valid_schema, f)

        # Create config file
        config_file = temp_dir_path / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(valid_config, f)

        # Create a mock header file
        include_dir = temp_dir_path / "include"
        include_dir.mkdir()
        header_file = include_dir / "header.h"
        header_file.touch()

        yield {
            "temp_dir": temp_dir_path,
            "schema_file": schema_file,
            "config_file": config_file,
            "header_file": header_file
        }


def test_successful_validation(temp_files):
    """Test that a valid config passes validation."""
    validator = ConfigValidator()
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])
    assert len(errors) == 0


def test_load_json_valid(temp_files):
    """Test loading a valid JSON file."""
    validator = ConfigValidator()
    data = validator.load_json(temp_files["config_file"])
    assert isinstance(data, dict)
    assert "test_project" in data


def test_load_json_file_not_found():
    """Test loading a non-existent JSON file."""
    validator = ConfigValidator()
    with pytest.raises(FileNotFoundError) as excinfo:
        validator.load_json("non_existent.json")
    assert "File not found" in str(excinfo.value)


def test_load_json_invalid_json(temp_files):
    """Test loading a file with invalid JSON."""
    # Create a file with invalid JSON
    invalid_json_file = temp_files["temp_dir"] / "invalid.json"
    with open(invalid_json_file, "w", encoding="utf-8") as f:
        f.write("{invalid json}")

    validator = ConfigValidator()
    with pytest.raises(json.JSONDecodeError) as excinfo:
        validator.load_json(invalid_json_file)

    # Check that our custom error message is in the exception
    assert "Failed to parse" in str(excinfo.value)


def test_invalid_boolean_type(temp_files, invalid_config):
    """Test that a string instead of boolean fails validation."""
    # Write the invalid config to the file
    with open(temp_files["config_file"], "w", encoding="utf-8") as f:
        json.dump(invalid_config, f)

    validator = ConfigValidator()
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])

    # Check for both schema validation errors and custom validation errors
    assert any("library" in error.lower() and "boolean" in error.lower()
               for error in errors)


def test_missing_platform(temp_files, invalid_config):
    """Test that missing platform field fails validation."""
    # Write the invalid config to the file
    with open(temp_files["config_file"], "w", encoding="utf-8") as f:
        json.dump(invalid_config, f)

    validator = ConfigValidator()
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])

    # Check for platform errors
    assert any("platform" in error and "missing" in error.lower()
               for error in errors)


def test_file_existence_check(temp_files):
    """Test that file existence checking works."""
    # Modify the config to reference a non-existent file
    with open(temp_files["config_file"], "r", encoding="utf-8") as f:
        config = json.load(f)

    config["test_project"]["includes"][0]["public"] = [
        "include/non_existent.h"]

    with open(temp_files["config_file"], "w", encoding="utf-8") as f:
        json.dump(config, f)

    # Test with file existence checking enabled
    validator = ConfigValidator(
        check_file_existence=True, base_dir=temp_files["temp_dir"])
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])
    assert len(errors) > 0
    assert any("File not found" in error for error in errors)

    # Test with file existence checking disabled (should pass)
    validator = ConfigValidator(check_file_existence=False)
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])
    assert len(errors) == 0


def test_duplicate_file_paths(temp_files):
    """Test that duplicate file paths are detected."""
    # Modify the config to have duplicate file paths
    with open(temp_files["config_file"], "r", encoding="utf-8") as f:
        config = json.load(f)

    config["test_project"]["includes"].append({
        "platform": "windows",
        "public": ["include/header.h"]  # Duplicate of the existing path
    })

    with open(temp_files["config_file"], "w", encoding="utf-8") as f:
        json.dump(config, f)

    validator = ConfigValidator()
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])
    assert len(errors) > 0
    assert any("Duplicate file path" in error for error in errors)


def test_missing_file(temp_files):
    """Test for non-existent JSON file."""
    validator = ConfigValidator()
    errors = validator.validate("non_existent.json", temp_files["schema_file"])
    assert len(errors) > 0
    assert any("File not found" in error for error in errors)


def test_invalid_json(temp_files):
    """Test for invalid JSON in file."""
    # Create a file with invalid JSON
    invalid_json_file = temp_files["temp_dir"] / "invalid.json"
    with open(invalid_json_file, "w", encoding="utf-8") as f:
        f.write("{invalid json}")

    validator = ConfigValidator()
    errors = validator.validate(invalid_json_file, temp_files["schema_file"])
    assert len(errors) > 0
    assert any("Failed to parse" in error for error in errors)


def test_missing_visibility(temp_files):
    """Test that missing visibility section fails validation."""
    with open(temp_files["config_file"], "r", encoding="utf-8") as f:
        config = json.load(f)

    # Remove both public and private sections
    del config["test_project"]["includes"][0]["public"]

    with open(temp_files["config_file"], "w", encoding="utf-8") as f:
        json.dump(config, f)

    validator = ConfigValidator()
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])
    assert len(errors) > 0
    assert any(
        "Must have either 'public' or 'private' section" in error for error in errors)


def test_invalid_platform(temp_files):
    """Test that an invalid platform value fails validation."""
    with open(temp_files["config_file"], "r", encoding="utf-8") as f:
        config = json.load(f)

    # Set an invalid platform
    config["test_project"]["includes"][0]["platform"] = "invalid_platform"

    with open(temp_files["config_file"], "w", encoding="utf-8") as f:
        json.dump(config, f)

    validator = ConfigValidator()
    errors = validator.validate(
        temp_files["config_file"], temp_files["schema_file"])
    assert len(errors) > 0
    assert any(
        "Value 'invalid_platform' not in enumeration" in error for error in errors)


def test_complex_schema_validation():
    """Test validation of a complex schema with multiple constraints."""
    validator = ConfigValidator()

    schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 2,
                "maxLength": 50
            },
            "age": {
                "type": "integer",
                "minimum": 0,
                "maximum": 120
            },
            "email": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 10,
                "uniqueItems": True
            },
            "settings": {
                "type": "object",
                "properties": {
                    "newsletter": {"type": "boolean"},
                    "theme": {"enum": ["light", "dark", "system"]}
                },
                "required": ["newsletter"]
            }
        },
        "required": ["name", "email"]
    }

    # Create a validator with just the schema for this test
    class SimpleValidator:
        def __init__(self):
            self.schema_validator = validator.schema_validator

        def validate(self, data):
            return self.schema_validator.validate(data, schema)

    simple_validator = SimpleValidator()

    # Valid complex object
    valid_data = {
        "name": "John Doe",
        "age": 30,
        "email": "john@example.com",
        "tags": ["user", "premium"],
        "settings": {
            "newsletter": False,
            "theme": "dark"
        }
    }
    assert len(simple_validator.validate(valid_data)) == 0

    # Invalid - missing required field
    invalid_data = {
        "name": "John Doe",
        "age": 30,
        "tags": ["user"]
    }
    errors = simple_validator.validate(invalid_data)
    assert len(errors) > 0
    assert any("Missing required property 'email'" in error for error in errors)

    # Invalid - multiple validation errors
    invalid_data2 = {
        "name": "J",  # too short
        "email": "invalid-email",  # invalid pattern
        "age": 150,  # above maximum
        "tags": [],  # empty array
        "settings": {}  # missing required property
    }
    errors = simple_validator.validate(invalid_data2)
    # Should have at least 5 errors for the issues above
    assert len(errors) >= 5


def test_command_line_args():
    """Test command-line argument parsing."""
    from json_schema.cli import parse_args

    # Test basic arguments
    args = parse_args(['config.json', 'schema.json'])
    assert args.data_file == 'config.json'
    assert args.schema_file == 'schema.json'
    assert not args.check_files
    assert not args.verbose

    # Test all options
    args = parse_args(['config.json', 'schema.json',
                      '--check-files', '--verbose'])
    assert args.data_file == 'config.json'
    assert args.schema_file == 'schema.json'
    assert args.check_files
    assert args.verbose


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
