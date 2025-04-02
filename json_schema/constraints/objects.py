"""
Object constraint implementation.
"""

import re
from typing import Any, Dict, List, Optional, Union

from .base import TypeConstraint, ValidationContext, Constraint
from ..api import ErrorCode


class ObjectConstraint(TypeConstraint):
    """
    Constraint for validating object values.
    """
    
    def __init__(self, 
                properties: Optional[Dict[str, Constraint]] = None,
                required: Optional[List[str]] = None,
                additional_properties: Union[bool, Constraint] = True,
                pattern_properties: Optional[Dict[str, Constraint]] = None,
                property_names: Optional[Constraint] = None,
                min_properties: Optional[int] = None,
                max_properties: Optional[int] = None,
                dependencies: Optional[Dict[str, List[str]]] = None):
        """
        Initialize a new object constraint.
        
        Args:
            properties: Constraints for specific properties
            required: List of required property names
            additional_properties: Whether additional properties are allowed, or constraint for them
            pattern_properties: Constraints for properties matching regex patterns
            property_names: Constraint for property names
            min_properties: Minimum number of properties
            max_properties: Maximum number of properties
            dependencies: Property dependencies
        """
        self.properties = properties or {}
        self.required = required or []
        self.additional_properties = additional_properties
        self.pattern_properties = pattern_properties or {}
        self.property_names = property_names
        self.min_properties = min_properties
        self.max_properties = max_properties
        self.dependencies = dependencies or {}
        
        # Compile the pattern property regexes
        self._compiled_patterns = {}
        for pattern in self.pattern_properties:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern)
            except re.error:
                # We'll handle this during validation
                pass
    
    @property
    def json_type(self) -> str:
        return "object"
    
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate object-specific constraints.
        
        Args:
            value: The object to validate (guaranteed to be an object)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        valid = True
        
        # Check min_properties
        if self.min_properties is not None and len(value) < self.min_properties:
            context.add_error(
                ErrorCode.OBJECT_TOO_FEW_PROPERTIES,
                f"Object has {len(value)} properties, but minimum is {self.min_properties}",
                value=value,
                constraint=self
            )
            valid = False
            
        # Check max_properties
        if self.max_properties is not None and len(value) > self.max_properties:
            context.add_error(
                ErrorCode.OBJECT_TOO_MANY_PROPERTIES,
                f"Object has {len(value)} properties, but maximum is {self.max_properties}",
                value=value,
                constraint=self
            )
            valid = False
            
        # Check required properties - do this first as it's a key validation
        for prop in self.required:
            if prop not in value:
                context.add_error(
                    ErrorCode.REQUIRED_PROPERTY_MISSING,
                    f"Missing required property '{prop}'",
                    value=value,
                    constraint=self
                )
                valid = False
        
        # Check dependencies
        for prop, deps in self.dependencies.items():
            if prop in value:
                for dep in deps:
                    if dep not in value:
                        context.add_error(
                            ErrorCode.DEPENDENCY_MISSING,
                            f"Property '{prop}' depends on '{dep}', which is missing",
                            value=value,
                            constraint=self
                        )
                        valid = False
        
        # Validate property names
        if self.property_names is not None:
            for prop in value:
                with context.with_path(prop):
                    if not self.property_names.validate(prop, context):
                        valid = False
                
        # Track which properties have been validated by a schema
        validated_props = set()
        
        # Add properties defined in this schema to parent properties
        for prop in self.properties.keys():
            context.add_parent_property(prop)
        
        # Validate specified properties
        for prop, constraint in self.properties.items():
            # Mark as validated even if not present in the value
            validated_props.add(prop)
            
            if prop in value:
                with context.with_path(prop):
                    if not constraint.validate(value[prop], context):
                        valid = False
        
        # Validate pattern properties
        for pattern, constraint in self.pattern_properties.items():
            # Compile the pattern if not already compiled
            if pattern not in self._compiled_patterns:
                try:
                    self._compiled_patterns[pattern] = re.compile(pattern)
                except re.error as e:
                    context.add_error(
                        ErrorCode.SCHEMA_INVALID,
                        f"Invalid regex pattern '{pattern}': {str(e)}",
                        value=pattern,
                        constraint=self
                    )
                    valid = False
                    continue
            
            compiled_pattern = self._compiled_patterns[pattern]
            
            # Check properties against the pattern
            for prop in value:
                if compiled_pattern.search(prop):
                    validated_props.add(prop)
                    with context.with_path(prop):
                        if not constraint.validate(value[prop], context):
                            valid = False
        
        # Check additional properties - do this last after all other validations
        for prop in value:
            if prop not in validated_props:
                # Also check if the property is defined in a parent schema
                if prop in context.parent_properties:
                    # This property is defined in a parent schema, so it's valid
                    continue
                    
                if self.additional_properties is False:
                    context.add_error(
                        ErrorCode.ADDITIONAL_PROPERTY_NOT_ALLOWED,
                        f"Additional property '{prop}' not allowed",
                        value=value[prop],
                        constraint=self
                    )
                    valid = False
                elif isinstance(self.additional_properties, Constraint):
                    with context.with_path(prop):
                        if not self.additional_properties.validate(value[prop], context):
                            valid = False
        
        return valid
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        parts = []
        if self.properties:
            parts.append(f"properties={list(self.properties.keys())}")
        if self.required:
            parts.append(f"required={self.required}")
        if self.additional_properties is not True:
            ap_str = str(self.additional_properties) if isinstance(self.additional_properties, Constraint) else str(self.additional_properties)
            parts.append(f"additional_properties={ap_str}")
        if self.pattern_properties:
            parts.append(f"pattern_properties={list(self.pattern_properties.keys())}")
        if self.property_names is not None:
            parts.append(f"property_names={self.property_names}")
        if self.min_properties is not None:
            parts.append(f"min_properties={self.min_properties}")
        if self.max_properties is not None:
            parts.append(f"max_properties={self.max_properties}")
        if self.dependencies:
            parts.append(f"dependencies={self.dependencies}")
        
        return f"ObjectConstraint({', '.join(parts)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the object constraint."""
        return self.__str__()
