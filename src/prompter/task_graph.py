"""Task dependency graph management for parallel execution.

This module implements a Directed Acyclic Graph (DAG) for managing task dependencies
and provides algorithms for validation, topological sorting, and parallel execution scheduling.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the task dependency graph."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = cycle_path
        super().__init__(
            f"Cycle detected in task dependencies: {' -> '.join(cycle_path)}"
        )


@dataclass
class GraphNode:
    """Represents a node in the task dependency graph."""

    name: str
    task: Any  # Will be TaskConfig when integrated
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    in_degree: int = 0
    out_degree: int = 0

    # Resource requirements (for future resource management)
    cpu_required: float = 1.0
    memory_required: int = 512  # MB
    priority: int = 0
    exclusive: bool = False  # If True, task must run alone


class TaskGraph:
    """Manages task dependencies as a directed acyclic graph."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self._adjacency_list: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency_list: dict[str, set[str]] = defaultdict(set)
        self._is_validated = False
        self._topological_order: list[str] = []

    def add_task(
        self, name: str, task: Any, dependencies: list[str] | None = None
    ) -> None:
        """Add a task to the graph with its dependencies."""
        if name in self.nodes:
            raise ValueError(f"Task '{name}' already exists in the graph")

        # Create node
        node = GraphNode(name=name, task=task)
        self.nodes[name] = node

        # Add dependencies
        if dependencies:
            for dep in dependencies:
                self.add_dependency(name, dep)

        self._is_validated = False

    def add_dependency(self, task_name: str, dependency_name: str) -> None:
        """Add a dependency relationship between tasks."""
        if task_name not in self.nodes:
            raise ValueError(f"Task '{task_name}' not found in graph")

        # Allow forward references - dependency might be added later
        self.nodes[task_name].dependencies.add(dependency_name)
        self._adjacency_list[dependency_name].add(task_name)
        self._reverse_adjacency_list[task_name].add(dependency_name)

        # Update in/out degrees if dependency exists
        if dependency_name in self.nodes:
            self.nodes[dependency_name].dependents.add(task_name)
            self.nodes[task_name].in_degree += 1
            self.nodes[dependency_name].out_degree += 1

        self._is_validated = False

    def validate(self) -> None:
        """Validate the graph structure (check for cycles and missing dependencies)."""
        # Check for missing dependencies
        missing_deps = []
        for name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    missing_deps.append((name, dep))

        if missing_deps:
            errors = [
                f"Task '{task}' depends on undefined task '{dep}'"
                for task, dep in missing_deps
            ]
            raise ValueError("Missing dependencies:\\n" + "\\n".join(errors))

        # Check for cycles using DFS
        self._detect_cycles()

        # Compute topological order
        self._compute_topological_order()

        self._is_validated = True

    def _detect_cycles(self) -> None:
        """Detect cycles in the graph using DFS with three-color marking."""
        # Colors: WHITE (0) = unvisited, GRAY (1) = visiting, BLACK (2) = visited
        colors = dict.fromkeys(self.nodes, 0)

        def dfs(node: str, path: list[str]) -> None:
            colors[node] = 1  # Mark as visiting (GRAY)
            path.append(node)

            for neighbor in self._adjacency_list[node]:
                if colors[neighbor] == 1:  # Found a back edge (cycle)
                    # Extract the cycle path
                    cycle_start = path.index(neighbor)
                    cycle = [*path[cycle_start:], neighbor]
                    raise CycleDetectedError(cycle)
                if colors[neighbor] == 0:  # Unvisited
                    dfs(neighbor, path.copy())

            colors[node] = 2  # Mark as visited (BLACK)

        # Run DFS from all unvisited nodes
        for node in self.nodes:
            if colors[node] == 0:
                dfs(node, [])

    def _compute_topological_order(self) -> None:
        """Compute a topological ordering of tasks using Kahn's algorithm."""
        # Create a copy of in-degrees
        in_degree = {name: node.in_degree for name, node in self.nodes.items()}

        # Find all nodes with no dependencies
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        self._topological_order = []

        while queue:
            # Get a task with no remaining dependencies
            current = queue.popleft()
            self._topological_order.append(current)

            # Remove this task from dependencies of others
            for dependent in self.nodes[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If we didn't process all nodes, there's a cycle (should be caught earlier)
        if len(self._topological_order) != len(self.nodes):
            raise CycleDetectedError(["<cycle detected but path not determined>"])

    def get_ready_tasks(self, completed_tasks: set[str] | None = None) -> list[str]:
        """Get tasks that are ready to execute (all dependencies satisfied)."""
        if not self._is_validated:
            self.validate()

        completed = completed_tasks or set()
        ready = []

        for name, node in self.nodes.items():
            if name not in completed and all(
                dep in completed for dep in node.dependencies
            ):
                ready.append(name)

        return ready

    def get_execution_levels(self) -> list[list[str]]:
        """Get tasks grouped by execution level (tasks in same level can run in parallel)."""
        if not self._is_validated:
            self.validate()

        levels = []
        completed: set[str] = set()

        while len(completed) < len(self.nodes):
            # Get all tasks that can run now
            ready = self.get_ready_tasks(completed)
            if not ready:
                # This shouldn't happen if graph is valid
                break

            levels.append(ready)
            completed.update(ready)

        return levels

    def get_critical_path(self) -> list[str]:
        """Find the critical path (longest dependency chain) in the graph."""
        if not self._is_validated:
            self.validate()

        # Use dynamic programming to find longest path
        longest_path_to = dict.fromkeys(self.nodes, 0)
        parent = dict.fromkeys(self.nodes)

        # Process in topological order
        for task in self._topological_order:
            for dependent in self.nodes[task].dependents:
                if longest_path_to[task] + 1 > longest_path_to[dependent]:
                    longest_path_to[dependent] = longest_path_to[task] + 1
                    parent[dependent] = task

        # Find the end of the longest path
        end_task = max(longest_path_to, key=lambda x: longest_path_to[x])

        # Reconstruct the path
        path = []
        current: str | None = end_task
        while current is not None:
            path.append(current)
            current = parent[current]

        return list(reversed(path))

    def visualize_ascii(self) -> str:
        """Generate a simple ASCII visualization of the graph."""
        if not self._is_validated:
            self.validate()

        lines = ["Task Dependency Graph:", "=" * 30]

        # Show tasks by level
        levels = self.get_execution_levels()
        for i, level in enumerate(levels):
            lines.append(f"\\nLevel {i} (can run in parallel):")
            for task in sorted(level):
                deps = sorted(self.nodes[task].dependencies)
                if deps:
                    lines.append(f"  {task} <- {', '.join(deps)}")
                else:
                    lines.append(f"  {task} (no dependencies)")

        # Show critical path
        critical_path = self.get_critical_path()
        if len(critical_path) > 1:
            lines.append(f"\\nCritical Path: {' -> '.join(critical_path)}")

        return "\\n".join(lines)
