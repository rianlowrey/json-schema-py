"""
String constraint implementation.
"""

import re
from typing import Any, Optional, Pattern

from .base import TypeConstraint, ValidationContext
from ..api import ErrorCode


class StringConstraint(TypeConstraint):
    """
    Constraint for validating string values.
    """
    
    def __init__(self, 
                min_length: Optional[int] = None,
                max_length: Optional[int] = None,
                pattern: Optional[str] = None):
        """
        Initialize a new string constraint.
        
        Args:
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regular expression pattern
        """
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self._compiled_pattern: Optional[Pattern] = None
        
        # Compile the pattern if provided
        if pattern:
            try:
                self._compiled_pattern = re.compile(pattern)
            except re.error:
                # We'll handle this during validation
                pass
    
    @property
    def json_type(self) -> str:
        return "string"
    
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate string-specific constraints.
        
        Args:
            value: The string to validate (guaranteed to be a string)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        valid = True
        
        # Check min_length
        if self.min_length is not None and len(value) < self.min_length:
            context.add_error(
                ErrorCode.STRING_TOO_SHORT,
                f"String length is {len(value)}, but minimum is {self.min_length}",
                value=value,
                constraint=self
            )
            valid = False
            
        # Check max_length
        if self.max_length is not None and len(value) > self.max_length:
            context.add_error(
                ErrorCode.STRING_TOO_LONG,
                f"String length is {len(value)}, but maximum is {self.max_length}",
                value=value,
                constraint=self
            )
            valid = False
            
        # Check pattern
        if self.pattern is not None:
            if self._compiled_pattern is None:
                try:
                    self._compiled_pattern = re.compile(self.pattern)
                except re.error as e:
                    context.add_error(
                        ErrorCode.SCHEMA_INVALID,
                        f"Invalid regex pattern: {str(e)}",
                        value=value,
                        constraint=self
                    )
                    return False
                    
            if not self._compiled_pattern.search(value):
                context.add_error(
                    ErrorCode.PATTERN_MISMATCH,
                    f"String '{value}' does not match pattern '{self.pattern}'",
                    value=value,
                    constraint=self
                )
                valid = False
                
        return valid
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        parts = []
        if self.min_length is not None:
            parts.append(f"minLength={self.min_length}")
        if self.max_length is not None:
            parts.append(f"maxLength={self.max_length}")
        if self.pattern is not None:
            parts.append(f"pattern={self.pattern}")
        
        return f"StringConstraint({', '.join(parts)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the string constraint."""
        return self.__str__()
