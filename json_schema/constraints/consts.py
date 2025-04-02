"""
Const constraint implementation.
"""

from typing import Any

from .base import Constraint, ValidationContext
from ..api import ErrorCode


class ConstConstraint(Constraint):
    """
    Constraint that validates a value against a constant.
    """
    
    def __init__(self, value: Any):
        """
        Initialize a new const constraint.
        
        Args:
            value: Constant value to match
        """
        self.value = value
    
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this const constraint.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # Check if the value equals the const value
        if value == self.value:
            return True
        
        # Value doesn't match
        context.add_error(
            ErrorCode.CONST_MISMATCH,
            f"Expected constant value {self.value}, got {value}",
            value=value,
            constraint=self
        )
        return False
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"ConstConstraint(value={self.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of the const constraint."""
        return self.__str__()
