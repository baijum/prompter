"""Tests for the task runner module."""

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from prompter.config import PrompterConfig, TaskConfig
from prompter.runner import TaskResult, TaskRunner


class TestTaskResult:
    """Tests for TaskResult class."""

    def test_task_result_creation(self):
        """Test TaskResult creation with all parameters."""
        result = TaskResult(
            task_name="test_task",
            success=True,
            output="Task completed",
            error="",
            verification_output="All tests passed",
            attempts=2,
        )

        assert result.task_name == "test_task"
        assert result.success is True
        assert result.output == "Task completed"
        assert result.error == ""
        assert result.verification_output == "All tests passed"
        assert result.attempts == 2
        assert result.timestamp > 0

    def test_task_result_with_defaults(self):
        """Test TaskResult creation with default parameters."""
        result = TaskResult("test_task", False)

        assert result.task_name == "test_task"
        assert result.success is False
        assert result.output == ""
        assert result.error == ""
        assert result.verification_output == ""
        assert result.attempts == 1


class TestTaskRunner:
    """Tests for TaskRunner class."""

    class MockAsyncIterator:
        """A mock async iterator that properly handles async iteration."""

        def __init__(self, items):
            self.items = items
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=PrompterConfig)
        config.check_interval = 0  # No delay for tests
        config.working_directory = None
        return config

    @pytest.fixture
    def sample_task(self):
        """Create a sample task configuration."""
        return TaskConfig(
            {
                "name": "test_task",
                "prompt": "Fix all warnings",
                "verify_command": "make",
                "verify_success_code": 0,
                "on_success": "next",
                "on_failure": "retry",
                "max_attempts": 3,
            }
        )

    def test_runner_initialization(self, mock_config):
        """Test TaskRunner initialization."""
        runner = TaskRunner(mock_config)

        assert runner.config == mock_config
        assert runner.dry_run is False
        assert runner.current_directory == Path.cwd()

    def test_runner_initialization_with_working_directory(self, mock_config, temp_dir):
        """Test TaskRunner initialization with working directory."""
        mock_config.working_directory = str(temp_dir)
        runner = TaskRunner(mock_config)

        assert runner.current_directory == temp_dir

    def test_runner_dry_run(self, mock_config, sample_task):
        """Test task execution in dry run mode."""
        runner = TaskRunner(mock_config, dry_run=True)

        result = runner.run_task(sample_task)

        assert result.success is True
        assert "[DRY RUN]" in result.output
        assert "[DRY RUN]" in result.verification_output
        assert result.task_name == "test_task"

    @patch("prompter.runner.query")
    @patch("prompter.runner.subprocess.run")
    def test_successful_task_execution(
        self, mock_subprocess, mock_query, mock_config, sample_task
    ):
        """Test successful task execution."""
        # Create mock message with text content
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = "Task completed successfully"
        mock_message.content = [mock_content]

        # Make query return an async generator
        mock_query.return_value = self.MockAsyncIterator([mock_message])

        # Mock verification command success
        verify_result = Mock()
        verify_result.returncode = 0
        verify_result.stdout = "Build successful"
        verify_result.stderr = ""

        mock_subprocess.return_value = verify_result

        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)

        assert result.success is True
        assert result.task_name == "test_task"
        assert result.attempts == 1
        assert "Task completed successfully" in result.output

    @patch("prompter.runner.query")
    def test_claude_sdk_failure(self, mock_query, mock_config, sample_task):
        """Test task execution when Claude SDK fails."""

        # Mock SDK query empty response
        mock_query.return_value = self.MockAsyncIterator([])

        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)

        assert result.success is False
        assert result.attempts == sample_task.max_attempts
        assert "empty response" in result.error

    @patch("prompter.runner.query")
    @patch("prompter.runner.subprocess.run")
    def test_verification_failure_with_retry(
        self, mock_subprocess, mock_query, mock_config, sample_task
    ):
        """Test task execution when verification fails but should retry."""

        # Mock SDK query success response
        def query_side_effect(*args, **kwargs):
            mock_message = Mock()
            mock_content = Mock()
            mock_content.text = "Task completed"
            mock_message.content = [mock_content]

            return self.MockAsyncIterator([mock_message])

        mock_query.side_effect = query_side_effect

        # Mock verification command failure
        verify_result = Mock()
        verify_result.returncode = 1
        verify_result.stdout = "Build failed"
        verify_result.stderr = "Error in build"

        mock_subprocess.return_value = verify_result  # Always fail verification

        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)

        assert result.success is False
        assert result.attempts == sample_task.max_attempts
        assert "Task failed after" in result.error

    @patch("prompter.runner.query")
    @patch("prompter.runner.subprocess.run")
    def test_verification_failure_with_stop(
        self, mock_subprocess, mock_query, mock_config
    ):
        """Test task execution when verification fails and should stop."""
        task = TaskConfig(
            {
                "name": "stop_task",
                "prompt": "Do something",
                "verify_command": "make",
                "on_failure": "stop",
                "max_attempts": 3,
            }
        )

        # Mock SDK query success response
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = "Task completed"
        mock_message.content = [mock_content]

        mock_query.return_value = self.MockAsyncIterator([mock_message])

        # Mock verification command failure
        verify_result = Mock()
        verify_result.returncode = 1
        verify_result.stdout = "Build failed"
        verify_result.stderr = "Error"

        mock_subprocess.return_value = verify_result

        runner = TaskRunner(mock_config)
        result = runner.run_task(task)  # Use the correct task variable

        assert result.success is False
        assert result.attempts == 1  # Should stop after first failure

    @patch("prompter.runner.query")
    def test_sdk_timeout_legacy(self, mock_query, mock_config):
        """Test task execution with timeout (legacy TimeoutError)."""
        task = TaskConfig(
            {
                "name": "timeout_task",
                "prompt": "Long running task",
                "verify_command": "make",
                "timeout": 1,
                "max_attempts": 1,
            }
        )

        # Mock SDK query timeout
        mock_query.side_effect = TimeoutError("Task timed out")

        runner = TaskRunner(mock_config)
        result = runner.run_task(task)

        assert result.success is False
        assert "timed out" in result.error

    @patch("prompter.runner.query")
    def test_sdk_error(self, mock_query, mock_config, sample_task):
        """Test task execution when SDK raises an error."""
        # Mock SDK query error
        mock_query.side_effect = Exception("SDK error")

        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)

        assert result.success is False
        assert "Error executing Claude SDK task" in result.error

    @patch("prompter.runner.query")
    @patch("prompter.runner.subprocess.run")
    def test_verification_timeout(self, mock_subprocess, mock_query, mock_config):
        """Test verification command timeout."""
        # Create a task that stops on failure to avoid retries
        task = TaskConfig(
            {
                "name": "test_task",
                "prompt": "Fix all warnings",
                "verify_command": "make",
                "verify_success_code": 0,
                "on_success": "next",
                "on_failure": "stop",  # Stop on failure to avoid retries
                "max_attempts": 3,
            }
        )

        # Mock SDK query success response
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = "Task completed"
        mock_message.content = [mock_content]

        mock_query.return_value = self.MockAsyncIterator([mock_message])

        # Mock verification timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("make", 300)

        runner = TaskRunner(mock_config)
        result = runner.run_task(task)

        assert result.success is False
        # Check that timeout is mentioned in verification output
        assert "timed out" in result.verification_output.lower()

    @patch("prompter.runner.query")
    @patch("prompter.runner.subprocess.run")
    def test_task_with_custom_success_code(
        self, mock_subprocess, mock_query, mock_config
    ):
        """Test task with custom verification success code."""
        task = TaskConfig(
            {
                "name": "custom_success_task",
                "prompt": "Custom task",
                "verify_command": "custom_command",
                "verify_success_code": 2,  # Custom success code
                "max_attempts": 1,
            }
        )

        # Mock SDK query success response
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = "Task completed"
        mock_message.content = [mock_content]

        mock_query.return_value = self.MockAsyncIterator([mock_message])

        # Mock verification with custom success code
        verify_result = Mock()
        verify_result.returncode = 2  # Matches custom success code
        verify_result.stdout = "Custom success"
        verify_result.stderr = ""

        mock_subprocess.return_value = verify_result

        runner = TaskRunner(mock_config)
        result = runner.run_task(task)

        assert result.success is True

    @patch("prompter.runner.query")
    @patch("prompter.runner.asyncio.wait_for")
    def test_sdk_timeout_with_asyncio(self, mock_wait_for, mock_query, mock_config):
        """Test task execution with asyncio timeout."""
        task = TaskConfig(
            {
                "name": "timeout_task",
                "prompt": "Long running task",
                "verify_command": "make",
                "timeout": 5,
                "max_attempts": 1,
            }
        )

        # Mock asyncio.wait_for to raise TimeoutError
        mock_wait_for.side_effect = TimeoutError()

        runner = TaskRunner(mock_config)
        result = runner.run_task(task)

        assert result.success is False
        assert "timed out after 5 seconds" in result.error
        mock_wait_for.assert_called_once()

    @patch("prompter.runner.query")
    def test_sdk_no_timeout_specified(self, mock_query, mock_config):
        """Test task execution without timeout specified."""
        task = TaskConfig(
            {
                "name": "no_timeout_task",
                "prompt": "Task without timeout",
                "verify_command": "make",
                "max_attempts": 1,
            }
        )

        # Mock SDK query success response
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = "Task completed"
        mock_message.content = [mock_content]

        mock_query.return_value = self.MockAsyncIterator([mock_message])

        # Mock verification success
        with patch("prompter.runner.subprocess.run") as mock_subprocess:
            verify_result = Mock()
            verify_result.returncode = 0
            verify_result.stdout = "Build successful"
            verify_result.stderr = ""
            mock_subprocess.return_value = verify_result

            runner = TaskRunner(mock_config)

            # Spy on asyncio.wait_for to ensure it's not called when no timeout
            with patch(
                "prompter.runner.asyncio.wait_for", wraps=asyncio.wait_for
            ) as mock_wait_for:
                result = runner.run_task(task)

                assert result.success is True
                assert task.timeout is None
                # wait_for should not be called when no timeout is specified
                mock_wait_for.assert_not_called()

    @patch("prompter.runner.query")
    def test_sdk_with_timeout_success(self, mock_query, mock_config):
        """Test successful task execution with timeout specified."""
        task = TaskConfig(
            {
                "name": "timeout_success_task",
                "prompt": "Quick task with timeout",
                "verify_command": "make",
                "timeout": 30,
                "max_attempts": 1,
            }
        )

        # Mock SDK query success response
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = "Task completed quickly"
        mock_message.content = [mock_content]

        mock_query.return_value = self.MockAsyncIterator([mock_message])

        # Mock verification success
        with patch("prompter.runner.subprocess.run") as mock_subprocess:
            verify_result = Mock()
            verify_result.returncode = 0
            verify_result.stdout = "Build successful"
            verify_result.stderr = ""
            mock_subprocess.return_value = verify_result

            runner = TaskRunner(mock_config)
            result = runner.run_task(task)

            assert result.success is True
            assert "Task completed quickly" in result.output

    @patch("prompter.runner.query")
    def test_sdk_multiple_timeout_attempts(self, mock_query, mock_config):
        """Test task execution with multiple timeout attempts."""
        task = TaskConfig(
            {
                "name": "timeout_retry_task",
                "prompt": "Task with timeout",
                "verify_command": "make",
                "timeout": 1,
                "max_attempts": 3,
                "on_failure": "retry",
            }
        )

        # Always timeout to test retry behavior
        # Note: This will be handled by the mock_wait_for.side_effect = TimeoutError()
        # The MockAsyncIterator won't be reached due to the timeout
        mock_query.return_value = self.MockAsyncIterator([])

        runner = TaskRunner(mock_config)

        # Mock asyncio.wait_for to always timeout for this test
        with patch("prompter.runner.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()

            result = runner.run_task(task)

            # Should fail after max attempts with timeout
            assert result.success is False
            assert result.attempts == 3
            assert "timed out after 1 seconds" in result.error
            # wait_for should be called once per attempt
            assert mock_wait_for.call_count == 3
