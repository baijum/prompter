"""Test helper utilities and fixtures."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from prompter.config import PrompterConfig, TaskConfig
from prompter.runner import TaskResult
from prompter.state import TaskState


class MockSubprocessResult:
    """Mock object for subprocess.run results."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TaskConfigBuilder:
    """Builder pattern for creating TaskConfig objects in tests."""

    def __init__(self):
        self._config = {
            "name": "test_task",
            "prompt": "Test prompt",
            "verify_command": "echo ok",
        }

    def name(self, name: str) -> "TaskConfigBuilder":
        self._config["name"] = name
        return self

    def prompt(self, prompt: str) -> "TaskConfigBuilder":
        self._config["prompt"] = prompt
        return self

    def verify_command(self, command: str) -> "TaskConfigBuilder":
        self._config["verify_command"] = command
        return self

    def verify_success_code(self, code: int) -> "TaskConfigBuilder":
        self._config["verify_success_code"] = code
        return self

    def on_success(self, action: str) -> "TaskConfigBuilder":
        self._config["on_success"] = action
        return self

    def on_failure(self, action: str) -> "TaskConfigBuilder":
        self._config["on_failure"] = action
        return self

    def max_attempts(self, attempts: int) -> "TaskConfigBuilder":
        self._config["max_attempts"] = attempts
        return self

    def timeout(self, timeout: int) -> "TaskConfigBuilder":
        self._config["timeout"] = timeout
        return self

    def build(self) -> TaskConfig:
        return TaskConfig(self._config)


class TaskResultBuilder:
    """Builder pattern for creating TaskResult objects in tests."""

    def __init__(self):
        self._task_name = "test_task"
        self._success = True
        self._output = ""
        self._error = ""
        self._verification_output = ""
        self._attempts = 1

    def task_name(self, name: str) -> "TaskResultBuilder":
        self._task_name = name
        return self

    def success(self, success: bool) -> "TaskResultBuilder":
        self._success = success
        return self

    def output(self, output: str) -> "TaskResultBuilder":
        self._output = output
        return self

    def error(self, error: str) -> "TaskResultBuilder":
        self._error = error
        return self

    def verification_output(self, output: str) -> "TaskResultBuilder":
        self._verification_output = output
        return self

    def attempts(self, attempts: int) -> "TaskResultBuilder":
        self._attempts = attempts
        return self

    def build(self) -> TaskResult:
        return TaskResult(
            task_name=self._task_name,
            success=self._success,
            output=self._output,
            error=self._error,
            verification_output=self._verification_output,
            attempts=self._attempts,
        )


def create_mock_config(tasks: list = None, **settings) -> Mock:
    """Create a mock PrompterConfig object."""
    config = Mock(spec=PrompterConfig)

    # Default settings
    config.check_interval = settings.get("check_interval", 0)
    config.max_retries = settings.get("max_retries", 3)
    config.claude_command = settings.get("claude_command", "claude")
    config.working_directory = settings.get("working_directory")

    # Default tasks
    if tasks is None:
        tasks = [TaskConfigBuilder().name("default_task").build()]
    config.tasks = tasks

    # Mock methods
    config.validate.return_value = []
    config.get_task_by_name.side_effect = lambda name: next(
        (task for task in config.tasks if task.name == name), None
    )

    return config


def create_temp_config_file(content: str, temp_dir: Path) -> Path:
    """Create a temporary TOML configuration file."""
    config_file = temp_dir / "test_config.toml"
    config_file.write_text(content)
    return config_file


def assert_task_result_matches(result: TaskResult, expected: dict[str, Any]) -> None:
    """Assert that a TaskResult matches expected values."""
    if "task_name" in expected:
        assert result.task_name == expected["task_name"]
    if "success" in expected:
        assert result.success == expected["success"]
    if "attempts" in expected:
        assert result.attempts == expected["attempts"]
    if "error" in expected:
        assert expected["error"] in result.error
    if "output" in expected:
        assert expected["output"] in result.output


def assert_task_state_matches(state: TaskState, expected: dict[str, Any]) -> None:
    """Assert that a TaskState matches expected values."""
    if "name" in expected:
        assert state.name == expected["name"]
    if "status" in expected:
        assert state.status == expected["status"]
    if "attempts" in expected:
        assert state.attempts == expected["attempts"]
    if "error_message" in expected:
        assert expected["error_message"] in state.error_message


@pytest.fixture
def task_config_builder():
    """Provide TaskConfigBuilder fixture."""
    return TaskConfigBuilder


@pytest.fixture
def task_result_builder():
    """Provide TaskResultBuilder fixture."""
    return TaskResultBuilder


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess result."""
    return MockSubprocessResult(returncode=0, stdout="Success")


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess result."""
    return MockSubprocessResult(returncode=1, stderr="Error")


# Additional fixtures for common test scenarios


@pytest.fixture
def simple_task_config():
    """Simple task configuration for testing."""
    return TaskConfigBuilder().name("simple").prompt("Do something").build()


@pytest.fixture
def retry_task_config():
    """Task configuration with retry logic."""
    return (
        TaskConfigBuilder()
        .name("retry_task")
        .prompt("Task that might fail")
        .on_failure("retry")
        .max_attempts(3)
        .build()
    )


@pytest.fixture
def stop_task_config():
    """Task configuration that stops on failure."""
    return (
        TaskConfigBuilder()
        .name("stop_task")
        .prompt("Task that stops on failure")
        .on_failure("stop")
        .max_attempts(1)
        .build()
    )


@pytest.fixture
def successful_task_result():
    """Successful task result for testing."""
    return (
        TaskResultBuilder()
        .task_name("test_task")
        .success(True)
        .output("Task completed successfully")
        .attempts(1)
        .build()
    )


@pytest.fixture
def failed_task_result():
    """Failed task result for testing."""
    return (
        TaskResultBuilder()
        .task_name("test_task")
        .success(False)
        .error("Task failed")
        .attempts(3)
        .build()
    )


class TestTaskConfigBuilder:
    """Tests for the TaskConfigBuilder helper."""

    def test_builder_default_values(self):
        """Test builder creates config with default values."""
        config = TaskConfigBuilder().build()

        assert config.name == "test_task"
        assert config.prompt == "Test prompt"
        assert config.verify_command == "echo ok"

    def test_builder_custom_values(self):
        """Test builder with custom values."""
        config = (
            TaskConfigBuilder()
            .name("custom_task")
            .prompt("Custom prompt")
            .verify_command("custom command")
            .max_attempts(5)
            .build()
        )

        assert config.name == "custom_task"
        assert config.prompt == "Custom prompt"
        assert config.verify_command == "custom command"
        assert config.max_attempts == 5

    def test_builder_chaining(self):
        """Test that builder methods can be chained."""
        config = (
            TaskConfigBuilder()
            .name("chained")
            .prompt("Chained prompt")
            .on_success("stop")
            .on_failure("retry")
            .timeout(600)
            .build()
        )

        assert config.name == "chained"
        assert config.on_success == "stop"
        assert config.on_failure == "retry"
        assert config.timeout == 600


class TestTaskResultBuilder:
    """Tests for the TaskResultBuilder helper."""

    def test_result_builder_defaults(self):
        """Test result builder with default values."""
        result = TaskResultBuilder().build()

        assert result.task_name == "test_task"
        assert result.success is True
        assert result.attempts == 1

    def test_result_builder_custom_values(self):
        """Test result builder with custom values."""
        result = (
            TaskResultBuilder()
            .task_name("custom_result")
            .success(False)
            .error("Custom error")
            .attempts(3)
            .build()
        )

        assert result.task_name == "custom_result"
        assert result.success is False
        assert result.error == "Custom error"
        assert result.attempts == 3


class TestAssertionHelpers:
    """Tests for assertion helper functions."""

    def test_assert_task_result_matches(self):
        """Test task result assertion helper."""
        result = TaskResultBuilder().task_name("test").success(True).build()

        # Should not raise
        assert_task_result_matches(result, {"task_name": "test", "success": True})

        # Should raise
        with pytest.raises(AssertionError):
            assert_task_result_matches(result, {"task_name": "wrong"})

    def test_assert_task_state_matches(self):
        """Test task state assertion helper."""
        state = TaskState("test", "completed", attempts=2)

        # Should not raise
        assert_task_state_matches(state, {"name": "test", "status": "completed"})

        # Should raise
        with pytest.raises(AssertionError):
            assert_task_state_matches(state, {"status": "failed"})
