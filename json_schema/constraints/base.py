"""
Base constraint classes for the Enhanced JSON Schema Validator.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Set

from ..api import ValidationError, ErrorCode
from ..utils import JsonPointer


class ValidationContext:
    """
    Context for validation operations.
    
    This class maintains state during the validation process,
    including the current path, error collection, and type hints.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize a new validation context.
        
        Args:
            verbose: Whether to include additional details in errors
        """
        self.errors: List[ValidationError] = []
        self.path_parts: List[str] = []
        self.schema_path_parts: List[str] = []
        self.verbose = verbose
        self.type_hints: Dict[str, str] = {}
        self.root_schema: Optional[Dict[str, Any]] = None
        self.parent_properties: Set[str] = set()  # Track properties defined in parent schemas
        
    @property
    def path(self) -> str:
        """
        Get the current JSON Pointer path.
        
        Returns:
            JSON Pointer string for the current path
        """
        return JsonPointer.from_parts(self.path_parts)
        
    @property
    def schema_path(self) -> str:
        """
        Get the current schema JSON Pointer path.
        
        Returns:
            JSON Pointer string for the current schema path
        """
        return JsonPointer.from_parts(self.schema_path_parts)
        
    def push_path(self, part: Any) -> None:
        """
        Push a path part onto the current path.
        
        Args:
            part: Path segment to add
        """
        self.path_parts.append(str(part))
        
    def pop_path(self) -> None:
        """Remove the last path part from the current path."""
        if self.path_parts:
            self.path_parts.pop()
            
    def push_schema_path(self, part: Any) -> None:
        """
        Push a path part onto the current schema path.
        
        Args:
            part: Path segment to add
        """
        self.schema_path_parts.append(str(part))
        
    def pop_schema_path(self) -> None:
        """Remove the last path part from the current schema path."""
        if self.schema_path_parts:
            self.schema_path_parts.pop()
            
    def add_error(self, 
                code: ErrorCode, 
                message: str, 
                value: Any = None,
                constraint: Any = None) -> None:
        """
        Add a validation error to the context.
        
        Args:
            code: Error code
            message: Error message
            value: Value that failed validation
            constraint: Constraint that was violated
        """
        error = ValidationError(
            code=code,
            path=self.path,
            message=message,
            schema_path=self.schema_path,
            value=value,
            constraint=constraint
        )
        self.errors.append(error)
        
    def with_path(self, part: Any):
        """
        Context manager for adding a path part temporarily.
        
        Args:
            part: Path segment to add
            
        Returns:
            Context manager
        """
        return PathContext(self, part)
        
    def with_schema_path(self, part: Any):
        """
        Context manager for adding a schema path part temporarily.
        
        Args:
            part: Path segment to add
            
        Returns:
            Context manager
        """
        return SchemaPathContext(self, part)
        
    def get_type_hint(self, path: str) -> Optional[str]:
        """
        Get a type hint for a path.
        
        Args:
            path: JSON Pointer path
            
        Returns:
            Type hint if available, otherwise None
        """
        return self.type_hints.get(path)
        
    def add_type_hint(self, path: str, type_hint: str) -> None:
        """
        Add a type hint for a path.
        
        Args:
            path: JSON Pointer path
            type_hint: Type hint to add
        """
        self.type_hints[path] = type_hint
    
    def add_parent_property(self, property_name: str) -> None:
        """
        Add a property name to the parent properties set.
        
        Args:
            property_name: Name of property defined in parent schema
        """
        self.parent_properties.add(property_name)
    
    def add_parent_properties(self, property_names: Set[str]) -> None:
        """
        Add multiple property names to the parent properties set.
        
        Args:
            property_names: Set of property names defined in parent schema
        """
        self.parent_properties.update(property_names)
    
    def __str__(self) -> str:
        """String representation of the validation context."""
        return f"ValidationContext(path={self.path}, errors={len(self.errors)})"


class PathContext:
    """Context manager for temporarily adding a path part."""
    
    def __init__(self, context: ValidationContext, part: Any):
        """
        Initialize a new path context.
        
        Args:
            context: Validation context
            part: Path segment to add
        """
        self.context = context
        self.part = part
        
    def __enter__(self):
        """Add the path part when entering the context."""
        self.context.push_path(self.part)
        return self.context
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove the path part when exiting the context."""
        self.context.pop_path()


class SchemaPathContext:
    """Context manager for temporarily adding a schema path part."""
    
    def __init__(self, context: ValidationContext, part: Any):
        """
        Initialize a new schema path context.
        
        Args:
            context: Validation context
            part: Path segment to add
        """
        self.context = context
        self.part = part
        
    def __enter__(self):
        """Add the schema path part when entering the context."""
        self.context.push_schema_path(self.part)
        return self.context
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove the schema path part when exiting the context."""
        self.context.pop_schema_path()


class Constraint(ABC):
    """
    Base class for all schema constraints.
    
    This is the foundation of the constraint hierarchy, defining
    the interface for all constraint types.
    """
    
    @abstractmethod
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this constraint.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the constraint."""
        return f"{self.__class__.__name__}"
    
    def __repr__(self) -> str:
        """Detailed representation of the constraint."""
        return self.__str__()


class TypeConstraint(Constraint, ABC):
    """
    Base class for type-specific constraints.
    
    Type constraints validate values of a specific type.
    """
    
    @property
    @abstractmethod
    def json_type(self) -> str:
        """
        Get the JSON Schema type for this constraint.
        
        Returns:
            JSON Schema type name
        """
        pass
    
    def validate(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate a value against this type constraint.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        # First check if the value has the correct type
        if not self._validate_type(value, context):
            return False
            
        # If the type is correct, perform type-specific validation
        return self._validate_type_specific(value, context)
    
    def _validate_type(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate that the value has the correct type.
        
        Args:
            value: Value to validate
            context: Validation context
            
        Returns:
            True if the value has the correct type, False otherwise
        """
        # Map JSON type to Python type for validation
        expected_type = self.json_type
        
        if expected_type == "string" and not isinstance(value, str):
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected string, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
        elif expected_type == "number" and not (isinstance(value, (int, float)) and not isinstance(value, bool)):
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected number, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
        elif expected_type == "integer" and not (isinstance(value, int) and not isinstance(value, bool)):
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected integer, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
        elif expected_type == "boolean" and not isinstance(value, bool):
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected boolean, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
        elif expected_type == "array" and not isinstance(value, list):
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected array, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
        elif expected_type == "object" and not isinstance(value, dict):
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected object, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
        elif expected_type == "null" and value is not None:
            context.add_error(
                ErrorCode.TYPE_ERROR,
                f"Expected null, got {type(value).__name__}",
                value=value,
                constraint=self
            )
            return False
            
        return True
    
    @abstractmethod
    def _validate_type_specific(self, value: Any, context: ValidationContext) -> bool:
        """
        Validate type-specific constraints.
        
        This method is called after the type validation has passed
        and should implement the type-specific validation logic.
        
        Args:
            value: Value to validate (guaranteed to be of the correct type)
            context: Validation context
            
        Returns:
            True if validation succeeds, False otherwise
        """
        pass
    
    def accepts_type(self, json_type: str) -> bool:
        """
        Check if this constraint accepts a specific JSON type.
        
        Args:
            json_type: JSON Schema type name
            
        Returns:
            True if this constraint accepts the type
        """
        return json_type == self.json_type
