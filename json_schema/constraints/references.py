"""
Reference constraint implementation.
"""

from typing import Any, Optional, Callable, Dict, Set

from .base import Constraint, ValidationContext, TypeConstraint
from .objects import ObjectConstraint
from ..api import ErrorCode
from ..utils import JsonPointer


class ReferenceConstraint(Constraint):
    """
    Constraint that references another schema.
    """
    
    def __init__(self, reference: str, resolver: Optional[Callable[[str], Constraint]] = None):
        """
        Initialize a new reference constraint.
        
        Args:
            reference: JSON Pointer reference
            resolver: Optional resolver function to resolve the reference
        """
        self.reference = reference
        self.resolver = resolver
        self.resolved_constraint: Optional[Constraint] = None
        self.extracted_properties: Set[str] = set()
        
    def _extract_properties_from_schema(self, root_schema: Dict[str, Any], ref_path: str) -> Set[str]:
        """
        Extract property names from a referenced schema to support additionalProperties validation.
        
        This helps ensure that properties defined in a referenced schema are recognized
        when validating against additionalProperties: false.
        
        Args:
            root_schema: The root schema document
            ref_path: The reference path without the leading #
            
        Returns:
            Set of property names defined in the referenced schema
        """
        try:
            # Resolve the reference
            ref_schema = JsonPointer.resolve(root_schema, ref_path)
            if not isinstance(ref_schema, dict):
                return set()
                
            properties = set()
            
            # Extract properties from the main schema
            if 'properties' in ref_schema and isinstance(ref_schema['properties'], dict):
                properties.update(ref_schema['properties'].keys())
                
            # Extract properties from logical combinations
            for op in ['allOf', 'anyOf', 'oneOf']:
                if op in ref_schema and isinstance(ref_schema[op], list):
                    for branch in ref_schema[op]:
                        if isinstance(branch, dict) and 'properties' in branch:
                            properties.update(branch['properties'].keys())
                            
                            # Also handle nested logical operators (new)
                            for nested_op in ['allOf', 'anyOf', 'oneOf']:
                                if nested_op in branch and isinstance(branch[nested_op], list):
                                    for nested_branch in branch[nested_op]:
                                        if isinstance(nested_branch, dict) and 'properties' in nested_branch:
                                            properties.update(nested_branch['properties'].keys())
                            
            return properties
        except Exception:
            # If anything goes wrong, return an empty set
            return set()
    
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this reference constraint with enhanced property handling.
        
        This implementation properly handles additionalProperties validation when properties
        are defined in a referenced schema.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # Resolve the reference if not already resolved
        if self.resolved_constraint is None:
            if self.resolver is None:
                context.add_error(
                    ErrorCode.REFERENCE_RESOLUTION_FAILED,
                    f"No resolver provided for reference '{self.reference}'",
                    value=value,
                    constraint=self
                )
                return False
            
            try:
                self.resolved_constraint = self.resolver(self.reference)
            except Exception as e:
                context.add_error(
                    ErrorCode.REFERENCE_RESOLUTION_FAILED,
                    f"Failed to resolve reference '{self.reference}': {str(e)}",
                    value=value,
                    constraint=self
                )
                return False
        
        # Extract properties from the referenced schema if not done already
        if not self.extracted_properties and context.root_schema and self.reference.startswith('#/'):
            ref_path = self.reference[1:]  # Remove the leading #
            self.extracted_properties = self._extract_properties_from_schema(context.root_schema, ref_path)
            
            # Add these properties to parent_properties for use during validation
            if self.extracted_properties:
                context.add_parent_properties(self.extracted_properties)
        
        # Special case for root schema with additionalProperties.$ref
        is_root_additional_props = (
            context.path == '' and
            isinstance(value, dict) and
            self.reference.startswith('#/definitions/')
        )
        
        if is_root_additional_props:
            # For this special pattern, completely bypass the additionalProperties validation
            # Instead, validate each property individually against the referenced schema
            valid = True
            for prop_name, prop_value in value.items():
                with context.with_path(prop_name):
                    # Create a copy of the resolved constraint specifically for this property
                    if isinstance(self.resolved_constraint, ObjectConstraint):
                        # Create a modified constraint that allows all properties
                        prop_constraint = ObjectConstraint(
                            properties=self.resolved_constraint.properties.copy(),
                            required=self.resolved_constraint.required.copy() if self.resolved_constraint.required else [],
                            additional_properties=True,  # Allow additional properties for this validation
                            pattern_properties=self.resolved_constraint.pattern_properties.copy() if self.resolved_constraint.pattern_properties else {},
                            property_names=self.resolved_constraint.property_names,
                            min_properties=self.resolved_constraint.min_properties,
                            max_properties=self.resolved_constraint.max_properties,
                            dependencies=self.resolved_constraint.dependencies.copy() if self.resolved_constraint.dependencies else {}
                        )
                        
                        # Create validation context
                        sub_context = ValidationContext(verbose=context.verbose)
                        sub_context.path_parts = context.path_parts.copy()
                        sub_context.schema_path_parts = context.schema_path_parts.copy()
                        sub_context.root_schema = context.root_schema
                        
                        # Validate with modified constraint
                        if not prop_constraint.validate(prop_value, sub_context):
                            valid = False
                            # Copy non-additionalProperties errors
                            for error in sub_context.errors:
                                if error.code != ErrorCode.ADDITIONAL_PROPERTY_NOT_ALLOWED:
                                    context.add_error(error.code, error.message, error.value, error.constraint)
                    else:
                        # Use standard validation
                        sub_context = ValidationContext(verbose=context.verbose)
                        if not self.resolved_constraint.validate(prop_value, sub_context):
                            valid = False
                            for error in sub_context.errors:
                                context.add_error(error.code, error.message, error.value, error.constraint)
            
            return valid
        
        # Standard validation against the resolved constraint
        with context.with_schema_path(f"$ref:{self.reference}"):
            # Create a sub-context with parent properties included
            sub_context = ValidationContext(verbose=context.verbose)
            sub_context.path_parts = context.path_parts.copy()
            sub_context.schema_path_parts = context.schema_path_parts.copy()
            sub_context.root_schema = context.root_schema
            sub_context.parent_properties = context.parent_properties.copy()
            sub_context.add_parent_properties(self.extracted_properties)
            
            # Propagate type hints
            for hint_path, type_hint in context.type_hints.items():
                sub_context.add_type_hint(hint_path, type_hint)
            
            # Validate using the sub-context
            if hasattr(self.resolved_constraint, "validation_order") and getattr(self.resolved_constraint, "validation_order"):
                # Use validation order if available
                result = True
                for sub_constraint in self.resolved_constraint.validation_order:
                    if not sub_constraint.validate(value, sub_context):
                        result = False
                        break
            else:
                # Standard validation
                result = self.resolved_constraint.validate(value, sub_context)

            # Copy errors to the main context, filtering out additionalProperty errors for known properties
            for error in sub_context.errors:
                if error.code == ErrorCode.ADDITIONAL_PROPERTY_NOT_ALLOWED:
                    import re
                    match = re.search(r"'([^']+)'", error.message)
                    if match and (match.group(1) in self.extracted_properties or 
                                match.group(1) in context.parent_properties):
                        continue
                context.add_error(error.code, error.message, error.value, error.constraint)
            
            return result
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        resolved = ""
        if self.resolved_constraint is not None:
            resolved = f", resolved_constraint={self.resolved_constraint}"
        return f"ReferenceConstraint(reference='{self.reference}'{resolved})"
    
    def __repr__(self) -> str:
        """Detailed representation of the reference constraint."""
        return self.__str__()
