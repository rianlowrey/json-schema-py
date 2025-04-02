#!/usr/bin/env python3
"""
Tests for the main CLI script.
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest import mock

# autopep8: off
from utils import setup
setup()
from json_schema.cli import main, load_json
# autopep8: on


@pytest.fixture
def valid_schema():
    """Create a valid schema for testing."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Test Schema",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        },
        "required": ["name"],
        "additionalProperties": False
    }


@pytest.fixture
def valid_data():
    """Create valid data for testing."""
    return {
        "name": "John Doe",
        "age": 30
    }


@pytest.fixture
def invalid_data():
    """Create invalid data for testing."""
    return {
        "name": 123,  # Wrong type
        "age": -5     # Below minimum
    }


@pytest.fixture
def temp_files(valid_schema, valid_data, invalid_data):
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Create schema file
        schema_file = temp_dir_path / "schema.json"
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(valid_schema, f)

        # Create valid data file
        valid_data_file = temp_dir_path / "valid_data.json"
        with open(valid_data_file, "w", encoding="utf-8") as f:
            json.dump(valid_data, f)

        # Create invalid data file
        invalid_data_file = temp_dir_path / "invalid_data.json"
        with open(invalid_data_file, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)

        # Create a file with invalid JSON
        invalid_json_file = temp_dir_path / "invalid_json.json"
        with open(invalid_json_file, "w", encoding="utf-8") as f:
            f.write("{invalid json")

        yield {
            "temp_dir": temp_dir_path,
            "schema_file": schema_file,
            "valid_data_file": valid_data_file,
            "invalid_data_file": invalid_data_file,
            "invalid_json_file": invalid_json_file
        }


def test_load_json_valid(temp_files):
    """Test loading a valid JSON file."""
    data = load_json(temp_files["valid_data_file"])
    assert isinstance(data, dict)
    assert "name" in data
    assert data["name"] == "John Doe"


def test_load_json_file_not_found():
    """Test loading a non-existent JSON file."""
    with pytest.raises(FileNotFoundError):
        load_json("non_existent.json")


def test_load_json_invalid_json(temp_files):
    """Test loading a file with invalid JSON."""
    with pytest.raises(json.JSONDecodeError):
        load_json(temp_files["invalid_json_file"])


def test_main_valid_data(temp_files):
    """Test main function with valid data."""
    with mock.patch("sys.argv", ["enhanced_validator_main.py",
                                 str(temp_files["valid_data_file"]),
                                 str(temp_files["schema_file"])]):
        exit_code = main()
    assert exit_code == 0


def test_main_invalid_data(temp_files):
    """Test main function with invalid data."""
    with mock.patch("sys.argv", ["enhanced_validator_main.py",
                                 str(temp_files["invalid_data_file"]),
                                 str(temp_files["schema_file"])]):
        exit_code = main()
    assert exit_code == 1


def test_main_invalid_json(temp_files):
    """Test main function with invalid JSON."""
    with mock.patch("sys.argv", ["enhanced_validator_main.py",
                                 str(temp_files["invalid_json_file"]),
                                 str(temp_files["schema_file"])]):
        exit_code = main()
    assert exit_code == 1


def test_main_file_not_found(temp_files):
    """Test main function with non-existent file."""
    with mock.patch("sys.argv", ["enhanced_validator_main.py",
                                 "non_existent.json",
                                 str(temp_files["schema_file"])]):
        exit_code = main()
    assert exit_code == 1


def test_main_schema_not_found(temp_files):
    """Test main function with non-existent schema file."""
    with mock.patch("sys.argv", ["enhanced_validator_main.py",
                                 str(temp_files["valid_data_file"]),
                                 "non_existent.json"]):
        exit_code = main()
    assert exit_code == 1


def test_main_verbose(temp_files):
    """Test main function with verbose flag."""
    with mock.patch("sys.argv", ["enhanced_validator_main.py",
                                 str(temp_files["valid_data_file"]),
                                 str(temp_files["schema_file"]),
                                 "--verbose"]):
        exit_code = main()
    assert exit_code == 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
