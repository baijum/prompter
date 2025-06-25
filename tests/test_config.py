"""Tests for the configuration module."""

from unittest.mock import mock_open, patch

import pytest

from prompter.config import PrompterConfig, TaskConfig


class TestTaskConfig:
    """Tests for TaskConfig class."""

    def test_task_config_creation_with_required_fields(self):
        """Test creating TaskConfig with only required fields."""
        config_data = {
            "name": "test_task",
            "prompt": "Fix all warnings",
            "verify_command": "make",
        }

        task = TaskConfig(config_data)

        assert task.name == "test_task"
        assert task.prompt == "Fix all warnings"
        assert task.verify_command == "make"
        assert task.verify_success_code == 0  # default
        assert task.on_success == "next"  # default
        assert task.on_failure == "retry"  # default
        assert task.max_attempts == 3  # default
        assert task.timeout is None  # default

    def test_task_config_creation_with_all_fields(self):
        """Test creating TaskConfig with all fields specified."""
        config_data = {
            "name": "full_task",
            "prompt": "Update documentation",
            "verify_command": "make docs",
            "verify_success_code": 1,
            "on_success": "stop",
            "on_failure": "next",
            "max_attempts": 5,
            "timeout": 600,
        }

        task = TaskConfig(config_data)

        assert task.name == "full_task"
        assert task.prompt == "Update documentation"
        assert task.verify_command == "make docs"
        assert task.verify_success_code == 1
        assert task.on_success == "stop"
        assert task.on_failure == "next"
        assert task.max_attempts == 5
        assert task.timeout == 600

    def test_task_config_repr(self):
        """Test TaskConfig string representation."""
        config_data = {"name": "test_task", "prompt": "test", "verify_command": "test"}
        task = TaskConfig(config_data)

        assert repr(task) == "TaskConfig(name='test_task')"


class TestPrompterConfig:
    """Tests for PrompterConfig class."""

    def test_config_loading_success(self, sample_toml_config):
        """Test successful configuration loading."""
        config = PrompterConfig(sample_toml_config)

        # Check settings
        assert config.check_interval == 3600
        assert config.max_retries == 3
        assert config.claude_command == "claude"
        assert config.working_directory is None

        # Check tasks
        assert len(config.tasks) == 2
        assert config.tasks[0].name == "test_task_1"
        assert config.tasks[1].name == "test_task_2"

    def test_config_loading_with_missing_file(self, temp_dir):
        """Test configuration loading with missing file."""
        missing_file = temp_dir / "missing.toml"

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            PrompterConfig(missing_file)

    @patch("builtins.open", mock_open(read_data="invalid toml content [[["))
    def test_config_loading_with_invalid_toml(self, temp_dir):
        """Test configuration loading with invalid TOML."""
        invalid_file = temp_dir / "invalid.toml"
        invalid_file.touch()  # Create the file so it exists

        with pytest.raises(Exception):  # TOML parsing error
            PrompterConfig(invalid_file)

    def test_config_with_minimal_settings(self, temp_dir):
        """Test configuration with minimal settings."""
        minimal_config = """[[tasks]]
name = "minimal_task"
prompt = "Do something"
verify_command = "echo ok"
"""
        config_file = temp_dir / "minimal.toml"
        config_file.write_text(minimal_config)

        config = PrompterConfig(config_file)

        # Check defaults
        assert config.check_interval == 3600
        assert config.max_retries == 3
        assert config.claude_command == "claude"
        assert config.working_directory is None

        # Check task
        assert len(config.tasks) == 1
        assert config.tasks[0].name == "minimal_task"

    def test_get_task_by_name(self, sample_toml_config):
        """Test getting task by name."""
        config = PrompterConfig(sample_toml_config)

        task = config.get_task_by_name("test_task_1")
        assert task is not None
        assert task.name == "test_task_1"

        task = config.get_task_by_name("nonexistent")
        assert task is None

    def test_validate_valid_config(self, sample_toml_config):
        """Test validation of valid configuration."""
        config = PrompterConfig(sample_toml_config)
        errors = config.validate()
        assert errors == []

    def test_validate_config_with_no_tasks(self, temp_dir):
        """Test validation of configuration with no tasks."""
        empty_config = """[settings]
check_interval = 3600
"""
        config_file = temp_dir / "empty.toml"
        config_file.write_text(empty_config)

        config = PrompterConfig(config_file)
        errors = config.validate()

        assert len(errors) == 1
        assert "No tasks defined" in errors[0]

    def test_validate_config_with_invalid_task_fields(self, temp_dir):
        """Test validation of configuration with invalid task fields."""
        invalid_config = """[[tasks]]
name = ""
prompt = ""
verify_command = ""
on_success = "invalid"
on_failure = "invalid"
max_attempts = 0
"""
        config_file = temp_dir / "invalid_fields.toml"
        config_file.write_text(invalid_config)

        config = PrompterConfig(config_file)
        errors = config.validate()

        assert len(errors) >= 5  # Multiple validation errors
        assert any("name is required" in error for error in errors)
        assert any("prompt is required" in error for error in errors)
        assert any("verify_command is required" in error for error in errors)
        assert any("on_success must be" in error for error in errors)
        assert any("on_failure must be" in error for error in errors)
        assert any("max_attempts must be >= 1" in error for error in errors)

    def test_validate_config_with_missing_required_fields(self, invalid_toml_config):
        """Test validation of configuration with missing required fields."""
        config = PrompterConfig(invalid_toml_config)
        errors = config.validate()

        # Should have errors for missing prompt and verify_command
        assert len(errors) >= 2
        assert any("prompt is required" in error for error in errors)
        assert any("verify_command is required" in error for error in errors)

    def test_config_with_working_directory(self, temp_dir):
        """Test configuration with working directory specified."""
        config_content = f"""[settings]
working_directory = "{temp_dir}"

[[tasks]]
name = "test_task"
prompt = "Do something"
verify_command = "echo ok"
"""
        config_file = temp_dir / "with_workdir.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.working_directory == str(temp_dir)
