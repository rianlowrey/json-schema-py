"""
Validator implementation with topological constraint ordering.
"""

from typing import Any, Dict, List, Optional

from .constraints import Constraint, ValidationContext, ArrayConstraint, ObjectConstraint
from .api import ValidationResult, ErrorCode


class Validator:
    """
    Validates data against compiled constraint trees.

    This class is responsible for validating data against
    compiled constraint trees and generating validation results.

    It respects the topological dependency order of constraints
    within each branch of logical operators, ensuring correct semantics.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize a new validator.

        Args:
            verbose: Whether to include additional details in error messages
        """
        self.verbose = verbose

    def validate(self, data: Any, constraint: Constraint) -> ValidationResult:
        """
        Validate data against a compiled constraint.

        Args:
            data: Data to validate
            constraint: Compiled constraint to validate against

        Returns:
            ValidationResult containing validation status and errors
        """
        # Create a validation context
        context = ValidationContext(verbose=self.verbose)

        # Determine which validation approach to use
        if self._is_logical_operator(constraint):
            # Delegate to the logical operator's own validate method
            valid = constraint.validate(data, context)
        elif hasattr(constraint, "validation_order") and getattr(constraint, "validation_order"):
            # Use hierarchical validation that respects structure
            valid = self._validate_hierarchically(data, constraint, context)
        else:
            # Standard validation for simple constraints
            valid = constraint.validate(data, context)

        # Create and return the validation result
        return ValidationResult(
            valid=valid,
            errors=context.errors
        )

    def _is_logical_operator(self, constraint: Constraint) -> bool:
        """
        Check if a constraint is a logical operator.

        Args:
            constraint: Constraint to check

        Returns:
            True if the constraint is a logical operator
        """
        return constraint.__class__.__name__ in {
            "AllOfConstraint", "AnyOfConstraint", "OneOfConstraint", "NotConstraint"
        }

    def _validate_hierarchically(self, data: Any, constraint: Constraint, context: ValidationContext) -> bool:
        """
        Validate data against constraints while respecting the hierarchical structure.

        This method ensures property constraints are only applied to their respective properties,
        not to the root object.

        Args:
            data: Data to validate
            constraint: Root constraint
            context: Validation context

        Returns:
            True if validation succeeds, False otherwise
        """
        # First validate the root constraint itself
        if not constraint.validate(data, context):
            return False

        # For object constraints, we don't need further validation since properties
        # are already validated inside the object constraint
        if isinstance(constraint, ObjectConstraint):
            return True

        # For array constraints, validate the items constraint against each item
        if isinstance(constraint, ArrayConstraint) and constraint.items and isinstance(data, list):
            for i, item in enumerate(data):
                with context.with_path(i):
                    if not constraint.items.validate(item, context):
                        return False

        # For other constraint types, we don't need additional validation
        return True

    def _validate_with_order(self, data: Any, constraint: Constraint, context: ValidationContext) -> bool:
        """
        Validate data against constraints in dependency order.

        Args:
            data: Data to validate
            constraint: Root constraint with validation_order attribute
            context: Validation context

        Returns:
            True if validation succeeds, False otherwise
        """
        # Get the validation order
        validation_order = getattr(constraint, "validation_order")

        # Track path -> type errors mapping
        type_errors = {}

        # Validate constraints in the specified order
        valid = True
        for c in validation_order:
            # Skip logical operators - they're handled separately
            if self._is_logical_operator(c):
                continue

            current_path = context.path

            # Skip validating NOT constraints if there's a type error for the path
            if (c.__class__.__name__ == "NotConstraint" and
                    current_path in type_errors):
                continue

            # Validate this constraint
            if not c.validate(data, context):
                valid = False

                # Check if this is a type error
                if hasattr(c, "json_type"):
                    for error in context.errors:
                        if error.code == ErrorCode.TYPE_ERROR and error.constraint == c:
                            type_errors[current_path] = error
                            break

        return valid
