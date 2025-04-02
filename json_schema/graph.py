"""
Constraint dependency model classes.

This module provides classes for modeling the dependency relationships
between constraints and determining their proper validation order.
"""

from typing import Dict, List, Set, Any, Optional, TypeVar, Generic

from .constraints import Constraint, ValidationContext

# Type variable for the node class
T = TypeVar('T')


class DependencyNode(Generic[T]):
    """
    A node in a dependency graph.

    Each node contains an item and its dependencies.
    """

    def __init__(self, item: T, key: str):
        """
        Initialize a new dependency node.

        Args:
            item: The item this node contains
            key: A unique identifier for this node
        """
        self.item = item
        self.key = key
        self.dependencies: Set[DependencyNode[T]] = set()
        self.dependents: Set[DependencyNode[T]] = set()

    def add_dependency(self, node: 'DependencyNode[T]') -> None:
        """
        Add a dependency to this node.

        Args:
            node: Node this node depends on
        """
        if node not in self.dependencies:
            self.dependencies.add(node)
            node.dependents.add(self)

    def remove_dependency(self, node: 'DependencyNode[T]') -> None:
        """
        Remove a dependency from this node.

        Args:
            node: Node to remove as a dependency
        """
        if node in self.dependencies:
            self.dependencies.remove(node)
            node.dependents.remove(self)

    def __repr__(self) -> str:
        """Detailed representation of the node."""
        return f"DependencyNode(key={self.key}, item={self.item}, dependencies={len(self.dependencies)})"


class DependencyGraph(Generic[T]):
    """
    A graph representing dependency relationships between items.

    This graph can be used to determine the order in which items should
    be processed based on their dependencies.
    """

    def __init__(self):
        """Initialize a new dependency graph."""
        self.nodes: Dict[str, DependencyNode[T]] = {}

    def add_node(self, item: T, key: str) -> DependencyNode[T]:
        """
        Add a node to the graph.

        Args:
            item: The item to add
            key: A unique identifier for the node

        Returns:
            The created node
        """
        if key in self.nodes:
            return self.nodes[key]

        node = DependencyNode(item, key)
        self.nodes[key] = node
        return node

    def add_dependency(self, dependent_key: str, dependency_key: str) -> None:
        """
        Add a dependency relationship between two nodes.

        Args:
            dependent_key: Key of the dependent node
            dependency_key: Key of the dependency node
        """
        if dependent_key not in self.nodes or dependency_key not in self.nodes:
            return

        dependent = self.nodes[dependent_key]
        dependency = self.nodes[dependency_key]
        dependent.add_dependency(dependency)

    def topological_sort(self) -> List[T]:
        """
        Sort the items in topological order.

        Returns:
            List of items in dependency order
        """
        result: List[T] = []
        visited: Set[str] = set()
        temp_visited: Set[str] = set()

        def visit(node: DependencyNode[T]) -> None:
            """
            Visit a node and its dependencies recursively.

            Args:
                node: Node to visit
            """
            if node.key in visited:
                return
            if node.key in temp_visited:
                # Cyclic dependency detected
                return

            temp_visited.add(node.key)

            # Visit dependencies first
            for dependency in node.dependencies:
                visit(dependency)

            temp_visited.remove(node.key)
            visited.add(node.key)
            result.append(node.item)

        # Visit all nodes
        for node in self.nodes.values():
            if node.key not in visited:
                visit(node)

        return result


class ConstraintDependencyGraph:
    """
    A specialized dependency graph for constraints.

    This graph automatically determines dependencies between constraints
    based on their types and relationships.
    """

    def __init__(self):
        """Initialize a new constraint dependency graph."""
        self.graph = DependencyGraph[Constraint]()
        self.type_nodes: Dict[str, DependencyNode[Constraint]] = {}

    def add_constraint(self, constraint: Constraint, path: str) -> DependencyNode[Constraint]:
        """
        Add a constraint to the graph.

        Args:
            constraint: Constraint to add
            path: JSON path to the constraint

        Returns:
            The node for the added constraint
        """
        return self.graph.add_node(constraint, path)

    def add_type_constraint(self, constraint: Constraint, path: str, json_type: str) -> None:
        """
        Add a type constraint to the graph.

        Args:
            constraint: Type constraint to add
            path: JSON path to the constraint
            json_type: JSON Schema type
        """
        node = self.add_constraint(constraint, path)
        self.type_nodes[json_type] = node

    def add_constraint_with_dependencies(self, constraint: Constraint, path: str,
                                         depends_on_types: Optional[List[str]] = None) -> None:
        """
        Add a constraint with dependencies on specific types.

        Args:
            constraint: Constraint to add
            path: JSON path to the constraint
            depends_on_types: List of JSON Schema types this constraint depends on
        """
        node = self.add_constraint(constraint, path)

        if depends_on_types:
            for type_name in depends_on_types:
                if type_name in self.type_nodes:
                    node.add_dependency(self.type_nodes[type_name])

    def add_dependency(self, dependent_path: str, dependency_path: str) -> None:
        """
        Add a dependency between two constraints.

        Args:
            dependent_path: Path of the dependent constraint
            dependency_path: Path of the dependency constraint
        """
        self.graph.add_dependency(dependent_path, dependency_path)

    def get_validation_order(self) -> List[Constraint]:
        """
        Get constraints in topological order for validation.

        Returns:
            List of constraints in dependency order
        """
        return self.graph.topological_sort()
