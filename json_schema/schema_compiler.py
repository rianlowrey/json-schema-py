"""
Enhanced schema compiler with dependency-aware constraint building.
"""

from typing import Any, Dict, List, Optional, Union, Set, Callable

from .constraints import (
    Constraint,
    StringConstraint,
    NumberConstraint,
    BooleanConstraint,
    NullConstraint,
    ArrayConstraint,
    ObjectConstraint,
    AllOfConstraint,
    AnyOfConstraint,
    OneOfConstraint,
    NotConstraint,
    EnumConstraint,
    ConstConstraint,
    ReferenceConstraint,
    TypeConstraintImpl,
    CombinedConstraint
)
from .graph import ConstraintDependencyGraph, DependencyNode
from .utils import SchemaKeywords, JsonPointer


class ConstraintBuilder:
    """
    Builds a constraint tree from a JSON Schema using a three-phase approach.

    Phase 1: Create all constraints
    Phase 2: Establish dependencies between constraints
    Phase 3: Build the final constraint tree with dependency information
    """

    def __init__(self):
        """Initialize a new constraint builder."""
        self.constraints = {}  # Path -> Constraint mapping
        self.schema_cache = {}  # Path -> Schema mapping
        self.ref_cache = {}    # Reference path -> Constraint mapping
        self.root_schema = None  # Root schema for reference resolution

        # Dependency graph for constraint ordering
        self.dependency_graph = ConstraintDependencyGraph()

        # Maps to track constraint types
        self.type_constraints = {}  # Path -> (Constraint, JSON type)
        self.logical_constraints = {}  # Path -> (Constraint, logical type)
        self.property_constraints = {}  # Path -> (Constraint, property name)

    def compile(self, schema: Dict[str, Any]) -> Constraint:
        """
        Compile a JSON Schema into a constraint tree.

        Args:
            schema: JSON Schema to compile

        Returns:
            Root constraint of the compiled schema
        """
        # Reset internal state
        self.constraints = {}
        self.schema_cache = {}
        self.ref_cache = {}
        self.root_schema = schema
        self.dependency_graph = ConstraintDependencyGraph()
        self.type_constraints = {}
        self.logical_constraints = {}
        self.property_constraints = {}

        # Phase 1: Cache schema paths and create constraints
        self._cache_schema_paths(schema, "")
        self._create_constraint_tree(schema, "")

        # Phase 2: Establish dependencies between constraints
        self._establish_dependencies()

        # Phase 3: Build the final constraint tree with branch connections
        self._connect_branches()

        # Phase 4: Attach validation order to the root constraint
        root_constraint = self.constraints.get("")
        if root_constraint:
            validation_order = self.dependency_graph.get_validation_order()
            setattr(root_constraint, "validation_order", validation_order)

        # Return the root constraint
        return root_constraint

    def _connect_branches(self):
        """Connect logical operator branches to their parent constraints."""
        # For each path in the constraints dictionary
        for path, constraint in self.constraints.items():
            # Check if this is a logical operator
            if isinstance(constraint, (AllOfConstraint, AnyOfConstraint, OneOfConstraint)):
                # Find child constraints
                operator_type = constraint.__class__.__name__.replace(
                    "Constraint", "").lower()
                operator_prefix = f"{path}/{operator_type}/" if path else f"/{operator_type}/"

                # Collect all child constraints
                child_constraints = []
                i = 0
                while True:
                    child_path = f"{operator_prefix}{i}"
                    if child_path in self.constraints:
                        child_constraints.append(self.constraints[child_path])
                        i += 1
                    else:
                        break

                # Attach child constraints to parent
                if child_constraints:
                    constraint.constraints = child_constraints

            # Special handling for NotConstraint
            elif isinstance(constraint, NotConstraint) and not constraint.constraint:
                # Find the child constraint
                not_path = f"{path}/not" if path else "/not"
                if not_path in self.constraints:
                    constraint.constraint = self.constraints[not_path]

    def _cache_schema_paths(self, schema: Dict[str, Any], path: str) -> None:
        """
        Recursively cache all schemas by their JSON paths.

        Args:
            schema: Schema to process
            path: JSON path to this schema
        """
        # Store this schema at its path
        self.schema_cache[path] = schema

        # Handle properties if it's an object schema
        if SchemaKeywords.PROPERTIES in schema:
            for prop, prop_schema in schema[SchemaKeywords.PROPERTIES].items():
                if isinstance(prop_schema, dict):
                    self._cache_schema_paths(
                        prop_schema, f"{path}/properties/{prop}")

        # Handle additionalProperties if it's an object schema
        if SchemaKeywords.ADDITIONAL_PROPERTIES in schema and isinstance(schema[SchemaKeywords.ADDITIONAL_PROPERTIES], dict):
            self._cache_schema_paths(
                schema[SchemaKeywords.ADDITIONAL_PROPERTIES], f"{path}/additionalProperties")

        # Handle items if it's an array schema
        if SchemaKeywords.ITEMS in schema and isinstance(schema[SchemaKeywords.ITEMS], dict):
            self._cache_schema_paths(
                schema[SchemaKeywords.ITEMS], f"{path}/items")

        # Handle pattern properties if it's an object schema
        if SchemaKeywords.PATTERN_PROPERTIES in schema:
            for pattern, pattern_schema in schema[SchemaKeywords.PATTERN_PROPERTIES].items():
                if isinstance(pattern_schema, dict):
                    self._cache_schema_paths(
                        pattern_schema, f"{path}/patternProperties/{pattern}")

        # Handle property names if it's an object schema
        if SchemaKeywords.PROPERTY_NAMES in schema and isinstance(schema[SchemaKeywords.PROPERTY_NAMES], dict):
            self._cache_schema_paths(
                schema[SchemaKeywords.PROPERTY_NAMES], f"{path}/propertyNames")

        # Handle allOf, anyOf, oneOf, not
        if SchemaKeywords.ALL_OF in schema:
            for i, sub_schema in enumerate(schema[SchemaKeywords.ALL_OF]):
                if isinstance(sub_schema, dict):
                    self._cache_schema_paths(sub_schema, f"{path}/allOf/{i}")

        if SchemaKeywords.ANY_OF in schema:
            for i, sub_schema in enumerate(schema[SchemaKeywords.ANY_OF]):
                if isinstance(sub_schema, dict):
                    self._cache_schema_paths(sub_schema, f"{path}/anyOf/{i}")

        if SchemaKeywords.ONE_OF in schema:
            for i, sub_schema in enumerate(schema[SchemaKeywords.ONE_OF]):
                if isinstance(sub_schema, dict):
                    self._cache_schema_paths(sub_schema, f"{path}/oneOf/{i}")

        if SchemaKeywords.NOT in schema and isinstance(schema[SchemaKeywords.NOT], dict):
            self._cache_schema_paths(schema[SchemaKeywords.NOT], f"{path}/not")

        # Handle definitions
        if "definitions" in schema:
            for def_name, def_schema in schema["definitions"].items():
                if isinstance(def_schema, dict):
                    self._cache_schema_paths(
                        def_schema, f"{path}/definitions/{def_name}")

    def _create_constraint_tree(self, schema: Dict[str, Any], path: str) -> None:
        """
        Recursively create all constraints in the schema.

        Args:
            schema: Schema to process
            path: JSON path to this schema
        """
        # Handle references first
        if SchemaKeywords.REF in schema:
            self._handle_reference(schema, path)
            return

        # Determine the constraint type and create the constraint
        constraint = self._create_constraint(schema, path)
        self.constraints[path] = constraint

        # Add the constraint to the dependency graph
        node = self.dependency_graph.add_constraint(constraint, path)

        # Register the constraint in the appropriate category
        self._categorize_constraint(constraint, path, schema)

        # Process child schemas
        self._process_child_schemas(schema, path, constraint)

    def _categorize_constraint(self, constraint: Constraint, path: str, schema: Dict[str, Any]) -> None:
        """
        Categorize a constraint for dependency tracking.

        Args:
            constraint: Constraint to categorize
            path: Path to the constraint
            schema: Schema that created the constraint
        """
        # Register type constraints
        if SchemaKeywords.TYPE in schema:
            type_value = schema[SchemaKeywords.TYPE]
            if isinstance(type_value, str):
                self.type_constraints[path] = (constraint, type_value)
                # Register in the dependency graph
                self.dependency_graph.add_type_constraint(
                    constraint, path, type_value)

        # Register logical constraints
        if any(op in schema for op in [
            SchemaKeywords.ALL_OF,
            SchemaKeywords.ANY_OF,
            SchemaKeywords.ONE_OF,
            SchemaKeywords.NOT
        ]):
            # Determine the logical operator type
            if SchemaKeywords.ALL_OF in schema:
                logical_type = "allOf"
            elif SchemaKeywords.ANY_OF in schema:
                logical_type = "anyOf"
            elif SchemaKeywords.ONE_OF in schema:
                logical_type = "oneOf"
            elif SchemaKeywords.NOT in schema:
                logical_type = "not"
            else:
                logical_type = "unknown"

            self.logical_constraints[path] = (constraint, logical_type)

    def _create_constraint(self, schema: Dict[str, Any], path: str) -> Constraint:
        """
        Create a constraint for a schema with special handling for root additionalProperties.
        
        Args:
            schema: Schema to create constraint for
            path: JSON path to this schema

        Returns:
            Created constraint
        """
        # Special case for schema with just required properties
        if SchemaKeywords.REQUIRED in schema and (
            len(schema.keys()) == 1 or 
            (len(schema.keys()) == 2 and "description" in schema)
        ):
            return ObjectConstraint(
                properties={},
                required=schema[SchemaKeywords.REQUIRED],
                additional_properties=True,
                pattern_properties={},
                property_names=None,
                min_properties=None,
                max_properties=None,
                dependencies=None
            )
        
        # Special case for root schema with only additionalProperties as a reference
        # This is common in project-type schemas where the root object allows additional
        # properties that conform to a reference
        if path == "" and set(schema.keys()) - set(["$schema", "title", "description", "type", "definitions"]) == {SchemaKeywords.ADDITIONAL_PROPERTIES}:
            if schema.get(SchemaKeywords.TYPE) == "object" and isinstance(schema.get(SchemaKeywords.ADDITIONAL_PROPERTIES), dict):
                ref = schema[SchemaKeywords.ADDITIONAL_PROPERTIES].get(SchemaKeywords.REF)
                if ref and ref.startswith('#/'):
                    # This is a special case - create an object constraint with additionalProperties as a reference
                    return ObjectConstraint(
                        properties={},
                        required=[],
                        additional_properties=None,  # Will set this after reference resolution
                        pattern_properties={},
                        property_names=None,
                        min_properties=None,
                        max_properties=None,
                        dependencies=None
                    )
        
        # Handle logical operators
        if self._has_logical_operators(schema):
            return self._create_logical_constraint(schema, path)

        # Handle enum and const
        if SchemaKeywords.ENUM in schema:
            return EnumConstraint(schema[SchemaKeywords.ENUM])

        if SchemaKeywords.CONST in schema:
            return ConstConstraint(schema[SchemaKeywords.CONST])

        # Determine the constraint type
        constraint_type = self._determine_constraint_type(schema)

        # Create an appropriate constraint based on the determined type
        if constraint_type == "string":
            return self._create_string_constraint(schema)
        elif constraint_type == "number" or constraint_type == "integer":
            return self._create_number_constraint(schema)
        elif constraint_type == "array":
            return ArrayConstraint(
                items=None,  # Will be connected later
                min_items=schema.get(SchemaKeywords.MIN_ITEMS),
                max_items=schema.get(SchemaKeywords.MAX_ITEMS),
                unique_items=schema.get(SchemaKeywords.UNIQUE_ITEMS, False)
            )
        elif constraint_type == "object":
            return ObjectConstraint(
                properties={},  # Will be populated later
                required=schema.get(SchemaKeywords.REQUIRED, []),
                additional_properties=schema.get(SchemaKeywords.ADDITIONAL_PROPERTIES, True),
                pattern_properties={},  # Will be populated later
                property_names=None,  # Will be connected later
                min_properties=schema.get(SchemaKeywords.MIN_PROPERTIES),
                max_properties=schema.get(SchemaKeywords.MAX_PROPERTIES),
                dependencies=schema.get(SchemaKeywords.DEPENDENCIES)
            )
        elif constraint_type == "boolean":
            return BooleanConstraint()
        elif constraint_type == "null":
            return NullConstraint()
        elif constraint_type == "multiple":
            return TypeConstraintImpl(schema[SchemaKeywords.TYPE])

        # If there are no constraints, return a constraint that accepts anything
        return CombinedConstraint([])

    def _process_child_schemas(self, schema: Dict[str, Any], path: str, constraint: Constraint) -> None:
        """
        Process child schemas and register dependencies.

        Args:
            schema: Parent schema
            path: Path to the parent schema
            constraint: Parent constraint
        """
        # Process logical operators
        self._process_logical_schemas(schema, path, constraint)

        # Process array and object specific schemas
        self._process_type_specific_schemas(schema, path, constraint)

    def _process_logical_schemas(self, schema: Dict[str, Any], path: str, constraint: Constraint) -> None:
        """
        Process logical operator schemas.

        Args:
            schema: Schema with logical operators
            path: Path to the schema
            constraint: Parent constraint
        """
        # Extract the logical constraint from combined constraint if needed
        logical_constraint = constraint
        if isinstance(constraint, CombinedConstraint):
            # Find the logical constraint in the combined constraints
            for c in constraint.constraints:
                if isinstance(c, (AllOfConstraint, AnyOfConstraint, OneOfConstraint, NotConstraint)):
                    logical_constraint = c
                    break

        # For AllOf, process sub-schemas
        if SchemaKeywords.ALL_OF in schema and isinstance(logical_constraint, AllOfConstraint):
            all_of_branches = []
            for i, sub_schema in enumerate(schema[SchemaKeywords.ALL_OF]):
                sub_path = f"{path}/allOf/{i}"
                self._create_constraint_tree(sub_schema, sub_path)
                all_of_branches.append(self.constraints[sub_path])

            # Directly attach branches to the constraint
            logical_constraint.constraints = all_of_branches

        # For AnyOf, process sub-schemas
        if SchemaKeywords.ANY_OF in schema and isinstance(logical_constraint, AnyOfConstraint):
            any_of_branches = []
            for i, sub_schema in enumerate(schema[SchemaKeywords.ANY_OF]):
                sub_path = f"{path}/anyOf/{i}"
                self._create_constraint_tree(sub_schema, sub_path)
                any_of_branches.append(self.constraints[sub_path])

            # Directly attach branches to the constraint
            logical_constraint.constraints = any_of_branches

        # For OneOf, process sub-schemas
        if SchemaKeywords.ONE_OF in schema and isinstance(logical_constraint, OneOfConstraint):
            one_of_branches = []
            for i, sub_schema in enumerate(schema[SchemaKeywords.ONE_OF]):
                sub_path = f"{path}/oneOf/{i}"
                self._create_constraint_tree(sub_schema, sub_path)
                one_of_branches.append(self.constraints[sub_path])

            # Directly attach branches to the constraint
            logical_constraint.constraints = one_of_branches

        # For Not, process the sub-schema
        if SchemaKeywords.NOT in schema and isinstance(logical_constraint, NotConstraint):
            not_path = f"{path}/not"
            self._create_constraint_tree(schema[SchemaKeywords.NOT], not_path)

            # Directly attach the branch to the constraint
            logical_constraint.constraint = self.constraints[not_path]

            # Register dependency - NOT constraints depend on type constraints
            for type_path, (type_constraint, _) in self.type_constraints.items():
                if type_path.startswith(path) and type_path != not_path:
                    self.dependency_graph.add_dependency(not_path, type_path)

    def _process_array_schema(self, array_schema: List[Dict[str, Any]], path: str,
                              operator: str, constraint: Constraint) -> None:
        """
        Process an array of schemas for logical operators.

        Args:
            array_schema: List of schemas
            path: Path to the parent schema
            operator: Logical operator name
            constraint: Parent constraint
        """
        # Process each schema in the array
        for i, sub_schema in enumerate(array_schema):
            sub_path = f"{path}/{operator}/{i}"
            self._create_constraint_tree(sub_schema, sub_path)

            # Add to the constraint's list if it has one
            if hasattr(constraint, "constraints"):
                constraint.constraints.append(self.constraints[sub_path])

            # Register dependency
            self.dependency_graph.add_dependency(sub_path, path)

    def _process_type_specific_schemas(self, schema: Dict[str, Any], path: str, constraint: Constraint) -> None:
        """
        Process type-specific child schemas.

        Args:
            schema: Schema with type-specific properties
            path: Path to the schema
            constraint: Parent constraint
        """
        # For Array constraints, process items schema
        if isinstance(constraint, ArrayConstraint) and SchemaKeywords.ITEMS in schema:
            items_path = f"{path}/items"
            self._create_constraint_tree(
                schema[SchemaKeywords.ITEMS], items_path)
            constraint.items = self.constraints[items_path]

            # Register dependency
            self.dependency_graph.add_dependency(items_path, path)

        # For Object constraints, process properties and other object-specific schemas
        if isinstance(constraint, ObjectConstraint):
            self._process_object_schemas(schema, path, constraint)

    def _process_object_schemas(self, schema: Dict[str, Any], path: str, constraint: ObjectConstraint) -> None:
        """
        Process object-specific schemas with better additionalProperties handling.
        
        Args:
            schema: Schema with object properties
            path: Path to the schema
            constraint: Object constraint
        """
        # Process properties
        if SchemaKeywords.PROPERTIES in schema:
            for prop_name, prop_schema in schema[SchemaKeywords.PROPERTIES].items():
                prop_path = f"{path}/properties/{prop_name}"
                self._create_constraint_tree(prop_schema, prop_path)
                constraint.properties[prop_name] = self.constraints[prop_path]

                # Register property constraint
                self.property_constraints[prop_path] = (self.constraints[prop_path], prop_name)

                # Register dependency
                self.dependency_graph.add_dependency(prop_path, path)

        # Process required properties
        if SchemaKeywords.REQUIRED in schema:
            constraint.required = schema[SchemaKeywords.REQUIRED]

        # Process additionalProperties
        if SchemaKeywords.ADDITIONAL_PROPERTIES in schema:
            if isinstance(schema[SchemaKeywords.ADDITIONAL_PROPERTIES], dict):
                # Handle additionalProperties as a schema
                add_props_path = f"{path}/additionalProperties"
                
                # Special handling for references
                if SchemaKeywords.REF in schema[SchemaKeywords.ADDITIONAL_PROPERTIES]:
                    ref = schema[SchemaKeywords.ADDITIONAL_PROPERTIES][SchemaKeywords.REF]
                    # Create reference constraint
                    self._create_constraint_tree(schema[SchemaKeywords.ADDITIONAL_PROPERTIES], add_props_path)
                    constraint.additional_properties = self.constraints[add_props_path]
                else:
                    # Regular schema for additionalProperties
                    self._create_constraint_tree(schema[SchemaKeywords.ADDITIONAL_PROPERTIES], add_props_path)
                    constraint.additional_properties = self.constraints[add_props_path]
                
                # Register dependency
                self.dependency_graph.add_dependency(add_props_path, path)
            else:
                # Handle boolean value
                constraint.additional_properties = schema[SchemaKeywords.ADDITIONAL_PROPERTIES]

        # Process pattern properties
        if SchemaKeywords.PATTERN_PROPERTIES in schema:
            for pattern, pattern_schema in schema[SchemaKeywords.PATTERN_PROPERTIES].items():
                pattern_path = f"{path}/patternProperties/{pattern}"
                self._create_constraint_tree(pattern_schema, pattern_path)
                constraint.pattern_properties[pattern] = self.constraints[pattern_path]

                # Register dependency
                self.dependency_graph.add_dependency(pattern_path, path)

        # Process property names
        if SchemaKeywords.PROPERTY_NAMES in schema:
            prop_names_path = f"{path}/propertyNames"
            self._create_constraint_tree(schema[SchemaKeywords.PROPERTY_NAMES], prop_names_path)
            constraint.property_names = self.constraints[prop_names_path]

            # Register dependency
            self.dependency_graph.add_dependency(prop_names_path, path)

        # Process min/max properties
        if SchemaKeywords.MIN_PROPERTIES in schema:
            constraint.min_properties = schema[SchemaKeywords.MIN_PROPERTIES]

        if SchemaKeywords.MAX_PROPERTIES in schema:
            constraint.max_properties = schema[SchemaKeywords.MAX_PROPERTIES]

        # Process dependencies
        if SchemaKeywords.DEPENDENCIES in schema:
            constraint.dependencies = schema[SchemaKeywords.DEPENDENCIES]

    def _handle_reference(self, schema: Dict[str, Any], path: str) -> None:
        """
        Handle a reference schema with improved resolution.

        Args:
            schema: Schema with a reference
            path: Path to this schema
        """
        ref = schema[SchemaKeywords.REF]

        # Check if we've already seen this reference
        if ref in self.ref_cache:
            ref_constraint = self.ref_cache[ref]
            self.constraints[path] = ref_constraint
            return

        # Try to resolve the reference
        try:
            # Get the schema this reference points to
            if ref.startswith('#/'):
                # Get the referenced schema from our cache
                ref_path = ref[1:]  # Remove the leading #
                ref_schema = self._resolve_json_pointer(
                    self.root_schema, ref_path)

                # Create a reference constraint
                ref_constraint = ReferenceConstraint(
                    ref, self._create_resolver())
                self.constraints[path] = ref_constraint
                self.ref_cache[ref] = ref_constraint

                # Create a constraint for the referenced schema
                ref_constraint_path = ref[1:]  # Use the ref as the path

                # Check if we've already processed this schema
                if ref_constraint_path in self.constraints:
                    # Use the existing constraint
                    ref_constraint.resolved_constraint = self.constraints[ref_constraint_path]
                else:
                    # Create the constraint now
                    self._create_constraint_tree(
                        ref_schema, ref_constraint_path)
                    ref_constraint.resolved_constraint = self.constraints[ref_constraint_path]

            else:
                # External references not supported
                raise ValueError(f"External references not supported: {ref}")

        except ValueError as e:
            # Reference could not be resolved, the validator will handle this
            print(f"Warning: Failed to resolve reference: {e}")
            # Create a placeholder reference constraint
            ref_constraint = ReferenceConstraint(ref, None)
            self.constraints[path] = ref_constraint
            self.ref_cache[ref] = ref_constraint

    def _establish_dependencies(self) -> None:
        """Establish dependencies between constraints based on their hierarchical structure and types."""
        # Capture parent-child relationships
        parent_child_map = {}  # path -> [child_paths]

        # Build parent-child map
        for path in self.constraints:
            if "/" in path:
                parent_path = path.rsplit("/", 1)[0]
                if parent_path not in parent_child_map:
                    parent_child_map[parent_path] = []
                parent_child_map[parent_path].append(path)

        # For each parent, establish dependencies to children
        for parent_path, child_paths in parent_child_map.items():
            if parent_path in self.constraints:
                parent = self.constraints[parent_path]

                # Object property constraints
                if isinstance(parent, ObjectConstraint):
                    for child_path in child_paths:
                        # Don't create hierarchy dependencies for object properties
                        # They should be validated by the object constraint itself
                        pass

                # Array item constraints
                elif isinstance(parent, ArrayConstraint):
                    for child_path in child_paths:
                        if "items" in child_path:
                            # Don't create hierarchy dependencies for array items
                            # They should be validated by the array constraint itself
                            pass

                # Other types of parent-child relationships
                else:
                    for child_path in child_paths:
                        self.dependency_graph.add_dependency(
                            child_path, parent_path)

        # For each logical constraint, add dependencies on relevant type constraints
        for logical_path, (logical_constraint, logical_type) in self.logical_constraints.items():
            # Find parent path
            parent_path = logical_path.rsplit(
                '/', 1)[0] if '/' in logical_path else ""

            # Find type constraints in the same parent scope
            for type_path, (type_constraint, json_type) in self.type_constraints.items():
                if type_path.startswith(parent_path):
                    # Type constraint is in the same scope, establish dependency
                    self.dependency_graph.add_dependency(
                        logical_path, type_path)

            # Special handling for NOT constraints
            if logical_type == "not":
                # NOT constraints should be validated last
                for other_path in self.constraints:
                    if other_path != logical_path and other_path.startswith(parent_path):
                        self.dependency_graph.add_dependency(
                            logical_path, other_path)

    def _resolve_json_pointer(self, document: Any, pointer: str) -> Any:
        """
        Resolve a JSON Pointer within a document.

        Args:
            document: The JSON document
            pointer: JSON Pointer string

        Returns:
            The referenced value

        Raises:
            ValueError: If the pointer cannot be resolved
        """
        # Try using our schema cache first
        if pointer in self.schema_cache:
            return self.schema_cache[pointer]

        # Fall back to the JsonPointer class
        try:
            return JsonPointer.resolve(document, pointer)
        except ValueError as e:
            raise ValueError(
                f"Failed to resolve reference '{pointer}': {str(e)}")

    def _has_logical_operators(self, schema: Dict[str, Any]) -> bool:
        """
        Check if a schema has logical operators.

        Args:
            schema: Schema to check

        Returns:
            True if the schema has logical operators
        """
        logical_operators = [
            SchemaKeywords.ALL_OF,
            SchemaKeywords.ANY_OF,
            SchemaKeywords.ONE_OF,
            SchemaKeywords.NOT
        ]
        return any(op in schema for op in logical_operators)

    def _create_logical_constraint(self, schema: Dict[str, Any], path: str) -> Constraint:
        """
        Create a logical constraint.

        Args:
            schema: Schema with logical operators
            path: Path to this schema

        Returns:
            Logical constraint
        """
        # Determine which logical operators are present
        has_all_of = SchemaKeywords.ALL_OF in schema
        has_any_of = SchemaKeywords.ANY_OF in schema
        has_one_of = SchemaKeywords.ONE_OF in schema
        has_not = SchemaKeywords.NOT in schema

        # Create a list of constraints
        constraints = []

        # Create type constraint first if present
        if SchemaKeywords.TYPE in schema:
            type_value = schema[SchemaKeywords.TYPE]
            if isinstance(type_value, list):
                constraints.append(TypeConstraintImpl(type_value))
            else:
                # Create appropriate type-specific constraint
                if type_value == "string":
                    constraints.append(StringConstraint())
                elif type_value == "integer":
                    constraints.append(NumberConstraint(integer_only=True))
                elif type_value == "number":
                    constraints.append(NumberConstraint())
                elif type_value == "boolean":
                    constraints.append(BooleanConstraint())
                elif type_value == "null":
                    constraints.append(NullConstraint())
                elif type_value == "array":
                    constraints.append(ArrayConstraint(None))
                elif type_value == "object":
                    constraints.append(ObjectConstraint(
                        properties={},
                        required=schema.get(SchemaKeywords.REQUIRED, []),
                        additional_properties=schema.get(
                            SchemaKeywords.ADDITIONAL_PROPERTIES, True),
                        pattern_properties={}
                    ))

        # Create a single logical constraint based on the schema
        logical_constraint = None
        if has_all_of:
            logical_constraint = AllOfConstraint([])
        elif has_any_of:
            logical_constraint = AnyOfConstraint([])
        elif has_one_of:
            logical_constraint = OneOfConstraint([])
        elif has_not:
            logical_constraint = NotConstraint(None)

        # If we have a logical constraint and other constraints, combine them
        if logical_constraint and constraints:
            return CombinedConstraint(constraints + [logical_constraint])

        # If we only have a logical constraint, return it directly
        if logical_constraint:
            return logical_constraint

        # If we only have regular constraints, combine them
        if constraints:
            return CombinedConstraint(constraints) if len(constraints) > 1 else constraints[0]

        # If there are no constraints, return an empty combined constraint
        return CombinedConstraint([])

    def _determine_constraint_type(self, schema: Dict[str, Any]) -> str:
        """
        Determine the most appropriate constraint type for a schema.

        Args:
            schema: Schema to analyze

        Returns:
            Constraint type ("string", "number", "array", "object", etc.)
        """
        # Check for explicit type declaration
        if SchemaKeywords.TYPE in schema:
            type_value = schema[SchemaKeywords.TYPE]
            if isinstance(type_value, list):
                # For multiple types, we need special handling
                return "multiple"
            return type_value

        # Infer type from type-specific keywords
        # Array indicators
        if any(key in schema for key in [
            SchemaKeywords.ITEMS,
            SchemaKeywords.MIN_ITEMS,
            SchemaKeywords.MAX_ITEMS,
            SchemaKeywords.UNIQUE_ITEMS
        ]):
            return "array"

        # Object indicators
        if any(key in schema for key in [
            SchemaKeywords.PROPERTIES,
            SchemaKeywords.REQUIRED,
            SchemaKeywords.ADDITIONAL_PROPERTIES,
            SchemaKeywords.PATTERN_PROPERTIES,
            SchemaKeywords.PROPERTY_NAMES,
            SchemaKeywords.MIN_PROPERTIES,
            SchemaKeywords.MAX_PROPERTIES,
            SchemaKeywords.DEPENDENCIES
        ]):
            return "object"

        # String indicators
        if any(key in schema for key in [
            SchemaKeywords.MIN_LENGTH,
            SchemaKeywords.MAX_LENGTH,
            SchemaKeywords.PATTERN
        ]):
            return "string"

        # Number indicators
        if any(key in schema for key in [
            SchemaKeywords.MINIMUM,
            SchemaKeywords.MAXIMUM,
            SchemaKeywords.EXCLUSIVE_MINIMUM,
            SchemaKeywords.EXCLUSIVE_MAXIMUM,
            SchemaKeywords.MULTIPLE_OF
        ]):
            return "number"

        # If we can't determine a specific type, default to "any"
        return "any"

    def _create_string_constraint(self, schema: Dict[str, Any]) -> StringConstraint:
        """
        Create a string constraint.

        Args:
            schema: Schema containing string constraints

        Returns:
            StringConstraint for string validation
        """
        min_length = schema.get(SchemaKeywords.MIN_LENGTH)
        max_length = schema.get(SchemaKeywords.MAX_LENGTH)
        pattern = schema.get(SchemaKeywords.PATTERN)

        return StringConstraint(
            min_length=min_length,
            max_length=max_length,
            pattern=pattern
        )

    def _create_number_constraint(self, schema: Dict[str, Any]) -> NumberConstraint:
        """
        Create a number constraint.

        Args:
            schema: Schema containing number constraints

        Returns:
            NumberConstraint for number validation
        """
        minimum = schema.get(SchemaKeywords.MINIMUM)
        maximum = schema.get(SchemaKeywords.MAXIMUM)
        exclusive_minimum = schema.get(SchemaKeywords.EXCLUSIVE_MINIMUM, False)
        exclusive_maximum = schema.get(SchemaKeywords.EXCLUSIVE_MAXIMUM, False)
        multiple_of = schema.get(SchemaKeywords.MULTIPLE_OF)
        integer_only = schema.get(SchemaKeywords.TYPE) == "integer"

        return NumberConstraint(
            minimum=minimum,
            maximum=maximum,
            exclusive_minimum=exclusive_minimum,
            exclusive_maximum=exclusive_maximum,
            multiple_of=multiple_of,
            integer_only=integer_only
        )

    def _create_resolver(self) -> Callable[[str], Constraint]:
        """
        Create a resolver function for JSON Schema references.

        Returns:
            Function that resolves references to constraint objects
        """
        def resolver(ref: str) -> Constraint:
            if not ref.startswith('#/'):
                raise ValueError(f"External references not supported: {ref}")

            # Try to get from cache first
            if ref in self.ref_cache and self.ref_cache[ref].resolved_constraint is not None:
                return self.ref_cache[ref].resolved_constraint

            # Resolve the reference from the root schema
            try:
                ref_path = ref[1:]  # Remove the leading #
                ref_schema = self._resolve_json_pointer(
                    self.root_schema, ref_path)

                # Create a new builder just for this reference
                temp_builder = ConstraintBuilder()
                temp_builder.root_schema = self.root_schema
                constraint = temp_builder._create_constraint(ref_schema, "")

                return constraint
            except ValueError as e:
                raise ValueError(
                    f"Failed to resolve reference '{ref}': {str(e)}")

        return resolver


# Create a SchemaCompiler class that uses the ConstraintBuilder internally
class SchemaCompiler:
    """
    Compiles JSON Schemas into constraint trees.

    This class is responsible for parsing a JSON Schema and
    creating a tree of constraint objects that can be used for
    efficient validation.
    """

    def __init__(self):
        """Initialize a new schema compiler."""
        self.builder = ConstraintBuilder()

    def compile(self, schema: Dict[str, Any]) -> Constraint:
        """
        Compile a JSON Schema into a constraint tree.

        Args:
            schema: JSON Schema to compile

        Returns:
            Root constraint of the compiled schema
        """
        return self.builder.compile(schema)
