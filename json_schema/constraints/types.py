"""
Type constraint implementation.
"""

from typing import Any, List, Union

from .base import Constraint, ValidationContext
from ..api import ErrorCode
from ..utils import TypeUtils


class TypeConstraintImpl(Constraint):
    """
    Constraint that validates a value's type against one or more possible types.
    """
    
    def __init__(self, types: Union[str, List[str]]):
        """
        Initialize a new type constraint.
        
        Args:
            types: JSON Schema type name or list of type names
        """
        # Store the original specified types
        self.specified_types = set([types] if isinstance(types, str) else types)
        
        # Get all effective types considering the type hierarchy
        self.effective_types = TypeUtils.get_effective_types(self.specified_types)
    
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this type constraint.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # Get the actual JSON type of the value
        actual_type = TypeUtils.get_json_type(value)
        
        # Check if the actual type is among the effective types
        if actual_type in self.effective_types:
            return True
        
        # Type doesn't match - check if it's compatible in the reverse direction
        # (e.g., if the value is an integer but we're looking for a number)
        compatible_types = TypeUtils.get_compatible_types(actual_type)
        if any(t in self.specified_types for t in compatible_types):
            return True
        
        # Type doesn't match
        types_list = sorted(self.specified_types)  # Sort for consistent error messages
        context.add_error(
            ErrorCode.TYPE_ERROR,
            f"Expected {', '.join(types_list)}, got {actual_type}",
            value=value,
            constraint=self
        )
        return False
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        types_list = sorted(self.specified_types)  # Sort for consistent string representation
        return f"TypeConstraint(types={types_list})"
    
    def __repr__(self) -> str:
        """Detailed representation of the type constraint."""
        return self.__str__()
