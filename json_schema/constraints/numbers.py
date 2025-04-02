"""
Number constraint implementation.
"""

from typing import Any, Optional

from .base import TypeConstraint, ValidationContext
from ..api import ErrorCode


class NumberConstraint(TypeConstraint):
    """
    Constraint for validating numeric values.
    """
    
    def __init__(self, 
                minimum: Optional[float] = None,
                maximum: Optional[float] = None,
                exclusive_minimum: bool = False,
                exclusive_maximum: bool = False,
                multiple_of: Optional[float] = None,
                integer_only: bool = False):
        """
        Initialize a new number constraint.
        
        Args:
            minimum: Minimum value
            maximum: Maximum value
            exclusive_minimum: Whether minimum is exclusive
            exclusive_maximum: Whether maximum is exclusive
            multiple_of: Value must be a multiple of this
            integer_only: Whether only integers are allowed
        """
        self.minimum = minimum
        self.maximum = maximum
        self.exclusive_minimum = exclusive_minimum
        self.exclusive_maximum = exclusive_maximum
        self.multiple_of = multiple_of
        self.integer_only = integer_only
    
    @property
    def json_type(self) -> str:
        return "integer" if self.integer_only else "number"
    
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate number-specific constraints.
        
        Args:
            value: The number to validate (guaranteed to be a number)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        valid = True
        
        # Check minimum
        if self.minimum is not None:
            if self.exclusive_minimum and value <= self.minimum:
                context.add_error(
                    ErrorCode.NUMBER_TOO_SMALL,
                    f"Value {value} must be greater than {self.minimum}",
                    value=value,
                    constraint=self
                )
                valid = False
            elif not self.exclusive_minimum and value < self.minimum:
                context.add_error(
                    ErrorCode.NUMBER_TOO_SMALL,
                    f"Value {value} must be greater than or equal to {self.minimum}",
                    value=value,
                    constraint=self
                )
                valid = False
        
        # Check maximum
        if self.maximum is not None:
            if self.exclusive_maximum and value >= self.maximum:
                context.add_error(
                    ErrorCode.NUMBER_TOO_LARGE,
                    f"Value {value} must be less than {self.maximum}",
                    value=value,
                    constraint=self
                )
                valid = False
            elif not self.exclusive_maximum and value > self.maximum:
                context.add_error(
                    ErrorCode.NUMBER_TOO_LARGE,
                    f"Value {value} must be less than or equal to {self.maximum}",
                    value=value,
                    constraint=self
                )
                valid = False
        
        # Check multiple_of
        if self.multiple_of is not None:
            # Handle floating point precision issues
            if isinstance(value, float) or isinstance(self.multiple_of, float):
                # For floating point, we need to consider precision
                remainder = value % self.multiple_of
                is_multiple = remainder < 1e-10 or abs(remainder - self.multiple_of) < 1e-10
            else:
                is_multiple = value % self.multiple_of == 0
                
            if not is_multiple:
                context.add_error(
                    ErrorCode.NUMBER_NOT_MULTIPLE,
                    f"Value {value} is not a multiple of {self.multiple_of}",
                    value=value,
                    constraint=self
                )
                valid = False
                
        return valid
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        parts = []
        if self.minimum is not None:
            parts.append(f"minimum={self.minimum}")
            if self.exclusive_minimum:
                parts.append("exclusiveMinimum=True")
        if self.maximum is not None:
            parts.append(f"maximum={self.maximum}")
            if self.exclusive_maximum:
                parts.append("exclusiveMaximum=True")
        if self.multiple_of is not None:
            parts.append(f"multipleOf={self.multiple_of}")
        if self.integer_only:
            parts.append("integer_only=True")
        
        return f"NumberConstraint({', '.join(parts)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the number constraint."""
        return self.__str__()
