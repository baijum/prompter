"""Simplified integration tests for parallel execution."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from prompter.config import PrompterConfig
from prompter.parallel_coordinator import ParallelTaskCoordinator
from prompter.runner import TaskResult, TaskRunner
from prompter.state import StateManager


@pytest.mark.integration
class TestParallelExecutionIntegration:
    """Integration tests focusing on parallel execution mechanics."""

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary state file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    def test_dependency_validation_catches_cycles(self):
        """Test that circular dependencies are caught during validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
enable_parallel = true

[[tasks]]
name = "a"
prompt = "Task A"
verify_command = "echo a"
depends_on = ["c"]

[[tasks]]
name = "b"
prompt = "Task B"
verify_command = "echo b"
depends_on = ["a"]

[[tasks]]
name = "c"
prompt = "Task C"
verify_command = "echo c"
depends_on = ["b"]
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            errors = config.validate()

            # Should have validation errors
            assert len(errors) > 0
            assert any("Circular dependency detected" in error for error in errors)
        finally:
            config_file.unlink()

    def test_missing_dependency_validation(self):
        """Test that missing dependencies are caught."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
enable_parallel = true

[[tasks]]
name = "task1"
prompt = "Task 1"
verify_command = "echo 1"
depends_on = ["nonexistent"]
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            errors = config.validate()

            assert len(errors) > 0
            assert any("unknown task 'nonexistent'" in error for error in errors)
        finally:
            config_file.unlink()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_simple_parallel_execution(self, temp_state_file):
        """Test basic parallel execution with independent tasks."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
max_parallel_tasks = 2
enable_parallel = true

[[tasks]]
name = "task1"
prompt = "Do task 1"
verify_command = "echo 1"
depends_on = []

[[tasks]]
name = "task2"
prompt = "Do task 2"
verify_command = "echo 2"
depends_on = []
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            state_manager = StateManager(temp_state_file)

            # Mock runner
            mock_runner = MagicMock(spec=TaskRunner)
            execution_order = []

            def mock_run_task(task, state_mgr):
                execution_order.append(task.name)
                return TaskResult(
                    task_name=task.name, success=True, output=f"{task.name} done"
                )

            mock_runner.run_task.side_effect = mock_run_task

            # Execute
            coordinator = ParallelTaskCoordinator(
                config=config,
                runner=mock_runner,
                state_manager=state_manager,
                dry_run=False,
            )

            results = await coordinator.execute_all()

            # Both tasks should complete
            assert len(results) == 2
            assert all(result.success for result in results.values())
            assert set(execution_order) == {"task1", "task2"}
        finally:
            config_file.unlink()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_dependency_ordering(self, temp_state_file):
        """Test that dependencies are respected in execution order."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
enable_parallel = true

[[tasks]]
name = "first"
prompt = "First task"
verify_command = "echo first"
depends_on = []

[[tasks]]
name = "second"
prompt = "Second task"
verify_command = "echo second"
depends_on = ["first"]

[[tasks]]
name = "third"
prompt = "Third task"
verify_command = "echo third"
depends_on = ["second"]
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            state_manager = StateManager(temp_state_file)

            # Mock runner that tracks order
            mock_runner = MagicMock(spec=TaskRunner)
            execution_order = []

            def mock_run_task(task, state_mgr):
                execution_order.append(task.name)
                time.sleep(0.01)  # Small delay to ensure ordering
                return TaskResult(
                    task_name=task.name, success=True, output=f"{task.name} done"
                )

            mock_runner.run_task.side_effect = mock_run_task

            # Execute
            coordinator = ParallelTaskCoordinator(
                config=config,
                runner=mock_runner,
                state_manager=state_manager,
                dry_run=False,
            )

            results = await coordinator.execute_all()

            # Check order
            assert execution_order == ["first", "second", "third"]
            assert len(results) == 3
            assert all(result.success for result in results.values())
        finally:
            config_file.unlink()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_failure_stops_dependents(self, temp_state_file):
        """Test that task failure prevents dependents from running."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
enable_parallel = true

[[tasks]]
name = "will_fail"
prompt = "This will fail"
verify_command = "exit 1"
depends_on = []

[[tasks]]
name = "depends_on_failure"
prompt = "This depends on failure"
verify_command = "echo ok"
depends_on = ["will_fail"]
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            state_manager = StateManager(temp_state_file)

            # Mock runner
            mock_runner = MagicMock(spec=TaskRunner)
            executed_tasks = []

            def mock_run_task(task, state_mgr):
                executed_tasks.append(task.name)

                if task.name == "will_fail":
                    return TaskResult(
                        task_name=task.name, success=False, error="Task failed"
                    )

                return TaskResult(
                    task_name=task.name, success=True, output=f"{task.name} done"
                )

            mock_runner.run_task.side_effect = mock_run_task

            # Execute
            coordinator = ParallelTaskCoordinator(
                config=config,
                runner=mock_runner,
                state_manager=state_manager,
                dry_run=False,
            )

            results = await coordinator.execute_all()

            # Only the first task should have executed
            assert executed_tasks == ["will_fail"]
            assert not results["will_fail"].success

            # The dependent task should not be in results
            # (It never ran because its dependency failed)
            assert len(results) == 1
        finally:
            config_file.unlink()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_parallel_limit_respected(self, temp_state_file):
        """Test that max_parallel_tasks limit is enforced."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
max_parallel_tasks = 2
enable_parallel = true

[[tasks]]
name = "task1"
prompt = "Task 1"
verify_command = "echo 1"
depends_on = []

[[tasks]]
name = "task2"
prompt = "Task 2"
verify_command = "echo 2"
depends_on = []

[[tasks]]
name = "task3"
prompt = "Task 3"
verify_command = "echo 3"
depends_on = []

[[tasks]]
name = "task4"
prompt = "Task 4"
verify_command = "echo 4"
depends_on = []
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            state_manager = StateManager(temp_state_file)

            # Track concurrent executions
            max_concurrent = 0
            current_concurrent = 0

            mock_runner = MagicMock(spec=TaskRunner)

            def mock_run_task(task, state_mgr):
                nonlocal max_concurrent, current_concurrent

                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

                # Simulate work
                time.sleep(0.05)

                current_concurrent -= 1

                return TaskResult(
                    task_name=task.name, success=True, output=f"{task.name} done"
                )

            mock_runner.run_task.side_effect = mock_run_task

            # Execute
            coordinator = ParallelTaskCoordinator(
                config=config,
                runner=mock_runner,
                state_manager=state_manager,
                dry_run=False,
            )

            results = await coordinator.execute_all()

            # All tasks should complete
            assert len(results) == 4
            assert all(result.success for result in results.values())

            # Should never exceed limit
            assert max_concurrent <= 2
        finally:
            config_file.unlink()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_diamond_dependency_pattern(self, temp_state_file):
        """Test diamond dependency pattern execution."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[settings]
enable_parallel = true

[[tasks]]
name = "start"
prompt = "Start"
verify_command = "echo start"
depends_on = []

[[tasks]]
name = "left"
prompt = "Left branch"
verify_command = "echo left"
depends_on = ["start"]

[[tasks]]
name = "right"
prompt = "Right branch"
verify_command = "echo right"
depends_on = ["start"]

[[tasks]]
name = "end"
prompt = "End"
verify_command = "echo end"
depends_on = ["left", "right"]
""")
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            state_manager = StateManager(temp_state_file)

            # Track execution
            execution_times = {}

            mock_runner = MagicMock(spec=TaskRunner)

            def mock_run_task(task, state_mgr):
                execution_times[task.name] = time.time()
                time.sleep(0.01)  # Small delay

                return TaskResult(
                    task_name=task.name, success=True, output=f"{task.name} done"
                )

            mock_runner.run_task.side_effect = mock_run_task

            # Execute
            coordinator = ParallelTaskCoordinator(
                config=config,
                runner=mock_runner,
                state_manager=state_manager,
                dry_run=False,
            )

            results = await coordinator.execute_all()

            # All should complete
            assert len(results) == 4
            assert all(result.success for result in results.values())

            # Verify ordering
            assert execution_times["start"] < execution_times["left"]
            assert execution_times["start"] < execution_times["right"]
            assert execution_times["left"] < execution_times["end"]
            assert execution_times["right"] < execution_times["end"]

            # Left and right should run in parallel (close start times)
            assert abs(execution_times["left"] - execution_times["right"]) < 0.1
        finally:
            config_file.unlink()
