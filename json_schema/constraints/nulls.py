"""
Null constraint implementation.
"""

from typing import Any

from .base import TypeConstraint, ValidationContext


class NullConstraint(TypeConstraint):
    """
    Constraint for validating null values.
    """
    
    @property
    def json_type(self) -> str:
        return "null"
    
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate null-specific constraints.
        
        Args:
            value: The null value to validate (guaranteed to be None)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # No additional constraints for null
        return True
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        return "NullConstraint()"
    
    def __repr__(self) -> str:
        """Detailed representation of the null constraint."""
        return self.__str__()
