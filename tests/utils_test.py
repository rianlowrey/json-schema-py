#!/usr/bin/env python3
"""
Tests for utility classes and functions.
"""
import pytest

# autopep8: off
from utils import setup
setup()
from json_schema import JsonPointer
from json_schema.utils import TypeUtils
from json_schema.schema_compiler import SchemaKeywords
# autopep8: on


class TestJsonPointer:
    """Tests for JsonPointer class."""

    def test_from_parts(self):
        """Test creating a JSON Pointer from path parts."""
        assert JsonPointer.from_parts([]) == ""
        assert JsonPointer.from_parts(["foo"]) == "/foo"
        assert JsonPointer.from_parts(["foo", "bar"]) == "/foo/bar"
        assert JsonPointer.from_parts(["foo", "bar", "0"]) == "/foo/bar/0"

    def test_escape_part(self):
        """Test escaping path parts."""
        assert JsonPointer.escape_part("foo") == "foo"
        assert JsonPointer.escape_part("foo/bar") == "foo~1bar"
        assert JsonPointer.escape_part("foo~bar") == "foo~0bar"
        assert JsonPointer.escape_part("foo/bar~baz") == "foo~1bar~0baz"

    def test_unescape_part(self):
        """Test unescaping path parts."""
        assert JsonPointer.unescape_part("foo") == "foo"
        assert JsonPointer.unescape_part("foo~1bar") == "foo/bar"
        assert JsonPointer.unescape_part("foo~0bar") == "foo~bar"
        assert JsonPointer.unescape_part("foo~1bar~0baz") == "foo/bar~baz"

    def test_to_parts(self):
        """Test splitting a JSON Pointer into parts."""
        assert JsonPointer.to_parts("") == []
        assert JsonPointer.to_parts("/foo") == ["foo"]
        assert JsonPointer.to_parts("/foo/bar") == ["foo", "bar"]
        assert JsonPointer.to_parts("/foo/bar/0") == ["foo", "bar", "0"]
        assert JsonPointer.to_parts("/foo~1bar/baz") == ["foo/bar", "baz"]
        assert JsonPointer.to_parts("/foo~0bar/baz") == ["foo~bar", "baz"]

        # Test invalid pointer
        with pytest.raises(ValueError):
            JsonPointer.to_parts("foo/bar")

    def test_resolve(self):
        """Test resolving a JSON Pointer within a document."""
        document = {
            "foo": {
                "bar": [1, 2, 3],
                "baz": "value"
            },
            "qux": 42,
            "with/slash": "slash value",
            "with~tilde": "tilde value"
        }

        # Empty pointer should return the document
        assert JsonPointer.resolve(document, "") is document

        # Basic resolution
        assert JsonPointer.resolve(document, "/foo") == document["foo"]
        assert JsonPointer.resolve(
            document, "/foo/bar") == document["foo"]["bar"]
        assert JsonPointer.resolve(
            document, "/foo/baz") == document["foo"]["baz"]
        assert JsonPointer.resolve(document, "/qux") == document["qux"]

        # Array indexing
        assert JsonPointer.resolve(
            document, "/foo/bar/0") == document["foo"]["bar"][0]
        assert JsonPointer.resolve(
            document, "/foo/bar/1") == document["foo"]["bar"][1]
        assert JsonPointer.resolve(
            document, "/foo/bar/2") == document["foo"]["bar"][2]

        # Escaped characters
        assert JsonPointer.resolve(
            document, "/with~1slash") == document["with/slash"]
        assert JsonPointer.resolve(
            document, "/with~0tilde") == document["with~tilde"]

        # Invalid pointers
        with pytest.raises(ValueError):
            JsonPointer.resolve(document, "/nonexistent")

        with pytest.raises(ValueError):
            JsonPointer.resolve(document, "/foo/bar/3")  # Out of range

        with pytest.raises(ValueError):
            JsonPointer.resolve(document, "/foo/bar/invalid")  # Not an integer

        with pytest.raises(ValueError):
            # Cannot navigate into string
            JsonPointer.resolve(document, "/foo/baz/subpath")


class TestTypeUtils:
    """Tests for TypeUtils class."""

    def test_get_python_type(self):
        """Test getting Python types from JSON Schema types."""
        # Single types
        assert TypeUtils.get_python_type("string") == (str,)
        assert TypeUtils.get_python_type("integer") == (int,)
        assert TypeUtils.get_python_type("number") == (int, float)
        assert TypeUtils.get_python_type("boolean") == (bool,)
        assert TypeUtils.get_python_type("array") == (list,)
        assert TypeUtils.get_python_type("object") == (dict,)
        assert TypeUtils.get_python_type("null") == (type(None),)

        # Multiple types
        assert TypeUtils.get_python_type(
            ["string", "null"]) == (str, type(None))
        assert TypeUtils.get_python_type(
            ["integer", "number"]) == (int, int, float)

        # Invalid type
        assert TypeUtils.get_python_type("invalid") == tuple()

    def test_get_json_type(self):
        """Test getting JSON Schema types from Python values."""
        assert TypeUtils.get_json_type(None) == "null"
        assert TypeUtils.get_json_type(True) == "boolean"
        assert TypeUtils.get_json_type(False) == "boolean"
        assert TypeUtils.get_json_type(42) == "integer"
        assert TypeUtils.get_json_type(3.14) == "number"
        assert TypeUtils.get_json_type("hello") == "string"
        assert TypeUtils.get_json_type([1, 2, 3]) == "array"
        assert TypeUtils.get_json_type({"foo": "bar"}) == "object"

        # Custom types
        class CustomClass:
            pass

        assert TypeUtils.get_json_type(CustomClass()) == "unknown"


class TestSchemaKeywords:
    """Tests for SchemaKeywords class."""

    def test_is_type_specific_keyword(self):
        """Test checking if a keyword is type-specific."""
        # Number keywords
        assert SchemaKeywords.is_type_specific_keyword("minimum")
        assert SchemaKeywords.is_type_specific_keyword("maximum")
        assert SchemaKeywords.is_type_specific_keyword("exclusiveMinimum")
        assert SchemaKeywords.is_type_specific_keyword("exclusiveMaximum")
        assert SchemaKeywords.is_type_specific_keyword("multipleOf")

        # String keywords
        assert SchemaKeywords.is_type_specific_keyword("minLength")
        assert SchemaKeywords.is_type_specific_keyword("maxLength")
        assert SchemaKeywords.is_type_specific_keyword("pattern")
        assert SchemaKeywords.is_type_specific_keyword("format")

        # Array keywords
        assert SchemaKeywords.is_type_specific_keyword("items")
        assert SchemaKeywords.is_type_specific_keyword("minItems")
        assert SchemaKeywords.is_type_specific_keyword("maxItems")
        assert SchemaKeywords.is_type_specific_keyword("uniqueItems")

        # Object keywords
        assert SchemaKeywords.is_type_specific_keyword("properties")
        assert SchemaKeywords.is_type_specific_keyword("required")
        assert SchemaKeywords.is_type_specific_keyword("additionalProperties")
        assert SchemaKeywords.is_type_specific_keyword("propertyNames")

        # Non-type-specific keywords
        assert not SchemaKeywords.is_type_specific_keyword("type")
        assert not SchemaKeywords.is_type_specific_keyword("enum")
        assert not SchemaKeywords.is_type_specific_keyword("const")
        assert not SchemaKeywords.is_type_specific_keyword("allOf")
        assert not SchemaKeywords.is_type_specific_keyword("anyOf")
        assert not SchemaKeywords.is_type_specific_keyword("oneOf")
        assert not SchemaKeywords.is_type_specific_keyword("not")

    def test_get_implied_type(self):
        """Test getting the type implied by a schema keyword."""
        # Number keywords
        assert SchemaKeywords.get_implied_type("minimum") == "number"
        assert SchemaKeywords.get_implied_type("maximum") == "number"
        assert SchemaKeywords.get_implied_type("exclusiveMinimum") == "number"
        assert SchemaKeywords.get_implied_type("exclusiveMaximum") == "number"
        assert SchemaKeywords.get_implied_type("multipleOf") == "number"

        # String keywords
        assert SchemaKeywords.get_implied_type("minLength") == "string"
        assert SchemaKeywords.get_implied_type("maxLength") == "string"
        assert SchemaKeywords.get_implied_type("pattern") == "string"
        assert SchemaKeywords.get_implied_type("format") == "string"

        # Array keywords
        assert SchemaKeywords.get_implied_type("items") == "array"
        assert SchemaKeywords.get_implied_type("minItems") == "array"
        assert SchemaKeywords.get_implied_type("maxItems") == "array"
        assert SchemaKeywords.get_implied_type("uniqueItems") == "array"

        # Object keywords
        assert SchemaKeywords.get_implied_type("properties") == "object"
        assert SchemaKeywords.get_implied_type("required") == "object"
        assert SchemaKeywords.get_implied_type(
            "additionalProperties") == "object"
        assert SchemaKeywords.get_implied_type("propertyNames") == "object"

        # Non-type-specific keywords
        assert SchemaKeywords.get_implied_type("type") is None
        assert SchemaKeywords.get_implied_type("enum") is None
        assert SchemaKeywords.get_implied_type("const") is None
        assert SchemaKeywords.get_implied_type("allOf") is None
        assert SchemaKeywords.get_implied_type("anyOf") is None
        assert SchemaKeywords.get_implied_type("oneOf") is None
        assert SchemaKeywords.get_implied_type("not") is None


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
