"""Tests for the task runner module."""

import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from prompter.config import PrompterConfig, TaskConfig
from prompter.runner import TaskRunner, TaskResult


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

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=PrompterConfig)
        config.check_interval = 0  # No delay for tests
        config.claude_command = "claude"
        config.working_directory = None
        return config

    @pytest.fixture
    def sample_task(self):
        """Create a sample task configuration."""
        return TaskConfig({
            "name": "test_task",
            "prompt": "Fix all warnings",
            "verify_command": "make",
            "verify_success_code": 0,
            "on_success": "next",
            "on_failure": "retry",
            "max_attempts": 3,
        })

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

    @patch('prompter.runner.subprocess.run')
    def test_successful_task_execution(self, mock_subprocess, mock_config, sample_task):
        """Test successful task execution."""
        # Mock Claude command success
        claude_result = Mock()
        claude_result.returncode = 0
        claude_result.stdout = "Task completed successfully"
        
        # Mock verification command success
        verify_result = Mock()
        verify_result.returncode = 0
        verify_result.stdout = "Build successful"
        verify_result.stderr = ""
        
        mock_subprocess.side_effect = [claude_result, verify_result]
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)
        
        assert result.success is True
        assert result.task_name == "test_task"
        assert result.attempts == 1
        assert "Task completed successfully" in result.output

    @patch('prompter.runner.subprocess.run')
    def test_claude_command_failure(self, mock_subprocess, mock_config, sample_task):
        """Test task execution when Claude command fails."""
        # Mock Claude command failure
        claude_result = Mock()
        claude_result.returncode = 1
        claude_result.stderr = "Claude command failed"
        
        mock_subprocess.return_value = claude_result
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)
        
        assert result.success is False
        assert result.attempts == sample_task.max_attempts
        assert "Claude command failed" in result.error

    @patch('prompter.runner.subprocess.run')
    def test_verification_failure_with_retry(self, mock_subprocess, mock_config, sample_task):
        """Test task execution when verification fails but should retry."""
        # Mock Claude command success
        claude_result = Mock()
        claude_result.returncode = 0
        claude_result.stdout = "Task completed"
        
        # Mock verification command failure
        verify_result = Mock()
        verify_result.returncode = 1
        verify_result.stdout = "Build failed"
        verify_result.stderr = "Error in build"
        
        mock_subprocess.side_effect = [claude_result, verify_result] * 3  # Retry 3 times
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)
        
        assert result.success is False
        assert result.attempts == sample_task.max_attempts
        assert "Task failed after" in result.error

    @patch('prompter.runner.subprocess.run')
    def test_verification_failure_with_stop(self, mock_subprocess, mock_config):
        """Test task execution when verification fails and should stop."""
        task = TaskConfig({
            "name": "stop_task",
            "prompt": "Do something",
            "verify_command": "make",
            "on_failure": "stop",
            "max_attempts": 3,
        })
        
        # Mock Claude command success
        claude_result = Mock()
        claude_result.returncode = 0
        claude_result.stdout = "Task completed"
        
        # Mock verification command failure
        verify_result = Mock()
        verify_result.returncode = 1
        verify_result.stdout = "Build failed"
        verify_result.stderr = "Error"
        
        mock_subprocess.side_effect = [claude_result, verify_result]
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(task)  # Use the correct task variable
        
        assert result.success is False
        assert result.attempts == 1  # Should stop after first failure

    @patch('prompter.runner.subprocess.run')
    def test_task_timeout(self, mock_subprocess, mock_config):
        """Test task execution with timeout."""
        task = TaskConfig({
            "name": "timeout_task",
            "prompt": "Long running task",
            "verify_command": "make",
            "timeout": 1,
            "max_attempts": 1,
        })
        
        # Mock subprocess timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("claude", 1)
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(task)
        
        assert result.success is False
        assert "timed out" in result.error

    @patch('prompter.runner.subprocess.run')
    def test_claude_command_not_found(self, mock_subprocess, mock_config, sample_task):
        """Test task execution when Claude command is not found."""
        mock_subprocess.side_effect = FileNotFoundError("Command not found")
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(sample_task)
        
        assert result.success is False
        assert "Claude command not found" in result.error

    @patch('prompter.runner.subprocess.run')
    def test_verification_timeout(self, mock_subprocess, mock_config):
        """Test verification command timeout."""
        # Create a task that stops on failure to avoid retries
        task = TaskConfig({
            "name": "test_task",
            "prompt": "Fix all warnings",
            "verify_command": "make",
            "verify_success_code": 0,
            "on_success": "next",
            "on_failure": "stop",  # Stop on failure to avoid retries
            "max_attempts": 3,
        })
        
        # Mock Claude command success
        claude_result = Mock()
        claude_result.returncode = 0
        claude_result.stdout = "Task completed"
        
        # Mock verification timeout - need to use side_effect that handles shell=True vs shell=False
        def subprocess_side_effect(*args, **kwargs):
            if kwargs.get('shell', False):  # Verification command uses shell=True
                raise subprocess.TimeoutExpired("make", 300)
            else:  # Claude command uses shell=False
                return claude_result
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(task)
        
        assert result.success is False
        # Check that timeout is mentioned in verification output
        assert "timed out" in result.verification_output.lower()

    @patch('prompter.runner.subprocess.run')
    def test_run_all_tasks_success(self, mock_subprocess, mock_config):
        """Test running all tasks successfully."""
        # Create config with multiple tasks
        config = Mock(spec=PrompterConfig)
        config.check_interval = 0
        config.claude_command = "claude"
        config.working_directory = None
        config.tasks = [
            TaskConfig({
                "name": "task1",
                "prompt": "Fix warnings",
                "verify_command": "make",
                "on_success": "next",
                "max_attempts": 1,
            }),
            TaskConfig({
                "name": "task2", 
                "prompt": "Update docs",
                "verify_command": "make docs",
                "on_success": "stop",
                "max_attempts": 1,
            }),
        ]
        
        # Mock successful execution for both tasks
        success_result = Mock()
        success_result.returncode = 0
        success_result.stdout = "Success"
        success_result.stderr = ""
        
        mock_subprocess.return_value = success_result
        
        runner = TaskRunner(config)
        results = runner.run_all_tasks()
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[1].task_name == "task2"

    @patch('prompter.runner.subprocess.run')
    def test_run_all_tasks_stop_on_failure(self, mock_subprocess, mock_config):
        """Test running all tasks with stop on failure."""
        config = Mock(spec=PrompterConfig)
        config.check_interval = 0
        config.claude_command = "claude"
        config.working_directory = None
        config.tasks = [
            TaskConfig({
                "name": "task1",
                "prompt": "Fix warnings",
                "verify_command": "make",
                "on_failure": "stop",
                "max_attempts": 1,
            }),
            TaskConfig({
                "name": "task2",
                "prompt": "Update docs", 
                "verify_command": "make docs",
                "max_attempts": 1,
            }),
        ]
        
        # Mock first task failure, second task should not run
        failure_result = Mock()
        failure_result.returncode = 1
        failure_result.stderr = "Failed"
        
        mock_subprocess.return_value = failure_result
        
        runner = TaskRunner(config)
        results = runner.run_all_tasks()
        
        assert len(results) == 1  # Only first task should run
        assert not results[0].success

    @patch('prompter.runner.subprocess.run')
    def test_task_with_custom_success_code(self, mock_subprocess, mock_config):
        """Test task with custom verification success code."""
        task = TaskConfig({
            "name": "custom_success_task",
            "prompt": "Custom task",
            "verify_command": "custom_command",
            "verify_success_code": 2,  # Custom success code
            "max_attempts": 1,
        })
        
        # Mock Claude success
        claude_result = Mock()
        claude_result.returncode = 0
        claude_result.stdout = "Task completed"
        
        # Mock verification with custom success code
        verify_result = Mock()
        verify_result.returncode = 2  # Matches custom success code
        verify_result.stdout = "Custom success"
        verify_result.stderr = ""
        
        mock_subprocess.side_effect = [claude_result, verify_result]
        
        runner = TaskRunner(mock_config)
        result = runner.run_task(task)
        
        assert result.success is True