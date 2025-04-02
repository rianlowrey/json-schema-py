"""
Utility classes and functions for the Enhanced JSON Schema Validator.
"""

from typing import Any, Dict, List, Optional, Union, Tuple, Set


class JsonPointer:
    """
    Utility class for handling JSON Pointers (RFC 6901).
    
    JSON Pointers are used to reference specific locations within a JSON document.
    """
    
    @staticmethod
    def from_parts(parts: List[str]) -> str:
        """
        Create a JSON Pointer from path parts.
        
        Args:
            parts: List of path segments
            
        Returns:
            JSON Pointer string
        """
        if not parts:
            return ""
            
        return "/" + "/".join(JsonPointer.escape_part(part) for part in parts)
    
    @staticmethod
    def escape_part(part: str) -> str:
        """
        Escape a JSON Pointer path segment.
        
        Args:
            part: Path segment to escape
            
        Returns:
            Escaped path segment
        """
        # Replace ~ with ~0 and / with ~1
        return str(part).replace("~", "~0").replace("/", "~1")
    
    @staticmethod
    def unescape_part(part: str) -> str:
        """
        Unescape a JSON Pointer path segment.
        
        Args:
            part: Escaped path segment
            
        Returns:
            Unescaped path segment
        """
        # Replace ~1 with / and ~0 with ~
        return part.replace("~1", "/").replace("~0", "~")
    
    @staticmethod
    def to_parts(pointer: str) -> List[str]:
        """
        Split a JSON Pointer into its component parts.
        
        Args:
            pointer: JSON Pointer string
            
        Returns:
            List of path segments
        """
        if not pointer or pointer == "":
            return []
            
        if not pointer.startswith("/"):
            raise ValueError(f"Invalid JSON Pointer: {pointer}")
            
        # Skip the first character (/) and split on remaining /
        parts = pointer[1:].split("/")
        
        # Unescape each part
        return [JsonPointer.unescape_part(part) for part in parts]
    
    @staticmethod
    def resolve(document: Any, pointer: str) -> Any:
        """
        Resolve a JSON Pointer within a document.
        
        Args:
            document: The JSON document to navigate
            pointer: JSON Pointer string
            
        Returns:
            The referenced value
            
        Raises:
            ValueError: If the pointer cannot be resolved
        """
        if not pointer or pointer == "":
            return document
            
        parts = JsonPointer.to_parts(pointer)
        current = document
        
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    raise ValueError(f"Failed to resolve JSON Pointer: {pointer}, part '{part}' not found")
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if index < 0 or index >= len(current):
                        raise ValueError(f"Failed to resolve JSON Pointer: {pointer}, index {index} out of range")
                    current = current[index]
                except ValueError:
                    raise ValueError(f"Failed to resolve JSON Pointer: {pointer}, invalid array index '{part}'")
            else:
                raise ValueError(f"Failed to resolve JSON Pointer: {pointer}, cannot navigate into {type(current).__name__}")
                
        return current


class TypeUtils:
    """Utilities for working with JSON Schema types."""
    
    # Map from JSON Schema types to Python types
    TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None)
    }
    
    # Map of type relationships (type -> set of compatible types)
    TYPE_HIERARCHY = {
        "number": {"number", "integer"}
    }
    
    @staticmethod
    def get_python_type(schema_type: Union[str, List[str]]) -> Tuple[type, ...]:
        """
        Get the Python type(s) corresponding to a JSON Schema type.
        
        Args:
            schema_type: JSON Schema type name or list of type names
            
        Returns:
            Tuple of Python types
        """
        if isinstance(schema_type, list):
            # For multiple types, combine all corresponding Python types
            result = []
            for t in schema_type:
                if t in TypeUtils.TYPE_MAP:
                    type_obj = TypeUtils.TYPE_MAP[t]
                    if isinstance(type_obj, tuple):
                        result.extend(type_obj)
                    else:
                        result.append(type_obj)
            return tuple(result)
        else:
            # For single type, return the corresponding Python type
            if schema_type in TypeUtils.TYPE_MAP:
                type_obj = TypeUtils.TYPE_MAP[schema_type]
                if isinstance(type_obj, tuple):
                    return type_obj
                else:
                    return (type_obj,)
        
        return tuple()
    
    @staticmethod
    def get_json_type(value: Any) -> str:
        """
        Get the JSON Schema type for a Python value.
        
        Args:
            value: Python value
            
        Returns:
            JSON Schema type name
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            # Best effort for custom types
            return "unknown"
    
    @staticmethod
    def get_compatible_types(schema_type: str) -> Set[str]:
        """
        Get all types that are compatible with the given JSON Schema type.
        
        For example, a value of type "integer" is also compatible with "number"
        according to the JSON Schema specification.
        
        Args:
            schema_type: JSON Schema type name
            
        Returns:
            Set of compatible JSON Schema type names, including the original type
        """
        compatible_types = {schema_type}
        
        # Check if this type is in the hierarchy map as a value
        for parent_type, subtypes in TypeUtils.TYPE_HIERARCHY.items():
            if schema_type in subtypes:
                compatible_types.add(parent_type)
        
        return compatible_types
    
    @staticmethod
    def get_effective_types(types: Union[str, List[str], Set[str]]) -> Set[str]:
        """
        Get all effective types for a set of JSON Schema types, including any subtypes.
        
        Args:
            types: JSON Schema type name or list/set of type names
            
        Returns:
            Set of JSON Schema type names effectively included by these types
        """
        if isinstance(types, str):
            types = {types}
        elif isinstance(types, list):
            types = set(types)
        
        effective_types = set(types)
        
        # Add subtypes based on the JSON Schema type hierarchy
        for t in list(effective_types):  # Make a copy to avoid modification during iteration
            if t in TypeUtils.TYPE_HIERARCHY:
                effective_types.update(TypeUtils.TYPE_HIERARCHY[t])
        
        return effective_types


class SchemaKeywords:
    """Constants for JSON Schema keywords."""
    
    # Type keywords
    TYPE = "type"
    
    # Number keywords
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    EXCLUSIVE_MINIMUM = "exclusiveMinimum"
    EXCLUSIVE_MAXIMUM = "exclusiveMaximum"
    MULTIPLE_OF = "multipleOf"
    
    # String keywords
    MIN_LENGTH = "minLength"
    MAX_LENGTH = "maxLength"
    PATTERN = "pattern"
    FORMAT = "format"
    
    # Array keywords
    ITEMS = "items"
    ADDITIONAL_ITEMS = "additionalItems"
    MIN_ITEMS = "minItems"
    MAX_ITEMS = "maxItems"
    UNIQUE_ITEMS = "uniqueItems"
    CONTAINS = "contains"
    
    # Object keywords
    PROPERTIES = "properties"
    PATTERN_PROPERTIES = "patternProperties"
    ADDITIONAL_PROPERTIES = "additionalProperties"
    REQUIRED = "required"
    PROPERTY_NAMES = "propertyNames"
    MIN_PROPERTIES = "minProperties"
    MAX_PROPERTIES = "maxProperties"
    DEPENDENCIES = "dependencies"
    
    # Schema composition
    ALL_OF = "allOf"
    ANY_OF = "anyOf"
    ONE_OF = "oneOf"
    NOT = "not"
    
    # Miscellaneous
    ENUM = "enum"
    CONST = "const"
    
    # References
    REF = "$ref"
    
    # Schema metadata
    ID = "$id"
    SCHEMA = "$schema"
    TITLE = "title"
    DESCRIPTION = "description"
    DEFAULT = "default"
    EXAMPLES = "examples"
    
    # Draft 2019-09 keywords
    THEN = "then"
    ELSE = "else"
    IF = "if"
    
    @staticmethod
    def is_type_specific_keyword(keyword: str) -> bool:
        """
        Check if a keyword is type-specific.
        
        Args:
            keyword: Schema keyword
            
        Returns:
            True if the keyword applies to a specific type
        """
        # Number keywords
        if keyword in {
            SchemaKeywords.MINIMUM,
            SchemaKeywords.MAXIMUM,
            SchemaKeywords.EXCLUSIVE_MINIMUM,
            SchemaKeywords.EXCLUSIVE_MAXIMUM,
            SchemaKeywords.MULTIPLE_OF
        }:
            return True
            
        # String keywords
        if keyword in {
            SchemaKeywords.MIN_LENGTH,
            SchemaKeywords.MAX_LENGTH,
            SchemaKeywords.PATTERN,
            SchemaKeywords.FORMAT
        }:
            return True
            
        # Array keywords
        if keyword in {
            SchemaKeywords.ITEMS,
            SchemaKeywords.ADDITIONAL_ITEMS,
            SchemaKeywords.MIN_ITEMS,
            SchemaKeywords.MAX_ITEMS,
            SchemaKeywords.UNIQUE_ITEMS,
            SchemaKeywords.CONTAINS
        }:
            return True
            
        # Object keywords
        if keyword in {
            SchemaKeywords.PROPERTIES,
            SchemaKeywords.PATTERN_PROPERTIES,
            SchemaKeywords.ADDITIONAL_PROPERTIES,
            SchemaKeywords.REQUIRED,
            SchemaKeywords.PROPERTY_NAMES,
            SchemaKeywords.MIN_PROPERTIES,
            SchemaKeywords.MAX_PROPERTIES,
            SchemaKeywords.DEPENDENCIES
        }:
            return True
            
        return False
    
    @staticmethod
    def get_implied_type(keyword: str) -> Optional[str]:
        """
        Get the type implied by a schema keyword.
        
        Args:
            keyword: Schema keyword
            
        Returns:
            Implied type, or None if the keyword doesn't imply a type
        """
        # Number keywords
        if keyword in {
            SchemaKeywords.MINIMUM,
            SchemaKeywords.MAXIMUM,
            SchemaKeywords.EXCLUSIVE_MINIMUM,
            SchemaKeywords.EXCLUSIVE_MAXIMUM,
            SchemaKeywords.MULTIPLE_OF
        }:
            return "number"
            
        # String keywords
        if keyword in {
            SchemaKeywords.MIN_LENGTH,
            SchemaKeywords.MAX_LENGTH,
            SchemaKeywords.PATTERN,
            SchemaKeywords.FORMAT
        }:
            return "string"
            
        # Array keywords
        if keyword in {
            SchemaKeywords.ITEMS,
            SchemaKeywords.ADDITIONAL_ITEMS,
            SchemaKeywords.MIN_ITEMS,
            SchemaKeywords.MAX_ITEMS,
            SchemaKeywords.UNIQUE_ITEMS,
            SchemaKeywords.CONTAINS
        }:
            return "array"
            
        # Object keywords
        if keyword in {
            SchemaKeywords.PROPERTIES,
            SchemaKeywords.PATTERN_PROPERTIES,
            SchemaKeywords.ADDITIONAL_PROPERTIES,
            SchemaKeywords.REQUIRED,
            SchemaKeywords.PROPERTY_NAMES,
            SchemaKeywords.MIN_PROPERTIES,
            SchemaKeywords.MAX_PROPERTIES,
            SchemaKeywords.DEPENDENCIES
        }:
            return "object"
            
        return None