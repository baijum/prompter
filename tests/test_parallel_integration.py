"""Integration tests for parallel task execution with complex dependency graphs."""

import time
from unittest.mock import MagicMock, patch

import anyio
import pytest

from prompter.cli.main import main
from prompter.config import PrompterConfig
from prompter.parallel_coordinator import ParallelTaskCoordinator
from prompter.runner import TaskResult, TaskRunner
from prompter.state import StateManager


@pytest.mark.slow
@pytest.mark.integration
class TestParallelIntegration:
    """Integration tests for parallel execution with real-world scenarios."""

    @pytest.fixture
    def complex_diamond_config(self, tmp_path):
        """Create a complex diamond dependency pattern configuration."""
        config_content = """
[settings]
max_parallel_tasks = 3
enable_parallel = true
check_interval = 0

# Layer 1: Entry point
[[tasks]]
name = "init"
prompt = "Initialize the project"
verify_command = "echo 'init done'"
depends_on = []

# Layer 2: Three parallel branches
[[tasks]]
name = "frontend_setup"
prompt = "Set up frontend"
verify_command = "echo 'frontend setup done'"
depends_on = ["init"]

[[tasks]]
name = "backend_setup"
prompt = "Set up backend"
verify_command = "echo 'backend setup done'"
depends_on = ["init"]

[[tasks]]
name = "database_setup"
prompt = "Set up database"
verify_command = "echo 'database setup done'"
depends_on = ["init"]

# Layer 3: Cross dependencies
[[tasks]]
name = "api_integration"
prompt = "Integrate API"
verify_command = "echo 'api integrated'"
depends_on = ["frontend_setup", "backend_setup"]

[[tasks]]
name = "data_migration"
prompt = "Migrate data"
verify_command = "echo 'data migrated'"
depends_on = ["backend_setup", "database_setup"]

# Layer 4: Convergence
[[tasks]]
name = "integration_tests"
prompt = "Run integration tests"
verify_command = "echo 'tests passed'"
depends_on = ["api_integration", "data_migration"]

# Layer 5: Final deployment
[[tasks]]
name = "deploy"
prompt = "Deploy to production"
verify_command = "echo 'deployed'"
depends_on = ["integration_tests"]
"""
        config_file = tmp_path / "diamond.toml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def wide_parallel_config(self, tmp_path):
        """Create a configuration with many parallel tasks."""
        config_content = """
[settings]
max_parallel_tasks = 5
enable_parallel = true

# 10 independent analysis tasks
[[tasks]]
name = "analyze_module_1"
prompt = "Analyze module 1"
verify_command = "echo 'module 1 analyzed'"
depends_on = []

[[tasks]]
name = "analyze_module_2"
prompt = "Analyze module 2"
verify_command = "echo 'module 2 analyzed'"
depends_on = []

[[tasks]]
name = "analyze_module_3"
prompt = "Analyze module 3"
verify_command = "echo 'module 3 analyzed'"
depends_on = []

[[tasks]]
name = "analyze_module_4"
prompt = "Analyze module 4"
verify_command = "echo 'module 4 analyzed'"
depends_on = []

[[tasks]]
name = "analyze_module_5"
prompt = "Analyze module 5"
verify_command = "echo 'module 5 analyzed'"
depends_on = []

# Aggregation task
[[tasks]]
name = "create_report"
prompt = "Create analysis report"
verify_command = "echo 'report created'"
depends_on = ["analyze_module_1", "analyze_module_2", "analyze_module_3", "analyze_module_4", "analyze_module_5"]
"""
        config_file = tmp_path / "wide.toml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def failure_recovery_config(self, tmp_path):
        """Create a configuration to test failure handling in parallel execution."""
        config_content = """
[settings]
max_parallel_tasks = 3
enable_parallel = true

# Two independent paths
[[tasks]]
name = "path_a_start"
prompt = "Start path A"
verify_command = "echo 'path A started'"
depends_on = []

[[tasks]]
name = "path_b_start"
prompt = "Start path B"
verify_command = "echo 'path B started'"
depends_on = []

# Path A continues (will fail)
[[tasks]]
name = "path_a_process"
prompt = "Process path A"
verify_command = "exit 1"  # This will fail
depends_on = ["path_a_start"]
on_failure = "stop"

# Path B continues successfully
[[tasks]]
name = "path_b_process"
prompt = "Process path B"
verify_command = "echo 'path B processed'"
depends_on = ["path_b_start"]

# Should only run if path B succeeds
[[tasks]]
name = "path_b_complete"
prompt = "Complete path B"
verify_command = "echo 'path B completed'"
depends_on = ["path_b_process"]
"""
        config_file = tmp_path / "failure.toml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def circular_dependency_config(self, tmp_path):
        """Create a configuration with circular dependencies (should fail validation)."""
        config_content = """
[settings]
enable_parallel = true

[[tasks]]
name = "task_a"
prompt = "Task A"
verify_command = "echo 'A'"
depends_on = ["task_c"]

[[tasks]]
name = "task_b"
prompt = "Task B"
verify_command = "echo 'B'"
depends_on = ["task_a"]

[[tasks]]
name = "task_c"
prompt = "Task C"
verify_command = "echo 'C'"
depends_on = ["task_b"]
"""
        config_file = tmp_path / "circular.toml"
        config_file.write_text(config_content)
        return config_file

    def test_complex_diamond_execution_order(self, complex_diamond_config, tmp_path):
        """Test that complex diamond dependencies execute in correct order."""
        import sys

        # Create command line args for main()
        test_args = [
            "prompter",
            str(complex_diamond_config),
            "--state-file",
            str(tmp_path / "state.json"),
        ]

        # Track execution order
        execution_order = []

        with patch("subprocess.run") as mock_run:
            # Mock successful execution
            mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

            # Patch the Claude SDK query to track execution
            async def mock_query(prompt, options):
                task_name = prompt.split()[0].lower()  # Extract task name from prompt
                execution_order.append(task_name)

                # Simulate task execution
                yield MagicMock(content=[MagicMock(text="Task completed")])

                # Return result message
                result = MagicMock()
                result.session_id = f"session_{task_name}"
                yield result

            with patch("prompter.runner.query", mock_query):
                with patch.object(sys, "argv", test_args):
                    # Run the tasks
                    result = main()
                    assert result == 0  # All tasks should succeed

        # Verify execution order respects dependencies
        # init must come first
        assert execution_order[0] == "initialize"

        # Layer 2 tasks must come after init
        layer2_starts = [i for i, task in enumerate(execution_order) if task == "set"]
        assert all(idx > 0 for idx in layer2_starts)

        # deploy must be last
        assert execution_order[-1] == "deploy"

    @pytest.mark.asyncio
    async def test_parallel_execution_performance(self, wide_parallel_config, tmp_path):
        """Test that parallel execution is faster than sequential."""
        state_file = tmp_path / "state.json"

        # Create config and state manager
        config = PrompterConfig(wide_parallel_config)
        state_manager = StateManager(state_file)

        # Mock runner that simulates work
        mock_runner = MagicMock(spec=TaskRunner)
        task_duration = 0.1  # Each task takes 0.1 seconds

        def mock_run_task(task, state_mgr):
            time.sleep(task_duration)  # Simulate work
            return TaskResult(
                task_name=task.name, success=True, output=f"{task.name} completed"
            )

        mock_runner.run_task.side_effect = mock_run_task

        # Run in parallel
        start_time = time.time()
        coordinator = ParallelTaskCoordinator(
            config=config,
            runner=mock_runner,
            state_manager=state_manager,
            dry_run=False,
        )

        results = await coordinator.execute_all()
        parallel_duration = time.time() - start_time

        # All tasks should complete
        assert len(results) == 6
        assert all(result.success for result in results.values())

        # Parallel execution should be significantly faster
        # 5 parallel tasks + 1 final task = ~2 * task_duration
        # Sequential would be 6 * task_duration
        expected_parallel = 2 * task_duration
        expected_sequential = 6 * task_duration

        # Allow some overhead
        assert parallel_duration < expected_sequential * 0.7
        assert parallel_duration < expected_parallel * 2

    def test_failure_handling_in_parallel(self, failure_recovery_config, tmp_path):
        """Test that failures in one path don't affect other parallel paths."""
        import sys

        state_file = tmp_path / "state.json"
        test_args = [
            "prompter",
            str(failure_recovery_config),
            "--state-file",
            str(state_file),
        ]

        # Track which tasks executed
        executed_tasks = []

        with patch("subprocess.run") as mock_run:

            def mock_subprocess(cmd, **kwargs):
                # Extract task name from verification
                if isinstance(cmd, str) and "exit 1" in cmd:
                    # This is the failing task
                    return MagicMock(returncode=1, stdout="", stderr="Failed")
                return MagicMock(returncode=0, stdout="Success", stderr="")

            mock_run.side_effect = mock_subprocess

            # Patch Claude SDK
            async def mock_query(prompt, options):
                task_name = " ".join(prompt.split()[:3])  # Extract task identifier
                executed_tasks.append(task_name)

                yield MagicMock(content=[MagicMock(text="Task completed")])

                result = MagicMock()
                result.session_id = f"session_{len(executed_tasks)}"
                yield result

            with patch("prompter.runner.query", mock_query):
                with patch.object(sys, "argv", test_args):
                    # Run the tasks
                    result = main()
                    assert result == 1  # Should fail due to path_a_process

        # Verify path B continued despite path A failure
        path_b_tasks = [task for task in executed_tasks if "path B" in task]
        assert len(path_b_tasks) >= 2  # path_b_process and path_b_complete should run

        # Load state and check task statuses
        state_manager = StateManager(state_file)
        assert state_manager.get_task_state("path_a_process").status == "failed"
        assert state_manager.get_task_state("path_b_complete").status == "completed"

    def test_circular_dependency_detection(self, circular_dependency_config):
        """Test that circular dependencies are detected during validation."""
        # This should fail during configuration validation
        config = PrompterConfig(circular_dependency_config)
        errors = config.validate()

        assert len(errors) > 0
        assert any("Circular dependency detected" in error for error in errors)

    @pytest.mark.asyncio
    async def test_state_persistence_across_parallel_runs(
        self, wide_parallel_config, tmp_path
    ):
        """Test that state is correctly persisted during parallel execution."""
        state_file = tmp_path / "state.json"

        # First run - execute first 3 tasks then simulate interruption
        config = PrompterConfig(wide_parallel_config)
        state_manager = StateManager(state_file)

        executed_count = 0

        # Mock runner that tracks executions
        mock_runner = MagicMock(spec=TaskRunner)

        def mock_run_task(task, state_mgr):
            nonlocal executed_count
            executed_count += 1

            # Simulate interruption after 3 tasks
            if executed_count > 3:
                msg = "Simulated interruption"
                raise KeyboardInterrupt(msg)

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

        # Run until interruption
        with pytest.raises(KeyboardInterrupt):
            await coordinator.execute_all()

        # Check that state was saved
        assert state_file.exists()

        # Load state and verify partial completion
        saved_state = StateManager(state_file)
        completed_tasks = saved_state.get_completed_tasks()
        assert len(completed_tasks) == 3

        # Second run - should continue from where it left off
        executed_count = 0
        remaining_tasks = []

        def mock_run_task_resume(task, state_mgr):
            remaining_tasks.append(task.name)
            return TaskResult(
                task_name=task.name, success=True, output=f"{task.name} completed"
            )

        mock_runner.run_task.side_effect = mock_run_task_resume

        # Create new coordinator with existing state
        coordinator2 = ParallelTaskCoordinator(
            config=config, runner=mock_runner, state_manager=saved_state, dry_run=False
        )

        results = await coordinator2.execute_all()

        # Should only execute remaining tasks
        assert len(remaining_tasks) == 3  # 2 analysis + 1 report
        assert all(task not in completed_tasks for task in remaining_tasks)

    @pytest.mark.asyncio
    async def test_max_parallel_tasks_limit(self, tmp_path):
        """Test that max_parallel_tasks limit is respected."""
        # Create config with many parallel tasks but low limit
        config_content = """
[settings]
max_parallel_tasks = 2
enable_parallel = true

[[tasks]]
name = "task1"
prompt = "Task 1"
verify_command = "echo '1'"
depends_on = []

[[tasks]]
name = "task2"
prompt = "Task 2"
verify_command = "echo '2'"
depends_on = []

[[tasks]]
name = "task3"
prompt = "Task 3"
verify_command = "echo '3'"
depends_on = []

[[tasks]]
name = "task4"
prompt = "Task 4"
verify_command = "echo '4'"
depends_on = []
"""
        config_file = tmp_path / "limit.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        state_manager = StateManager(tmp_path / "state.json")

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
                task_name=task.name, success=True, output=f"{task.name} completed"
            )

        mock_runner.run_task.side_effect = mock_run_task

        coordinator = ParallelTaskCoordinator(
            config=config,
            runner=mock_runner,
            state_manager=state_manager,
            dry_run=False,
        )

        await coordinator.execute_all()

        # Should never exceed the limit
        assert max_concurrent <= 2

    def test_mixed_sequential_and_parallel_workflow(self, tmp_path):
        """Test workflow that mixes sequential and parallel sections."""
        import sys

        config_content = """
[settings]
max_parallel_tasks = 3
enable_parallel = true

# Sequential section (on_success = stop/repeat)
[[tasks]]
name = "prepare"
prompt = "Prepare environment"
verify_command = "echo 'prepared'"
depends_on = []
on_success = "next"

[[tasks]]
name = "validate"
prompt = "Validate setup"
verify_command = "echo 'valid'"
depends_on = ["prepare"]
on_success = "next"

# Parallel section
[[tasks]]
name = "test_unit"
prompt = "Run unit tests"
verify_command = "echo 'unit tests passed'"
depends_on = ["validate"]

[[tasks]]
name = "test_integration"
prompt = "Run integration tests"
verify_command = "echo 'integration tests passed'"
depends_on = ["validate"]

[[tasks]]
name = "test_e2e"
prompt = "Run e2e tests"
verify_command = "echo 'e2e tests passed'"
depends_on = ["validate"]

# Sequential completion
[[tasks]]
name = "report"
prompt = "Generate test report"
verify_command = "echo 'report generated'"
depends_on = ["test_unit", "test_integration", "test_e2e"]
on_success = "stop"
"""
        config_file = tmp_path / "mixed.toml"
        config_file.write_text(config_content)

        test_args = [
            "prompter",
            str(config_file),
            "--state-file",
            str(tmp_path / "state.json"),
        ]

        execution_timeline = []

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

            async def mock_query(prompt, options):
                task_name = prompt.split()[0].lower()
                execution_timeline.append((task_name, time.time()))

                # Simulate varying task durations
                if "test" in task_name:
                    await anyio.sleep(0.1)  # Tests take longer

                yield MagicMock(content=[MagicMock(text="Completed")])

                result = MagicMock()
                result.session_id = f"session_{task_name}"
                yield result

            with patch("prompter.runner.query", mock_query):
                with patch.object(sys, "argv", test_args):
                    result = main()
                    assert result == 0

        # Verify execution pattern
        # First two should be sequential
        prepare_time = next(t for name, t in execution_timeline if name == "prepare")
        validate_time = next(t for name, t in execution_timeline if name == "validate")
        assert validate_time > prepare_time

        # Test tasks should start roughly at the same time
        test_times = [
            (name, t)
            for name, t in execution_timeline
            if "test" in name and name != "generate"
        ]
        assert len(test_times) == 3

        # All test tasks should start within a small window
        test_start_times = [t for _, t in test_times]
        assert max(test_start_times) - min(test_start_times) < 0.5

        # Report should be last
        report_time = next(t for name, t in execution_timeline if name == "generate")
        assert report_time > max(test_start_times)
