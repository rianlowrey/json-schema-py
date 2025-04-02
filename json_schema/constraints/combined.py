"""
Combined constraint implementation.
"""

from typing import Any, List

from .base import Constraint, ValidationContext


class CombinedConstraint(Constraint):
    """
    Constraint that combines multiple constraints.
    
    This is used for schemas that have multiple validations at the same level.
    """
    
    def __init__(self, constraints: List[Constraint]):
        """
        Initialize a new combined constraint.
        
        Args:
            constraints: List of constraints to combine
        """
        self.constraints = constraints
    
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against all combined constraints.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if all constraints pass, False otherwise
        """
        valid = True
        
        for constraint in self.constraints:
            if not constraint.validate(value, context):
                valid = False
        
        return valid
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"CombinedConstraint(constraints={len(self.constraints)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the combined constraint."""
        return f"CombinedConstraint(constraints={[str(c) for c in self.constraints]})"
