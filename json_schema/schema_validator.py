#!/usr/bin/env python3
"""
JSON Configuration Validator

This script validates JSON configuration files against a provided JSON schema,
with additional custom validation rules for project configuration files.

Usage:
    python json_schema.py <data_file> <schema_file> [--check-files] [--verbose]
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set, Tuple, Iterator

__version__ = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger("json_schema")


class JsonSchemaValidator:
    """JSON Schema validator with no external dependencies."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the JSON Schema validator.

        Args:
            verbose: If True, log additional details during validation
        """
        self.verbose = verbose
        if verbose:
            logger.setLevel(logging.DEBUG)

    def _resolve_reference(self, ref: str, root_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve a JSON Schema reference.

        Args:
            ref: The reference string (e.g., "#/definitions/Project")
            root_schema: The root schema document

        Returns:
            The resolved schema object

        Raises:
            ValueError: If reference resolution fails
        """
        if not ref.startswith("#/"):
            raise ValueError(f"External references not supported: {ref}")

        # Strip the '#/' prefix and split into path components
        path_parts = ref[2:].split("/")

        # Navigate the schema
        current = root_schema
        for part in path_parts:
            # Handle JSON Pointer escaping
            part = part.replace("~1", "/").replace("~0", "~")

            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ValueError(
                    f"Failed to resolve reference path component '{part}' in {ref}")

        return current

    def _infer_schema_type(self, schema: Dict[str, Any], value: Any) -> Optional[str]:
        """
        Infer the schema type based on constraints and value.
        
        Args:
            schema: The schema to analyze
            value: The value being validated
            
        Returns:
            The inferred type as a string, or None if no type can be determined
        """
        # Check explicit type first
        if "type" in schema:
            return schema["type"]
        
        # Infer type from constraints
        if any(key in schema for key in ["minimum", "maximum", "multipleOf"]):
            # For boolean values, don't infer number type even with number constraints
            if isinstance(value, bool):
                return None
            return "number" if isinstance(value, float) else "integer"
            
        if any(key in schema for key in ["minLength", "maxLength", "pattern"]):
            return "string"
            
        if any(key in schema for key in ["items", "minItems", "maxItems", "uniqueItems"]):
            return "array"
            
        if any(key in schema for key in ["properties", "required", "additionalProperties", 
                                        "patternProperties", "propertyNames", "minProperties",
                                        "maxProperties", "dependencies"]):
            return "object"
            
        return None

    def _has_constraints_for_type(self, schema: Dict[str, Any], type_name: str) -> bool:
        """
        Check if the schema has constraints specific to the given type.
        
        Args:
            schema: The schema to analyze
            type_name: The type to check constraints for
            
        Returns:
            True if the schema has constraints for the specified type
        """
        if type_name == "string":
            return any(key in schema for key in ["minLength", "maxLength", "pattern"])
        elif type_name in ["number", "integer"]:
            return any(key in schema for key in ["minimum", "maximum", "multipleOf"])
        elif type_name == "array":
            return any(key in schema for key in ["items", "minItems", "maxItems", "uniqueItems"])
        elif type_name == "object":
            return any(key in schema for key in ["properties", "required", "additionalProperties", 
                                                "patternProperties", "propertyNames", "minProperties",
                                                "maxProperties", "dependencies"])
        return False

    def _validate_type(self, value: Any, schema_type: Union[str, List[str]], path: str) -> List[str]:
        """
        Validate value against expected type(s).

        Args:
            value: The value to validate
            schema_type: Expected type or list of types
            path: JSON path for error reporting

        Returns:
            List of validation errors
        """
        errors = []
        types = [schema_type] if isinstance(schema_type, str) else schema_type

        # Map JSON Schema types to Python types
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }

        # Check if value matches any of the expected types
        valid = False
        for t in types:
            if t in type_map:
                expected_type = type_map[t]

                # Special case for "number" which can be int or float
                if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    valid = True
                    break
                elif isinstance(value, expected_type) and not (t != "boolean" and isinstance(value, bool)):
                    # This check handles the case where bool is a subclass of int
                    # so a boolean would incorrectly match "integer" or "number"
                    valid = True
                    break
            else:
                logger.warning(f"Unknown type '{t}' in schema at '{path}'")

        if not valid:
            type_names = ", ".join(types)
            errors.append(
                f"Error at '{path}': Expected {type_names}, got {type(value).__name__}")

        return errors

    def _validate_any_of(self, value: Any, schemas: List[Dict[str, Any]], path: str, root_schema: Dict[str, Any]) -> List[str]:
        """
        Validate against anyOf schema with improved type context preservation.

        Args:
            value: The value to validate
            schemas: List of possible schemas
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors if value doesn't match any schema
        """
        matched = False
        all_schemas_errors = []
        value_type = None  # Inferred type from value

        # Try to infer type from the value to improve context preservation
        if isinstance(value, str):
            value_type = "string"
        elif isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int):
            value_type = "integer"
        elif isinstance(value, float):
            value_type = "number"
        elif isinstance(value, list):
            value_type = "array"
        elif isinstance(value, dict):
            value_type = "object"
        elif value is None:
            value_type = "null"

        for i, schema in enumerate(schemas):
            # For schemas without a type but with type-specific constraints, 
            # add the inferred type if we have one and if it would be relevant
            schema_to_validate = schema
            if "type" not in schema and value_type and self._has_constraints_for_type(schema, value_type):
                # Create a copy to avoid modifying the original schema
                schema_to_validate = schema.copy()
                schema_to_validate["type"] = value_type

            sub_errors = self._validate_against_schema(
                value, schema_to_validate, path, root_schema)

            # If no errors for this schema, it's a match
            if not sub_errors:
                matched = True
                break
            else:
                # Collect errors from this schema for better error reporting
                all_schemas_errors.append((i, sub_errors))

        if matched:
            return []
        else:
            # Provide more detailed error message
            error_details = ""
            for i, errors in all_schemas_errors:
                error_details += f"\n  - Schema[{i}]: {errors[0] if errors else 'Unknown error'}"

            return [f"Error at '{path}': Value {value} (type: {type(value).__name__}) " +
                    f"doesn't match any of the required schemas in anyOf.{error_details}"]

    def _validate_all_of(self, value: Any, schemas: List[Dict[str, Any]], path: str, root_schema: Dict[str, Any]) -> List[str]:
        """
        Validate against allOf schema with improved type context preservation.
        
        Args:
            value: The value to validate
            schemas: List of schemas that all must match
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors
        """
        errors = []
        
        # Step 1: Pre-process schemas to check if there's a type declaration
        value_type = None
        for schema in schemas:
            if "type" in schema:
                value_type = schema["type"]
                break
                
        # If no explicit type, try to infer from the value
        if not value_type:
            if isinstance(value, str):
                value_type = "string"
            elif isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, int):
                value_type = "integer"
            elif isinstance(value, float):
                value_type = "number"
            elif isinstance(value, list):
                value_type = "array"
            elif isinstance(value, dict):
                value_type = "object"
            elif value is None:
                value_type = "null"
        
        # Step 2: Validate against each schema, preserving type context
        for i, schema in enumerate(schemas):
            # For schemas without a type but with type-specific constraints, 
            # add the inferred type if we have one
            schema_to_validate = schema
            if "type" not in schema and value_type and self._has_constraints_for_type(schema, value_type):
                # Create a copy to avoid modifying the original schema
                schema_to_validate = schema.copy()
                schema_to_validate["type"] = value_type
            
            sub_errors = self._validate_against_schema(value, schema_to_validate, path, root_schema)
            if sub_errors:
                if len(sub_errors) == 1:
                    # For single errors, include it directly for better readability
                    errors.append(f"Error at '{path}' (allOf[{i}]): {sub_errors[0].split(':', 1)[1].strip()}")
                else:
                    # For multiple errors, summarize
                    errors.append(f"Error at '{path}' (allOf[{i}]): Value {value} (type: {type(value).__name__}) " +
                                f"failed to validate: {', '.join(sub_errors)}")
        
        return errors

    def _validate_one_of(self, value: Any, schemas: List[Dict[str, Any]], path: str, root_schema: Dict[str, Any]) -> List[str]:
        """
        Validate against oneOf schema with improved type context preservation.

        Args:
            value: The value to validate
            schemas: List of possible schemas
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors if value doesn't match exactly one schema
        """
        valid_count = 0
        valid_indices = []
        schema_errors = []
        value_type = None  # Inferred type from value

        # Try to infer type from the value to improve context preservation
        if isinstance(value, str):
            value_type = "string"
        elif isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int):
            value_type = "integer"
        elif isinstance(value, float):
            value_type = "number"
        elif isinstance(value, list):
            value_type = "array"
        elif isinstance(value, dict):
            value_type = "object"
        elif value is None:
            value_type = "null"

        for i, schema in enumerate(schemas):
            # For schemas without a type but with type-specific constraints, 
            # add the inferred type if we have one and if it would be relevant
            schema_to_validate = schema
            if "type" not in schema and value_type and self._has_constraints_for_type(schema, value_type):
                # Create a copy to avoid modifying the original schema
                schema_to_validate = schema.copy()
                schema_to_validate["type"] = value_type

            sub_errors = self._validate_against_schema(
                value, schema_to_validate, path, root_schema)
            if not sub_errors:
                valid_count += 1
                valid_indices.append(i)
            else:
                # Store the errors for each schema for better error reporting
                schema_errors.append((i, sub_errors))

        if valid_count == 0:
            # Provide more detailed error message about why none of the schemas matched
            error_details = ""
            for i, errors in schema_errors:
                error_details += f"\n  - Schema[{i}]: {errors[0] if errors else 'Unknown error'}"

            return [f"Error at '{path}': Value {value} (type: {type(value).__name__}) " +
                    f"doesn't match any of the required schemas in oneOf.{error_details}"]
        elif valid_count > 1:
            return [f"Error at '{path}': Value {value} (type: {type(value).__name__}) " +
                    f"matches {valid_count} schemas (indices: {valid_indices}), but should match exactly one"]
        else:
            return []

    def _validate_against_schema(self, value: Any, schema: Dict[str, Any], path: str, root_schema: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Validate a value against a schema with enhanced type handling.

        Args:
            value: The value to validate
            schema: The schema to validate against
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors
        """
        errors = []
        
        # Use the current schema as the root schema if none is provided
        if root_schema is None:
            root_schema = schema
        
        # Handle $ref resolution first
        if "$ref" in schema:
            ref = schema["$ref"]
            try:
                resolved_schema = self._resolve_reference(ref, root_schema)
                return self._validate_against_schema(value, resolved_schema, path, root_schema)
            except ValueError as e:
                errors.append(f"Error at '{path}': {str(e)}")
                return errors
        
        # Process logical operators
        if "allOf" in schema:
            errors.extend(self._validate_all_of(value, schema["allOf"], path, root_schema))
            # If we have errors from allOf, return them immediately to avoid duplicate errors
            if errors:
                return errors
        
        if "anyOf" in schema:
            errors.extend(self._validate_any_of(value, schema["anyOf"], path, root_schema))
            # If we have errors from anyOf, return them immediately to avoid duplicate errors
            if errors:
                return errors

        if "oneOf" in schema:
            errors.extend(self._validate_one_of(value, schema["oneOf"], path, root_schema))
            # If we have errors from oneOf, return them immediately to avoid duplicate errors
            if errors:
                return errors
        
        if "not" in schema:
            not_errors = self._validate_against_schema(value, schema["not"], path, root_schema)
            if not not_errors:
                errors.append(f"Error at '{path}': Value {value} (type: {type(value).__name__}) " +
                              "should not validate against 'not' schema, but it did")
            # If we have errors from not, return them immediately
            if errors:
                return errors
        
        # Infer the type if not explicitly specified
        inferred_type = self._infer_schema_type(schema, value)
        
        # Validate type if specified or inferred
        if "type" in schema or inferred_type:
            type_to_check = schema.get("type", inferred_type)
            type_errors = self._validate_type(value, type_to_check, path)
            errors.extend(type_errors)
            
            # If type validation failed, skip type-specific validations
            if type_errors:
                return errors
        
        # Now handle type-specific validations
        # We'll use the actual type of the value plus any inferred type
        # to determine which validations to apply
        
        # String validations
        if ((schema.get("type") == "string" or inferred_type == "string") and 
                isinstance(value, str)):
            errors.extend(self._validate_string(value, schema, path))
            
        # Number validations
        elif ((schema.get("type") in ["number", "integer"] or inferred_type in ["number", "integer"]) and 
                isinstance(value, (int, float)) and not isinstance(value, bool)):
            errors.extend(self._validate_number(value, schema, path))
        
        # Array validations
        elif ((schema.get("type") == "array" or inferred_type == "array") and 
                isinstance(value, list)):
            errors.extend(self._validate_array(value, schema, path, root_schema))
        
        # Object validations
        elif ((schema.get("type") == "object" or inferred_type == "object") and 
                isinstance(value, dict)):
            errors.extend(self._validate_object(value, schema, path, root_schema))
        
        # Special case: Apply validations based on presence of constraints
        # even if type doesn't match (only if no explicit type is specified)
        elif "type" not in schema:
            # Apply number constraints to numeric values
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if any(key in schema for key in ["minimum", "maximum", "multipleOf"]):
                    errors.extend(self._validate_number(value, schema, path))
            
            # Apply string constraints to string values
            elif isinstance(value, str):
                if any(key in schema for key in ["minLength", "maxLength", "pattern"]):
                    errors.extend(self._validate_string(value, schema, path))
            
            # Apply array constraints to array values
            elif isinstance(value, list):
                if any(key in schema for key in ["items", "minItems", "maxItems", "uniqueItems"]):
                    errors.extend(self._validate_array(value, schema, path, root_schema))
            
            # Apply object constraints to object values
            elif isinstance(value, dict):
                if any(key in schema for key in ["properties", "required", "additionalProperties", 
                                             "patternProperties", "propertyNames", "minProperties",
                                             "maxProperties", "dependencies"]):
                    errors.extend(self._validate_object(value, schema, path, root_schema))
        
        # Validate enum and const regardless of type
        if "enum" in schema:
            enum_errors = self._validate_enum(value, schema["enum"], path)
            errors.extend(enum_errors)
        
        if "const" in schema and value != schema["const"]:
            errors.append(
                f"Error at '{path}': Expected constant value {schema['const']}, got {value}")
        
        return errors

    def validate(self, data: Any, schema: Dict[str, Any]) -> List[str]:
        """
        Validate data against a JSON schema.

        Args:
            data: The data to validate
            schema: The JSON schema

        Returns:
            List of validation errors
        """
        return self._validate_against_schema(data, schema, "")

    def _validate_enum(self, value: Any, enum_values: List[Any], path: str) -> List[str]:
        """
        Validate value against enumeration.

        Args:
            value: The value to validate
            enum_values: List of valid values
            path: JSON path for error reporting

        Returns:
            List of validation errors
        """
        errors = []
        if value not in enum_values:
            errors.append(
                f"Error at '{path}': Value '{value}' not in enumeration {enum_values}")
        return errors

    def _validate_string(self, value: str, schema: Dict[str, Any], path: str) -> List[str]:
        """
        Validate string-specific constraints.
        
        Args:
            value: The string to validate
            schema: The schema containing string constraints
            path: JSON path for error reporting
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate minLength
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(
                f"Error at '{path}': String length is {len(value)}, but minimum is {schema['minLength']}"
            )

        # Validate maxLength
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(
                f"Error at '{path}': String length is {len(value)}, but maximum is {schema['maxLength']}"
            )

        # Validate pattern
        if "pattern" in schema:
            try:
                pattern = schema["pattern"]
                if not re.match(pattern, value):
                    errors.append(
                        f"Error at '{path}': String '{value}' does not match pattern '{pattern}'"
                    )
            except re.error as e:
                errors.append(f"Error at '{path}': Invalid regex pattern '{schema['pattern']}': {str(e)}")
        
        return errors

    def _validate_number(self, value: Union[int, float], schema: Dict[str, Any], path: str) -> List[str]:
        """
        Validate number-specific constraints.
        
        Args:
            value: The number to validate
            schema: The schema containing number constraints
            path: JSON path for error reporting
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate minimum
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(
                f"Error at '{path}': Value is {value}, but minimum is {schema['minimum']}"
            )

        # Validate maximum
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(
                f"Error at '{path}': Value is {value}, but maximum is {schema['maximum']}"
            )

        # Validate multipleOf
        if "multipleOf" in schema:
            multiple = schema["multipleOf"]
            # Handle floating point precision issues
            if isinstance(value, float) or isinstance(multiple, float):
                # For floating point, we need to consider precision
                remainder = value % multiple
                is_multiple = remainder < 1e-10 or abs(remainder - multiple) < 1e-10
            else:
                is_multiple = value % multiple == 0
                
            if not is_multiple:
                errors.append(
                    f"Error at '{path}': Value {value} is not a multiple of {multiple}"
                )
        
        return errors

    def _validate_array(self, array: List[Any], schema: Dict[str, Any], path: str, root_schema: Dict[str, Any]) -> List[str]:
        """
        Validate array.

        Args:
            array: The array to validate
            schema: Schema for the array
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors
        """
        errors = []

        # Validate minItems
        if "minItems" in schema and len(array) < schema["minItems"]:
            errors.append(
                f"Error at '{path}': Array has {len(array)} items, but minimum is {schema['minItems']}"
            )

        # Validate maxItems
        if "maxItems" in schema and len(array) > schema["maxItems"]:
            errors.append(
                f"Error at '{path}': Array has {len(array)} items, but maximum is {schema['maxItems']}"
            )

        # Validate uniqueItems
        if schema.get("uniqueItems", False):
            # Convert items to JSON strings for comparison
            try:
                unique_items = set()
                for i, item in enumerate(array):
                    item_str = json.dumps(item, sort_keys=True)
                    if item_str in unique_items:
                        errors.append(
                            f"Error at '{path}': Array must contain unique items (duplicate found at index {i})"
                        )
                        break
                    unique_items.add(item_str)
            except (TypeError, ValueError):
                # Fall back to a less efficient method if items are not JSON serializable
                if len(array) != len(set(map(str, array))):
                    errors.append(
                        f"Error at '{path}': Array must contain unique items"
                    )

        # Validate items
        if "items" in schema and array:
            items_schema = schema["items"]
            for i, item in enumerate(array):
                item_path = f"{path}[{i}]"
                item_errors = self._validate_against_schema(
                    item, items_schema, item_path, root_schema)
                errors.extend(item_errors)

        return errors

    def _validate_required(self, obj: Dict[str, Any], required_props: List[str], path: str) -> List[str]:
        """
        Validate required properties.

        Args:
            obj: The object to validate
            required_props: List of required property names
            path: JSON path for error reporting

        Returns:
            List of validation errors
        """
        errors = []
        for prop in required_props:
            if prop not in obj:
                errors.append(
                    f"Error at '{path}': Missing required property '{prop}'")
        return errors

    def _validate_dependencies(self, obj: Dict[str, Any], dependencies: Dict[str, List[str]], path: str) -> List[str]:
        """
        Validate property dependencies.

        Args:
            obj: The object to validate
            dependencies: Mapping of property names to required dependent properties
            path: JSON path for error reporting

        Returns:
            List of validation errors
        """
        errors = []
        for prop, required_props in dependencies.items():
            if prop in obj:
                for req_prop in required_props:
                    if req_prop not in obj:
                        errors.append(
                            f"Error at '{path}': Property '{prop}' depends on '{req_prop}', which is missing"
                        )
        return errors

    def _validate_property_names(self, obj: Dict[str, Any], schema: Dict[str, Any], path: str, root_schema: Dict[str, Any]) -> List[str]:
        """
        Validate property names.

        Args:
            obj: The object to validate
            schema: Schema for property names
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors
        """
        errors = []

        for prop in obj:
            prop_path = f"{path}/{prop}"
            # Validate property name against the schema
            prop_errors = self._validate_against_schema(
                prop, schema, prop_path, root_schema)
            for error in prop_errors:
                # Adjust the error message to make it clear this is about a property name
                if "Error at" in error:
                    # Replace the path
                    modified_error = error.replace(
                        f"Error at '{prop_path}':", f"Error at '{path}':")

                    # Add property name for all error types
                    if "Property name" not in modified_error:
                        # For string length errors
                        if "String length" in modified_error:
                            modified_error = modified_error.replace(
                                "String length", f"Property name '{prop}' length"
                            )
                        # For pattern errors
                        elif "does not match pattern" in modified_error:
                            modified_error = modified_error.replace(
                                f"String '{prop}'", f"Property name '{prop}'"
                            )
                        # For any other error types
                        elif f"got {type(prop).__name__}" in modified_error:
                            modified_error = modified_error.replace(
                                f"got {type(prop).__name__}", f"Property name '{prop}'"
                            )
                        # Catch-all for any other errors
                        else:
                            modified_error = modified_error.replace(
                                ":", f": Property name '{prop}'"
                            )

                    errors.append(modified_error)
                else:
                    errors.append(error)

        return errors

    def _validate_object(self, obj: Dict[str, Any], schema: Dict[str, Any], path: str, root_schema: Dict[str, Any]) -> List[str]:
        """
        Validate object.

        Args:
            obj: The object to validate
            schema: Schema for the object
            path: JSON path for error reporting
            root_schema: The root schema document, used for resolving references

        Returns:
            List of validation errors
        """
        errors = []

        # Validate required properties
        if "required" in schema:
            errors.extend(self._validate_required(
                obj, schema["required"], path))

        # Validate dependencies
        if "dependencies" in schema:
            errors.extend(self._validate_dependencies(
                obj, schema["dependencies"], path))

        # Validate property names
        if "propertyNames" in schema:
            errors.extend(self._validate_property_names(
                obj, schema["propertyNames"], path, root_schema))

        # Validate minProperties
        if "minProperties" in schema and len(obj) < schema["minProperties"]:
            errors.append(
                f"Error at '{path}': Object has {len(obj)} properties, but minimum is {schema['minProperties']}"
            )

        # Validate maxProperties
        if "maxProperties" in schema and len(obj) > schema["maxProperties"]:
            errors.append(
                f"Error at '{path}': Object has {len(obj)} properties, but maximum is {schema['maxProperties']}"
            )

        # Validate properties
        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties", True)
        pattern_properties = schema.get("patternProperties", {})

        for prop, value in obj.items():
            if prop in properties:
                # Property is defined in properties
                prop_path = f"{path}/{prop}"
                prop_schema = properties[prop]
                errors.extend(self._validate_against_schema(
                    value, prop_schema, prop_path, root_schema))
            else:
                # Check if property matches any pattern properties
                matched_pattern = False
                for pattern, pattern_schema in pattern_properties.items():
                    if re.match(pattern, prop):
                        matched_pattern = True
                        prop_path = f"{path}/{prop}"
                        errors.extend(self._validate_against_schema(
                            value, pattern_schema, prop_path, root_schema))

                # If property didn't match any patterns and additionalProperties is false, it's an error
                if not matched_pattern and additional_properties is False:
                    errors.append(
                        f"Error at '{path}': Additional property '{prop}' not allowed")
                elif not matched_pattern and isinstance(additional_properties, dict):
                    # Validate additional property against additionalProperties schema
                    prop_path = f"{path}/{prop}"
                    errors.extend(self._validate_against_schema(
                        value, additional_properties, prop_path, root_schema))

        return errors

