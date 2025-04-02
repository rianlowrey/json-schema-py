"""
Boolean constraint implementation.
"""

from typing import Any

from .base import TypeConstraint, ValidationContext


class BooleanConstraint(TypeConstraint):
    """
    Constraint for validating boolean values.
    """
    
    @property
    def json_type(self) -> str:
        return "boolean"
    
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate boolean-specific constraints.
        
        Args:
            value: The boolean to validate (guaranteed to be a boolean)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # No additional constraints for booleans
        return True
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        return "BooleanConstraint()"
    
    def __repr__(self) -> str:
        """Detailed representation of the boolean constraint."""
        return self.__str__()
