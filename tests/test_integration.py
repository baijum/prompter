"""Integration tests for the prompter tool."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from prompter.cli import main
from prompter.config import PrompterConfig
from prompter.runner import TaskRunner
from prompter.state import StateManager


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def complete_config_file(self, temp_dir):
        """Create a complete configuration file for testing."""
        config_content = """[settings]
check_interval = 0
max_retries = 2
claude_command = "echo"

[[tasks]]
name = "simple_task"
prompt = "This is a test prompt"
verify_command = "echo 'verification'"
verify_success_code = 0
on_success = "next"
on_failure = "retry"
max_attempts = 2

[[tasks]]
name = "second_task"
prompt = "Second test prompt"
verify_command = "echo 'second verification'"
verify_success_code = 0
on_success = "stop"
on_failure = "stop"
max_attempts = 1
"""
        config_file = temp_dir / "complete_config.toml"
        config_file.write_text(config_content)
        return config_file

    def test_config_to_runner_integration(self, complete_config_file, temp_dir):
        """Test integration from config loading to task execution."""
        # Load configuration
        config = PrompterConfig(complete_config_file)
        assert len(config.tasks) == 2
        assert config.validate() == []

        # Create state manager
        state_file = temp_dir / "integration_state.json"
        state_manager = StateManager(state_file)

        # Create runner in dry run mode
        runner = TaskRunner(config, dry_run=True)

        # Execute first task
        task = config.tasks[0]
        result = runner.run_task(task)

        # Update state
        state_manager.update_task_state(result)

        # Verify results
        assert result.success is True
        assert result.task_name == "simple_task"

        # Verify state was updated
        task_state = state_manager.get_task_state("simple_task")
        assert task_state.status == "completed"

        # Verify state file was created
        assert state_file.exists()

    @patch("prompter.runner.query")
    @patch("subprocess.run")
    def test_runner_with_real_commands(
        self, mock_subprocess, mock_query, complete_config_file, temp_dir
    ):
        """Test runner with mocked subprocess calls."""
        # Setup successful command responses
        success_result = Mock()
        success_result.returncode = 0
        success_result.stdout = "Command executed successfully"
        success_result.stderr = ""

        mock_subprocess.return_value = success_result

        # Mock SDK query success response
        def query_side_effect(*args, **kwargs):
            mock_message = Mock()
            mock_content = Mock()
            mock_content.text = "Task completed"
            mock_message.content = [mock_content]

            async def mock_async_gen():
                yield mock_message

            return mock_async_gen()

        mock_query.side_effect = query_side_effect

        # Load config and create runner
        config = PrompterConfig(complete_config_file)
        runner = TaskRunner(config)

        # Execute all tasks
        results = runner.run_all_tasks()

        assert len(results) == 2
        assert all(result.success for result in results)

        # Verify subprocess was called for verification commands
        assert mock_subprocess.call_count == 2  # 2 tasks × 1 verification command each

    def test_state_persistence_across_sessions(self, complete_config_file, temp_dir):
        """Test that state persists across different sessions."""
        state_file = temp_dir / "persistent_state.json"

        # First session - create and update some state
        session1_manager = StateManager(state_file)
        session1_manager.mark_task_running("simple_task")

        # Verify state file was created
        assert state_file.exists()

        # Second session - load existing state
        session2_manager = StateManager(state_file)

        # Verify state was loaded
        task_state = session2_manager.get_task_state("simple_task")
        assert task_state.status == "running"

    @patch("prompter.runner.query")
    @patch("subprocess.run")
    def test_full_workflow_with_failure_and_retry(
        self, mock_subprocess, mock_query, temp_dir
    ):
        """Test complete workflow with task failure and retry."""
        # Create config with retry logic
        config_content = """[settings]
check_interval = 0

[[tasks]]
name = "retry_task"
prompt = "Task that fails first"
verify_command = "test_command"
on_failure = "retry"
max_attempts = 3
"""
        config_file = temp_dir / "retry_config.toml"
        config_file.write_text(config_content)

        # Mock SDK query success response
        def query_side_effect(*args, **kwargs):
            mock_message = Mock()
            mock_content = Mock()
            mock_content.text = "Task completed"
            mock_message.content = [mock_content]

            async def mock_async_gen():
                yield mock_message

            return mock_async_gen()

        mock_query.side_effect = query_side_effect

        # Setup mock responses - fail twice, then succeed
        verify_failure = Mock()
        verify_failure.returncode = 1
        verify_failure.stdout = "Verification failed"
        verify_failure.stderr = "Error"

        verify_success = Mock()
        verify_success.returncode = 0
        verify_success.stdout = "Verification succeeded"
        verify_success.stderr = ""

        # Sequence: verify fail, verify fail, verify success
        mock_subprocess.side_effect = [
            verify_failure,  # Attempt 1
            verify_failure,  # Attempt 2
            verify_success,  # Attempt 3
        ]

        # Execute workflow
        config = PrompterConfig(config_file)
        state_manager = StateManager(temp_dir / "retry_state.json")
        runner = TaskRunner(config)

        task = config.tasks[0]
        state_manager.mark_task_running(task.name)

        result = runner.run_task(task)
        state_manager.update_task_state(result)

        # Verify final result
        assert result.success is True
        assert result.attempts == 3

        # Verify state
        final_state = state_manager.get_task_state("retry_task")
        assert final_state.status == "completed"

    def test_cli_integration_with_real_config(self, complete_config_file, temp_dir):
        """Test CLI integration with configuration file."""
        import sys
        from unittest.mock import patch

        state_file = temp_dir / "cli_state.json"

        # Patch subprocess to avoid actual command execution
        with patch("subprocess.run") as mock_subprocess:
            success_result = Mock()
            success_result.returncode = 0
            success_result.stdout = "Success"
            success_result.stderr = ""
            mock_subprocess.return_value = success_result

            # Patch sys.argv and run CLI
            test_args = [
                "prompter",
                str(complete_config_file),
                "--state-file",
                str(state_file),
                "--dry-run",
            ]

            with patch.object(sys, "argv", test_args):
                exit_code = main()

        assert exit_code == 0
        # State file should not be created in dry run mode
        # (depending on implementation details)

    @patch("prompter.runner.query")
    @patch("subprocess.run")
    def test_task_failure_stops_execution(self, mock_subprocess, mock_query, temp_dir):
        """Test that task failure stops execution when configured."""
        config_content = """[settings]
check_interval = 0

[[tasks]]
name = "failing_task"
prompt = "This will fail"
verify_command = "failing_command"
on_failure = "stop"
max_attempts = 1

[[tasks]]
name = "should_not_run"
prompt = "This should not execute"
verify_command = "echo success"
"""
        config_file = temp_dir / "stop_on_fail.toml"
        config_file.write_text(config_content)

        # Mock SDK query success response
        def query_side_effect(*args, **kwargs):
            mock_message = Mock()
            mock_content = Mock()
            mock_content.text = "Task completed"
            mock_message.content = [mock_content]

            async def mock_async_gen():
                yield mock_message

            return mock_async_gen()

        mock_query.side_effect = query_side_effect

        # Mock failure
        verify_failure = Mock()
        verify_failure.returncode = 1
        verify_failure.stdout = "Failed"
        verify_failure.stderr = "Error"

        mock_subprocess.return_value = verify_failure

        # Execute
        config = PrompterConfig(config_file)
        runner = TaskRunner(config)
        results = runner.run_all_tasks()

        # Should only have one result (first task)
        assert len(results) == 1
        assert not results[0].success
        assert results[0].task_name == "failing_task"

    def test_config_validation_integration(self, temp_dir):
        """Test configuration validation in full workflow."""
        # Create invalid config
        invalid_config = """[settings]
check_interval = 3600

[[tasks]]
name = ""
# Missing required fields
"""
        config_file = temp_dir / "invalid.toml"
        config_file.write_text(invalid_config)

        # Test that validation catches errors
        config = PrompterConfig(config_file)
        errors = config.validate()

        assert len(errors) > 0
        assert any("name is required" in error for error in errors)
        assert any("prompt is required" in error for error in errors)

    def test_state_summary_integration(self, temp_dir):
        """Test state summary with multiple task states."""
        state_file = temp_dir / "summary_test.json"
        state_manager = StateManager(state_file)

        # Simulate various task results
        from prompter.runner import TaskResult

        # Completed task
        completed_result = TaskResult("completed_task", success=True, attempts=1)
        state_manager.update_task_state(completed_result)

        # Failed task
        failed_result = TaskResult(
            "failed_task", success=False, error="Failed", attempts=3
        )
        state_manager.update_task_state(failed_result)

        # Running task
        state_manager.mark_task_running("running_task")

        # Get summary
        summary = state_manager.get_summary()

        assert summary["total_tasks"] == 3
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["running"] == 1
        assert summary["pending"] == 0
        assert summary["total_results"] == 2

    def test_working_directory_integration(self, temp_dir):
        """Test integration with custom working directory."""
        work_dir = temp_dir / "workdir"
        work_dir.mkdir()

        config_content = f"""[settings]
working_directory = "{work_dir}"

[[tasks]]
name = "workdir_task"
prompt = "Test in working directory"
verify_command = "pwd"
"""
        config_file = temp_dir / "workdir_config.toml"
        config_file.write_text(config_content)

        # Load config and verify working directory
        config = PrompterConfig(config_file)
        assert config.working_directory == str(work_dir)

        # Create runner and verify directory is set
        runner = TaskRunner(config)
        assert runner.current_directory == work_dir

    def test_timeout_integration(self, complete_config_file, temp_dir):
        """Test timeout functionality integration."""
        from unittest.mock import patch

        config = PrompterConfig(complete_config_file)

        # Add timeout to first task
        config.tasks[0].timeout = 1
        # Set on_failure to stop so we get the verification output in the result
        config.tasks[0].on_failure = "stop"

        runner = TaskRunner(config)

        # Mock the query function to succeed
        with patch("prompter.runner.query") as mock_query:
            mock_message = Mock()
            mock_content = Mock()
            mock_content.text = "Task completed"
            mock_message.content = [mock_content]

            async def mock_async_gen():
                yield mock_message

            mock_query.return_value = mock_async_gen()

            # Mock subprocess to raise timeout
            with patch(
                "subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1)
            ):
                result = runner.run_task(config.tasks[0])

        assert not result.success
        # The timeout message appears in verification_output when on_failure="stop"
        assert "timed out" in result.verification_output
