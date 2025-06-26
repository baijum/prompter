"""Tests for interactive configuration customization."""

from unittest.mock import Mock

from prompter.cli.init.analyzer import AnalysisResult
from prompter.cli.init.interactive import InteractiveConfigurator, TaskConfig
from prompter.utils.console import Console


class TestTaskConfig:
    """Test the TaskConfig dataclass."""

    def test_default_values(self):
        """Test TaskConfig with default values."""
        task = TaskConfig(
            name="test_task", prompt="Do something", verify_command="echo done"
        )

        assert task.name == "test_task"
        assert task.prompt == "Do something"
        assert task.verify_command == "echo done"
        assert task.timeout == 300
        assert task.on_success == "next"
        assert task.on_failure == "retry"
        assert task.max_attempts == 3

    def test_custom_values(self):
        """Test TaskConfig with custom values."""
        task = TaskConfig(
            name="custom_task",
            prompt="Custom prompt",
            verify_command="test command",
            timeout=600,
            on_success="stop",
            on_failure="next",
            max_attempts=5,
        )

        assert task.timeout == 600
        assert task.on_success == "stop"
        assert task.on_failure == "next"
        assert task.max_attempts == 5

    def test_to_dict(self):
        """Test conversion to dictionary."""
        task = TaskConfig(
            name="test_task", prompt="Do something", verify_command="echo done"
        )

        result = task.to_dict()
        assert isinstance(result, dict)
        assert result["name"] == "test_task"
        assert result["prompt"] == "Do something"
        assert result["verify_command"] == "echo done"
        assert result["timeout"] == 300
        assert result["on_success"] == "next"
        assert result["on_failure"] == "retry"
        assert result["max_attempts"] == 3


class TestInteractiveConfigurator:
    """Test the InteractiveConfigurator class."""

    def test_initialization(self):
        """Test configurator initialization."""
        console = Console()
        configurator = InteractiveConfigurator(console)
        assert configurator.console == console

    def test_confirm_tools_accept_all(self):
        """Test confirming all detected tools."""
        console = Mock(spec=Console)
        console.get_input.return_value = ""  # Accept all

        configurator = InteractiveConfigurator(console)

        analysis = AnalysisResult(
            build_system="make",
            build_command="make build",
            test_framework="pytest",
            test_command="pytest",
            linter="ruff",
            lint_command="ruff check .",
        )

        config = {}
        result = configurator._confirm_tools(config, analysis)

        assert "tools" in result
        assert result["tools"]["build_command"] == "make build"
        assert result["tools"]["test_command"] == "pytest"
        assert result["tools"]["lint_command"] == "ruff check ."

    def test_confirm_tools_custom_command(self):
        """Test providing custom commands for tools."""
        console = Mock(spec=Console)
        console.get_input.side_effect = ["n", "pytest -xvs"]  # Decline, then custom

        configurator = InteractiveConfigurator(console)

        analysis = AnalysisResult(test_framework="pytest", test_command="pytest")

        config = {}
        result = configurator._confirm_tools(config, analysis)

        assert result["tools"]["test_command"] == "pytest -xvs"

    def test_customize_tasks_keep_all(self):
        """Test keeping all tasks without modification."""
        console = Mock(spec=Console)
        console.get_input.return_value = "keep"

        configurator = InteractiveConfigurator(console)

        tasks = [
            {"name": "task1", "prompt": "Do task 1", "verify_command": "test1"},
            {"name": "task2", "prompt": "Do task 2", "verify_command": "test2"},
        ]

        result = configurator._customize_tasks(tasks)

        assert len(result) == 2
        assert all(isinstance(t, TaskConfig) for t in result)
        assert result[0].name == "task1"
        assert result[1].name == "task2"

    def test_customize_tasks_edit(self):
        """Test editing a task."""
        console = Mock(spec=Console)
        console.get_input.side_effect = [
            "edit",  # Action
            "edited_task",  # New name
            "New prompt",  # New prompt
            "",  # Keep verify command
            "600",  # New timeout
            "stop",  # New on_success
            "stop",  # New on_failure
            "1",  # New max_attempts
        ]

        configurator = InteractiveConfigurator(console)

        tasks = [
            {
                "name": "original_task",
                "prompt": "Original prompt",
                "verify_command": "test",
            }
        ]

        result = configurator._customize_tasks(tasks)

        assert len(result) == 1
        assert result[0].name == "edited_task"
        assert result[0].prompt == "New prompt"
        assert result[0].verify_command == "test"  # Kept original
        assert result[0].timeout == 600
        assert result[0].on_success == "stop"
        assert result[0].on_failure == "stop"
        assert result[0].max_attempts == 1

    def test_customize_tasks_delete(self):
        """Test deleting tasks."""
        console = Mock(spec=Console)
        console.get_input.side_effect = ["delete", "keep"]

        configurator = InteractiveConfigurator(console)

        tasks = [
            {"name": "task1", "prompt": "Delete me", "verify_command": "test1"},
            {"name": "task2", "prompt": "Keep me", "verify_command": "test2"},
        ]

        result = configurator._customize_tasks(tasks)

        assert len(result) == 1
        assert result[0].name == "task2"

    def test_add_custom_tasks(self):
        """Test adding custom tasks interactively."""
        console = Mock(spec=Console)
        console.get_input.side_effect = [
            "y",  # Add a task
            "custom_task",  # Name
            "Custom prompt",  # Prompt
            "echo done",  # Verify command
            "",  # Default timeout
            "",  # Default on_success
            "",  # Default on_failure
            "",  # Default max_attempts
            "n",  # Don't add more
        ]

        configurator = InteractiveConfigurator(console)
        result = configurator._add_custom_tasks()

        assert len(result) == 1
        assert result[0].name == "custom_task"
        assert result[0].prompt == "Custom prompt"
        assert result[0].verify_command == "echo done"
        assert result[0].timeout == 300  # Default

    def test_add_custom_tasks_validation(self):
        """Test validation when adding custom tasks."""
        console = Mock(spec=Console)
        console.get_input.side_effect = [
            "y",  # Add a task
            "",  # Empty name (invalid)
            "y",  # Try again
            "valid_task",  # Valid name
            "",  # Empty prompt (invalid)
            "y",  # Try again
            "valid_task",  # Valid name
            "Valid prompt",  # Valid prompt
            "",  # Empty verify command (invalid)
            "n",  # Give up
        ]
        console.print_warning = Mock()

        configurator = InteractiveConfigurator(console)
        result = configurator._add_custom_tasks()

        assert len(result) == 0
        assert console.print_warning.call_count >= 3

    def test_customize_settings(self):
        """Test customizing global settings."""
        console = Mock(spec=Console)
        console.get_input.side_effect = [
            "/custom/path",  # Working directory
            "60",  # Check interval
            "y",  # Allow infinite loops
        ]

        configurator = InteractiveConfigurator(console)
        settings = {}

        result = configurator._customize_settings(settings)

        assert result["working_directory"] == "/custom/path"
        assert result["check_interval"] == 60
        assert result["allow_infinite_loops"] is True

    def test_customize_full_flow(self):
        """Test full customization flow."""
        console = Mock(spec=Console)
        # Mock all inputs for full flow
        console.get_input.side_effect = [
            # Tool confirmation
            "",  # Accept build
            "n",
            "pytest -xvs",  # Custom test command
            # Task customization
            "keep",  # Keep first task
            # Add custom task
            "n",  # No custom tasks
            # Settings
            "",  # Default working directory
            "",  # Default check interval
            "n",  # No infinite loops
        ]

        configurator = InteractiveConfigurator(console)

        analysis = AnalysisResult(
            build_system="make",
            build_command="make",
            test_framework="pytest",
            test_command="pytest",
        )

        config = {
            "tasks": [
                {
                    "name": "existing_task",
                    "prompt": "Do something",
                    "verify_command": "test",
                }
            ]
        }

        result = configurator.customize(config, analysis)

        assert "tools" in result
        assert result["tools"]["test_command"] == "pytest -xvs"
        assert "settings" in result
        assert len(result["tasks"]) == 1
        assert isinstance(result["tasks"][0], TaskConfig)
