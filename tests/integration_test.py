#!/usr/bin/env python3
"""
Integration tests for the enhanced JSON validator.
"""
import json
import pytest
import tempfile
from pathlib import Path

# autopep8: off
from utils import setup
setup()
from json_schema import ErrorCode, JsonValidator
# autopep8: on


class TestIntegration:
    """Integration tests for the enhanced JSON validator."""

    def setup_method(self):
        """Set up the test environment."""
        self.validator = JsonValidator()

    def test_integration_with_file_validation(self):
        """Test end-to-end validation using file-based schema and data."""
        # Create a temporary schema file
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
                "email": {"type": "string", "pattern": "^.+@.+\\..+$"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True
                }
            },
            "required": ["name", "age", "email"],
            "additionalProperties": False
        }

        # Create valid data
        valid_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "tags": ["user", "admin"]
        }

        # Create invalid data with multiple errors
        invalid_data = {
            "name": 123,  # Wrong type
            "age": -10,   # Below minimum
            "email": "invalid-email",  # Invalid pattern
            "tags": ["user", "user"],  # Duplicate items
            "extra": "not allowed"  # Additional property
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Write schema and data to files
            schema_file = temp_dir_path / "schema.json"
            with open(schema_file, "w", encoding="utf-8") as f:
                json.dump(schema, f)

            valid_data_file = temp_dir_path / "valid.json"
            with open(valid_data_file, "w", encoding="utf-8") as f:
                json.dump(valid_data, f)

            invalid_data_file = temp_dir_path / "invalid.json"
            with open(invalid_data_file, "w", encoding="utf-8") as f:
                json.dump(invalid_data, f)

            # Load and validate the files
            with open(schema_file, "r", encoding="utf-8") as f:
                loaded_schema = json.load(f)

            with open(valid_data_file, "r", encoding="utf-8") as f:
                loaded_valid_data = json.load(f)

            with open(invalid_data_file, "r", encoding="utf-8") as f:
                loaded_invalid_data = json.load(f)

            # Validate valid data
            result = self.validator.validate(loaded_valid_data, loaded_schema)
            assert result.valid
            assert not result.errors

            # Validate invalid data
            result = self.validator.validate(
                loaded_invalid_data, loaded_schema)
            assert not result.valid
            assert len(result.errors) >= 5  # At least 5 validation errors

    def test_reuse_validation(self):
        """Test reusing the validator for multiple validations."""
        validator = JsonValidator()

        # Define schemas
        string_schema = {"type": "string", "minLength": 3}
        number_schema = {"type": "number", "minimum": 0}
        array_schema = {"type": "array", "items": {"type": "integer"}}

        # Validate multiple values against their respective schemas
        result = validator.validate("abc", string_schema)
        assert result.valid

        result = validator.validate("a", string_schema)
        assert not result.valid

        result = validator.validate(10, number_schema)
        assert result.valid

        result = validator.validate(-5, number_schema)
        assert not result.valid

        result = validator.validate([1, 2, 3], array_schema)
        assert result.valid

        result = validator.validate([1, "2", 3], array_schema)
        assert not result.valid

    @pytest.mark.skip(reason="discovered a design flaw; addressed in v0.3.0")
    def test_project_json(self):
        """Test validation of a project.json configuration similar to the original use case."""
        # Load the project schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "additionalProperties": {
                "$ref": "#/definitions/Project"
            },
            "description": "Schema for project configuration",
            "title": "Project Configuration",
            "type": "object",
            "definitions": {
                "Project": {
                    "additionalProperties": False,
                    "anyOf": [
                        {
                            "properties": {
                                "library": {
                                    "enum": [True]
                                }
                            },
                            "required": ["library"]
                        },
                        {
                            "properties": {
                                "executable": {
                                    "enum": [True]
                                }
                            },
                            "required": ["executable"]
                        }
                    ],
                    "properties": {
                        "description": {
                            "description": "Project description",
                            "type": "string"
                        },
                        "executable": {
                            "default": False,
                            "description": "whether this is an executable project",
                            "type": "boolean"
                        },
                        "library": {
                            "default": False,
                            "description": "whether this is a library project",
                            "type": "boolean"
                        },
                        "install": {
                            "default": False,
                            "description": "whether this project should be installed",
                            "type": "boolean"
                        },
                        "libraries": {
                            "description": "libraries to link against",
                            "items": {
                                "type": "string"
                            },
                            "type": "array"
                        },
                        "includes": {
                            "description": "includes files",
                            "items": {
                                "$ref": "#/definitions/FileGroup"
                            },
                            "type": "array"
                        },
                        "sources": {
                            "description": "source files",
                            "items": {
                                "$ref": "#/definitions/FileGroup"
                            },
                            "type": "array"
                        }
                    },
                    "type": "object"
                },
                "FileGroup": {
                    "additionalProperties": False,
                    "anyOf": [
                        {"required": ["public"]},
                        {"required": ["private"]}
                    ],
                    "properties": {
                        "platform": {
                            "description": "target platform",
                            "enum": ["any", "windows", "apple", "linux", "posix"],
                            "type": "string"
                        },
                        "private": {
                            "description": "private files",
                            "items": {"type": "string"},
                            "type": "array"
                        },
                        "public": {
                            "description": "public files",
                            "items": {"type": "string"},
                            "type": "array"
                        }
                    },
                    "required": ["platform"],
                    "type": "object"
                }
            }
        }

        # Valid project.json
        project_json = {
            "core": {
                "description": "atlas core",
                "library": True,
                "install": True,
                "libraries": [
                    "std"
                ],
                "includes": [
                    {
                        "public": [
                            "defines.h"
                        ],
                        "platform": "any"
                    }
                ],
                "sources": [
                    {
                        "private": [
                            "strings.cpp"
                        ],
                        "platform": "any"
                    },
                    {
                        "private": [
                            "windows/wstrings.cpp"
                        ],
                        "platform": "windows"
                    }
                ]
            }
        }

        # Validate the project.json
        result = self.validator.validate(project_json, schema)
        assert result.valid
        assert not result.errors


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
