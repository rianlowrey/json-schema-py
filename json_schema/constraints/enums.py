"""
Enum constraint implementation.
"""

from typing import Any, List

from .base import Constraint, ValidationContext
from ..api import ErrorCode


class EnumConstraint(Constraint):
    """
    Constraint that validates a value against an enumeration.
    """
    
    def __init__(self, values: List[Any]):
        """
        Initialize a new enum constraint.
        
        Args:
            values: List of allowed values
        """
        self.values = values
    
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this enum constraint.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # Check if the value is in the enum
        for enum_value in self.values:
            if value == enum_value:
                return True
        
        # Value not in enum
        context.add_error(
            ErrorCode.ENUM_MISMATCH,
            f"Value '{value}' not in enumeration: {self.values}",
            value=value,
            constraint=self
        )
        return False
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"EnumConstraint(values={self.values})"
    
    def __repr__(self) -> str:
        """Detailed representation of the enum constraint."""
        return self.__str__()
