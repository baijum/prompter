"""Tests for parallel task execution functionality."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from prompter.config import PrompterConfig
from prompter.parallel_coordinator import ParallelTaskCoordinator
from prompter.runner import TaskResult, TaskRunner
from prompter.state import StateManager
from prompter.task_graph import CycleDetectedError, TaskGraph

from .test_helpers import create_task_config


class TestTaskGraph:
    """Test the TaskGraph class functionality."""

    def test_simple_graph_creation(self):
        """Test creating a simple task graph."""
        graph = TaskGraph()

        task1 = create_task_config(name="task1")
        task2 = create_task_config(name="task2")
        task3 = create_task_config(name="task3")

        graph.add_task("task1", task1, [])
        graph.add_task("task2", task2, ["task1"])
        graph.add_task("task3", task3, ["task1", "task2"])

        graph.validate()

        # Check topological order
        assert graph._topological_order == ["task1", "task2", "task3"]

        # Check ready tasks
        assert graph.get_ready_tasks(set()) == ["task1"]
        assert graph.get_ready_tasks({"task1"}) == ["task2"]
        assert graph.get_ready_tasks({"task1", "task2"}) == ["task3"]

    def test_parallel_execution_levels(self):
        """Test identifying tasks that can run in parallel."""
        graph = TaskGraph()

        # Create diamond pattern:
        #    A
        #   / \\
        #  B   C
        #   \\ /
        #    D
        graph.add_task("A", create_task_config(name="A"), [])
        graph.add_task("B", create_task_config(name="B"), ["A"])
        graph.add_task("C", create_task_config(name="C"), ["A"])
        graph.add_task("D", create_task_config(name="D"), ["B", "C"])

        graph.validate()

        levels = graph.get_execution_levels()
        assert len(levels) == 3
        assert levels[0] == ["A"]
        assert set(levels[1]) == {"B", "C"}  # B and C can run in parallel
        assert levels[2] == ["D"]

    def test_cycle_detection(self):
        """Test that cycles are properly detected."""
        graph = TaskGraph()

        # Create a cycle: A -> B -> C -> A
        graph.add_task("A", create_task_config(name="A"), ["C"])
        graph.add_task("B", create_task_config(name="B"), ["A"])
        graph.add_task("C", create_task_config(name="C"), ["B"])

        with pytest.raises(CycleDetectedError) as exc_info:
            graph.validate()

        assert "Cycle detected" in str(exc_info.value)
        assert "A" in str(exc_info.value)
        assert "B" in str(exc_info.value)
        assert "C" in str(exc_info.value)

    def test_missing_dependency_detection(self):
        """Test that missing dependencies are detected."""
        graph = TaskGraph()

        graph.add_task("A", create_task_config(name="A"), ["NonExistent"])

        with pytest.raises(ValueError) as exc_info:
            graph.validate()

        assert "depends on undefined task 'NonExistent'" in str(exc_info.value)

    def test_critical_path(self):
        """Test finding the critical path through the graph."""
        graph = TaskGraph()

        # Create graph with multiple paths
        graph.add_task("Start", create_task_config(name="Start"), [])
        graph.add_task("A1", create_task_config(name="A1"), ["Start"])
        graph.add_task("A2", create_task_config(name="A2"), ["A1"])
        graph.add_task("B1", create_task_config(name="B1"), ["Start"])
        graph.add_task("End", create_task_config(name="End"), ["A2", "B1"])

        graph.validate()

        critical_path = graph.get_critical_path()
        # The longer path Start -> A1 -> A2 -> End should be the critical path
        assert critical_path == ["Start", "A1", "A2", "End"]


class TestParallelCoordinator:
    """Test the ParallelTaskCoordinator class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
max_parallel_tasks = 3
enable_parallel = true

[[tasks]]
name = "task1"
prompt = "Do task 1"
verify_command = "echo 'task1 done'"
depends_on = []

[[tasks]]
name = "task2"
prompt = "Do task 2"
verify_command = "echo 'task2 done'"
depends_on = ["task1"]

[[tasks]]
name = "task3"
prompt = "Do task 3"
verify_command = "echo 'task3 done'"
depends_on = ["task1"]

[[tasks]]
name = "task4"
prompt = "Do task 4"
verify_command = "echo 'task4 done'"
depends_on = ["task2", "task3"]
""")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary state file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_execution_respects_dependencies(
        self, temp_config_file, temp_state_file
    ):
        """Test that parallel execution respects task dependencies."""
        config = PrompterConfig(temp_config_file)
        state_manager = StateManager(temp_state_file)

        # Track execution order
        execution_order = []

        # Mock runner that tracks execution
        mock_runner = MagicMock(spec=TaskRunner)

        def mock_run_task(task, state_mgr):
            execution_order.append(task.name)
            # Simulate some work
            time.sleep(0.1)
            return TaskResult(
                task_name=task.name, success=True, output=f"{task.name} completed"
            )

        mock_runner.run_task.side_effect = mock_run_task

        # Create coordinator and execute
        coordinator = ParallelTaskCoordinator(
            config=config,
            runner=mock_runner,
            state_manager=state_manager,
            dry_run=False,
        )

        results = await coordinator.execute_all()

        # Verify all tasks completed
        assert len(results) == 4
        assert all(result.success for result in results.values())

        # Verify dependencies were respected
        # task1 must complete before task2 and task3
        task1_idx = execution_order.index("task1")
        task2_idx = execution_order.index("task2")
        task3_idx = execution_order.index("task3")
        task4_idx = execution_order.index("task4")

        assert task1_idx < task2_idx
        assert task1_idx < task3_idx
        assert task2_idx < task4_idx
        assert task3_idx < task4_idx

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_execution_with_failures(
        self, temp_config_file, temp_state_file
    ):
        """Test parallel execution handles task failures correctly."""
        config = PrompterConfig(temp_config_file)
        state_manager = StateManager(temp_state_file)

        # Mock runner that fails task2
        mock_runner = MagicMock(spec=TaskRunner)

        def mock_run_task(task, state_mgr):
            if task.name == "task2":
                return TaskResult(
                    task_name=task.name, success=False, error="Task 2 failed"
                )
            return TaskResult(
                task_name=task.name, success=True, output=f"{task.name} completed"
            )

        mock_runner.run_task.side_effect = mock_run_task

        coordinator = ParallelTaskCoordinator(
            config=config,
            runner=mock_runner,
            state_manager=state_manager,
            dry_run=False,
        )

        results = await coordinator.execute_all()

        # task1 and task3 should succeed
        assert results["task1"].success
        assert results["task3"].success

        # task2 should fail
        assert not results["task2"].success
        assert "Task 2 failed" in results["task2"].error

        # task4 should still run even though task2 failed
        # (depends on the specific failure handling strategy)
        assert "task4" in results

    def test_resource_pool_constraints(self):
        """Test that resource pool enforces parallel task limits."""
        from prompter.parallel_coordinator import ResourcePool

        pool = ResourcePool(max_parallel_tasks=2)

        task1 = create_task_config(name="task1")
        task2 = create_task_config(name="task2")
        task3 = create_task_config(name="task3")

        # Can schedule first two tasks
        assert pool.can_schedule(task1)
        pool.allocate(task1)

        assert pool.can_schedule(task2)
        pool.allocate(task2)

        # Cannot schedule third task (limit reached)
        assert not pool.can_schedule(task3)

        # Release one task
        pool.release(task1, success=True)

        # Now can schedule task3
        assert pool.can_schedule(task3)

    def test_exclusive_task_handling(self):
        """Test that exclusive tasks run alone."""
        from prompter.parallel_coordinator import ResourcePool

        pool = ResourcePool(max_parallel_tasks=3)

        normal_task = create_task_config(name="normal")
        exclusive_task = create_task_config(name="exclusive", exclusive=True)

        # Can schedule normal task
        assert pool.can_schedule(normal_task)
        pool.allocate(normal_task)

        # Cannot schedule exclusive task while other task is running
        assert not pool.can_schedule(exclusive_task)

        # Release normal task
        pool.release(normal_task, success=True)

        # Now can schedule exclusive task
        assert pool.can_schedule(exclusive_task)
        pool.allocate(exclusive_task)

        # Cannot schedule normal task while exclusive is running
        assert not pool.can_schedule(normal_task)
