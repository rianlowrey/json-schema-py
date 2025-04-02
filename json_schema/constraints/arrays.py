"""
Array constraint implementation.
"""

from typing import Any, Optional

from .base import TypeConstraint, ValidationContext, Constraint
from ..api import ErrorCode


class ArrayConstraint(TypeConstraint):
    """
    Constraint for validating array values.
    """
    
    def __init__(self, 
                items: Optional[Constraint] = None,
                min_items: Optional[int] = None,
                max_items: Optional[int] = None,
                unique_items: bool = False):
        """
        Initialize a new array constraint.
        
        Args:
            items: Constraint for array items
            min_items: Minimum number of items
            max_items: Maximum number of items
            unique_items: Whether items must be unique
        """
        self.items = items
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
    
    @property
    def json_type(self) -> str:
        return "array"
    
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate array-specific constraints.
        
        Args:
            value: The array to validate (guaranteed to be an array)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        valid = True
        
        # Check min_items
        if self.min_items is not None and len(value) < self.min_items:
            context.add_error(
                ErrorCode.ARRAY_TOO_SHORT,
                f"Array has {len(value)} items, but minimum is {self.min_items}",
                value=value,
                constraint=self
            )
            valid = False
            
        # Check max_items
        if self.max_items is not None and len(value) > self.max_items:
            context.add_error(
                ErrorCode.ARRAY_TOO_LONG,
                f"Array has {len(value)} items, but maximum is {self.max_items}",
                value=value,
                constraint=self
            )
            valid = False
            
        # Check unique_items
        if self.unique_items and len(value) > 1:
            try:
                # Use JSON serialization for comparison
                unique_items = set()
                for i, item in enumerate(value):
                    item_str = str(item)  # Simple string representation
                    if item_str in unique_items:
                        context.add_error(
                            ErrorCode.ARRAY_ITEMS_NOT_UNIQUE,
                            f"Array items must be unique (duplicate at index {i})",
                            value=value,
                            constraint=self
                        )
                        valid = False
                        break
                    unique_items.add(item_str)
            except (TypeError, ValueError):
                # Fall back to a simpler approach
                if len(value) != len(set(map(str, value))):
                    context.add_error(
                        ErrorCode.ARRAY_ITEMS_NOT_UNIQUE,
                        "Array items must be unique",
                        value=value,
                        constraint=self
                    )
                    valid = False
        
        # Validate items
        if self.items is not None:
            for i, item in enumerate(value):
                with context.with_path(i):
                    if not self.items.validate(item, context):
                        valid = False
        
        return valid
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        parts = []
        if self.items is not None:
            parts.append(f"items={self.items}")
        if self.min_items is not None:
            parts.append(f"min_items={self.min_items}")
        if self.max_items is not None:
            parts.append(f"max_items={self.max_items}")
        if self.unique_items:
            parts.append("unique_items=True")
        
        return f"ArrayConstraint({', '.join(parts)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the array constraint."""
        return self.__str__()
