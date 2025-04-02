"""
Logical constraint implementations.
"""

from typing import Any, Dict, List, Optional, Union, Set, Pattern, Tuple

from .base import Constraint, ValidationContext
from .objects import ObjectConstraint
from ..api import ErrorCode
from ..utils import TypeUtils


class AllOfConstraint(Constraint):
    """
    Constraint that requires a value to satisfy all sub-constraints.
    """

    def __init__(self, constraints: List[Constraint]):
        """
        Initialize a new all-of constraint.

        Args:
            constraints: List of constraints that must all be satisfied
        """
        self.constraints = constraints

    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this all-of constraint.

        Args:
            value: Value to validate
            context: Validation context

        Returns:
            True if validation succeeds, False otherwise
        """
        valid = True

        # Add type hints based on the JSON type of the value
        json_type = TypeUtils.get_json_type(value)
        if json_type != "unknown":
            context.add_type_hint(context.path, json_type)
        
        # Special handling for objects with properties
        if json_type == "object":
            # Collect all defined properties from object constraints in allOf
            all_properties = set()
            for constraint in self.constraints:
                if isinstance(constraint, ObjectConstraint) and constraint.properties:
                    all_properties.update(constraint.properties.keys())
            
            # Add these to the parent_properties set in the context
            if all_properties:
                context.add_parent_properties(all_properties)
        
        # Validate against each constraint
        for i, constraint in enumerate(self.constraints):
            with context.with_schema_path(f"allOf/{i}"):
                # Use an isolated error context to collect sub-constraint errors
                sub_context = ValidationContext(verbose=context.verbose)
                sub_context.path_parts = context.path_parts.copy()
                sub_context.schema_path_parts = context.schema_path_parts.copy()
                sub_context.root_schema = context.root_schema  # Ensure root schema is propagated
                
                # Propagate any type hints
                for path, type_hint in context.type_hints.items():
                    sub_context.add_type_hint(path, type_hint)
                
                # Propagate parent properties
                sub_context.parent_properties = context.parent_properties.copy()
                
                # Check if this constraint has a validation order
                sub_result = False
                if hasattr(constraint, "validation_order") and getattr(constraint, "validation_order"):
                    # Use the validation order
                    sub_result = True
                    for sub_constraint in constraint.validation_order:
                        if not sub_constraint.validate(value, sub_context):
                            sub_result = False
                            break
                else:
                    # Use standard validation
                    sub_result = constraint.validate(value, sub_context)
                
                if not sub_result:
                    valid = False

                    # Add the collected errors to the main context
                    for error in sub_context.errors:
                        # Skip additionalProperty errors for properties defined in parent schemas
                        if error.code == ErrorCode.ADDITIONAL_PROPERTY_NOT_ALLOWED:
                            import re
                            match = re.search(r"'([^']+)'", error.message)
                            if match and match.group(1) in context.parent_properties:
                                continue
                        
                        context.add_error(
                            error.code,
                            f"allOf[{i}]: {error.message}",
                            value=error.value,
                            constraint=error.constraint
                        )

        return valid

    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"AllOfConstraint(constraints={len(self.constraints)})"

    def __repr__(self) -> str:
        """Detailed representation of the all-of constraint."""
        return f"AllOfConstraint(constraints={[str(c) for c in self.constraints]})"


class AnyOfConstraint(Constraint):
    """
    Constraint that requires a value to satisfy at least one sub-constraint.
    """

    def __init__(self, constraints: List[Constraint]):
        """
        Initialize a new any-of constraint.

        Args:
            constraints: List of constraints, at least one of which must be satisfied
        """
        self.constraints = constraints

    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this any-of constraint.

        Args:
            value: Value to validate
            context: Validation context

        Returns:
            True if validation succeeds, False otherwise
        """
        # Add type hints based on the JSON type of the value
        json_type = TypeUtils.get_json_type(value)
        if json_type != "unknown":
            context.add_type_hint(context.path, json_type)

        # Special handling for objects with properties
        if json_type == "object":
            # Collect all defined properties from object constraints in anyOf
            all_properties = set()
            for constraint in self.constraints:
                if isinstance(constraint, ObjectConstraint) and constraint.properties:
                    all_properties.update(constraint.properties.keys())
            
            # Add these to the parent_properties set in the context
            if all_properties:
                context.add_parent_properties(all_properties)
                
        # Track all sub-constraint errors
        all_errors = []

        # Check each constraint separately
        for i, constraint in enumerate(self.constraints):
            with context.with_schema_path(f"anyOf/{i}"):
                # Use an isolated error context to collect sub-constraint errors
                sub_context = ValidationContext(verbose=context.verbose)
                sub_context.path_parts = context.path_parts.copy()
                sub_context.schema_path_parts = context.schema_path_parts.copy()
                # Important for resolving references
                sub_context.root_schema = context.root_schema

                # Propagate any type hints
                for path, type_hint in context.type_hints.items():
                    sub_context.add_type_hint(path, type_hint)
                
                # Propagate parent properties
                sub_context.parent_properties = context.parent_properties.copy()
                
                # If this branch has a specified validation order, use it
                if hasattr(constraint, "validation_order") and getattr(constraint, "validation_order"):
                    # Validate using the ordered constraints
                    branch_valid = True
                    for sub_constraint in constraint.validation_order:
                        if not sub_constraint.validate(value, sub_context):
                            branch_valid = False
                            break
                    
                    if branch_valid:
                        return True  # This branch passed
                else:
                    # Use standard validation for this branch
                    if constraint.validate(value, sub_context):
                        return True  # At least one constraint passed
                
                # Store the errors for this sub-constraint
                all_errors.append((i, sub_context.errors))

        # If we got here, no constraints matched
        context.add_error(
            ErrorCode.ANY_OF_NO_MATCH,
            "Value does not match any of the required schemas",
            value=value,
            constraint=self
        )

        # Add details about why each constraint failed
        if context.verbose:
            for i, errors in all_errors:
                for error in errors:
                    # Skip additionalProperty errors for properties defined in parent schemas
                    # or in other anyOf branches
                    if error.code == ErrorCode.ADDITIONAL_PROPERTY_NOT_ALLOWED:
                        import re
                        match = re.search(r"'([^']+)'", error.message)
                        if match and match.group(1) in context.parent_properties:
                            continue
                    
                    context.add_error(
                        error.code,
                        f"anyOf[{i}]: {error.message}",
                        value=error.value,
                        constraint=error.constraint
                    )

        return False

    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"AnyOfConstraint(constraints={len(self.constraints)})"

    def __repr__(self) -> str:
        """Detailed representation of the any-of constraint."""
        return f"AnyOfConstraint(constraints={[str(c) for c in self.constraints]})"



class OneOfConstraint(Constraint):
    """
    Constraint that requires a value to satisfy exactly one sub-constraint.
    """

    def __init__(self, constraints: List[Constraint]):
        """
        Initialize a new one-of constraint.

        Args:
            constraints: List of constraints, exactly one of which must be satisfied
        """
        self.constraints = constraints

    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this one-of constraint.

        Args:
            value: Value to validate
            context: Validation context

        Returns:
            True if validation succeeds, False otherwise
        """
        # Add type hints based on the JSON type of the value
        json_type = TypeUtils.get_json_type(value)
        if json_type != "unknown":
            context.add_type_hint(context.path, json_type)
        
        # Special handling for objects with properties
        if json_type == "object":
            # Collect all defined properties from object constraints in oneOf
            all_properties = set()
            for constraint in self.constraints:
                if isinstance(constraint, ObjectConstraint) and constraint.properties:
                    all_properties.update(constraint.properties.keys())
            
            # Add these to the parent_properties set in the context
            if all_properties:
                context.add_parent_properties(all_properties)
        
        # Track matching constraints and their indices
        matching_constraints = []

        # Track all sub-constraint errors
        all_errors = []

        # Check each constraint
        for i, constraint in enumerate(self.constraints):
            with context.with_schema_path(f"oneOf/{i}"):
                # Use an isolated error context to collect sub-constraint errors
                sub_context = ValidationContext(verbose=context.verbose)
                sub_context.path_parts = context.path_parts.copy()
                sub_context.schema_path_parts = context.schema_path_parts.copy()
                sub_context.root_schema = context.root_schema

                # Propagate any type hints
                for path, type_hint in context.type_hints.items():
                    sub_context.add_type_hint(path, type_hint)
                
                # Propagate parent properties
                sub_context.parent_properties = context.parent_properties.copy()
                
                # If this branch has a specified validation order, use it
                if hasattr(constraint, "validation_order") and getattr(constraint, "validation_order"):
                    # Validate using the ordered constraints
                    branch_valid = True
                    for sub_constraint in constraint.validation_order:
                        if not sub_constraint.validate(value, sub_context):
                            branch_valid = False
                            break
                    
                    if branch_valid:
                        matching_constraints.append(i)
                else:
                    # Validate against the sub-constraint
                    if constraint.validate(value, sub_context):
                        matching_constraints.append(i)
                    else:
                        # Store the errors for this sub-constraint
                        all_errors.append((i, sub_context.errors))
        
        # Check if exactly one constraint matched
        if len(matching_constraints) == 0:
            context.add_error(
                ErrorCode.ONE_OF_NO_MATCH,
                "Value does not match any of the required schemas",
                value=value,
                constraint=self
            )

            # Add details about why each constraint failed
            if context.verbose:
                for i, errors in all_errors:
                    for error in errors:
                        # Skip additionalProperty errors for properties defined in parent schemas
                        if error.code == ErrorCode.ADDITIONAL_PROPERTY_NOT_ALLOWED:
                            import re
                            match = re.search(r"'([^']+)'", error.message)
                            if match and match.group(1) in context.parent_properties:
                                continue
                        
                        context.add_error(
                            error.code,
                            f"oneOf[{i}]: {error.message}",
                            value=error.value,
                            constraint=error.constraint
                        )

            return False
        elif len(matching_constraints) > 1:
            context.add_error(
                ErrorCode.ONE_OF_MULTIPLE_MATCHES,
                f"Value matches {len(matching_constraints)} schemas, but should match exactly one",
                value=value,
                constraint=self
            )

            # Include the indices of matching schemas
            context.add_error(
                ErrorCode.ONE_OF_MULTIPLE_MATCHES,
                f"Matching schema indices: {matching_constraints}",
                value=value,
                constraint=self
            )

            return False

        # Exactly one constraint matched
        return True

    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"OneOfConstraint(constraints={len(self.constraints)})"

    def __repr__(self) -> str:
        """Detailed representation of the one-of constraint."""
        return f"OneOfConstraint(constraints={[str(c) for c in self.constraints]})"


class NotConstraint(Constraint):
    """
    Constraint that requires a value to not satisfy a sub-constraint.
    """

    def __init__(self, constraint: Constraint):
        """
        Initialize a new not constraint.

        Args:
            constraint: Constraint that must not be satisfied
        """
        self.constraint = constraint

    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this not constraint.

        Args:
            value: Value to validate
            context: Validation context

        Returns:
            True if validation succeeds, False otherwise
        """
        # Add type hints based on the JSON type of the value
        json_type = TypeUtils.get_json_type(value)
        if json_type != "unknown":
            context.add_type_hint(context.path, json_type)

        # 10:08 am 3/27 - additionalProperties/validation_order bug fixes
        # Make sure we have a valid constraint to check against
        if self.constraint is None:
            context.add_error(
                ErrorCode.SCHEMA_INVALID,
                "Not constraint has no sub-constraint to validate against",
                value=value,
                constraint=self
            )
            return False

        # Use an isolated error context to check if the sub-constraint passes
        sub_context = ValidationContext(verbose=context.verbose)
        sub_context.path_parts = context.path_parts.copy()
        sub_context.schema_path_parts = context.schema_path_parts.copy()
        sub_context.root_schema = context.root_schema

        # Propagate any type hints
        for path, type_hint in context.type_hints.items():
            sub_context.add_type_hint(path, type_hint)
        
        # Propagate parent properties
        sub_context.parent_properties = context.parent_properties.copy()
        
        with context.with_schema_path("not"):
            # Check if the constraint is not satisfied
            # If this constraint has a validation order, use it
            sub_result = False
            if hasattr(self.constraint, "validation_order") and getattr(self.constraint, "validation_order"):
                sub_result = True
                for sub_constraint in self.constraint.validation_order:
                    if not sub_constraint.validate(value, sub_context):
                        sub_result = False
                        break
            else:
                sub_result = self.constraint.validate(value, sub_context)
            
            if sub_result:
                context.add_error(
                    ErrorCode.NOT_SCHEMA_MATCHED,
                    "Value should not validate against the schema, but it does",
                    value=value,
                    constraint=self
                )
                return False
        
        # Constraint was not satisfied, which is what we want
        return True

    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"NotConstraint(constraint={self.constraint})"

    def __repr__(self) -> str:
        """Detailed representation of the not constraint."""
        return self.__str__()
