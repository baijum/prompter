"""Tests for progress display functionality."""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from prompter.parallel_coordinator import TaskStatus
from prompter.progress_display import (
    ProgressDisplay,
    ProgressDisplayMode,
    TaskProgress,
)


class TestTaskProgress:
    """Test TaskProgress data class."""

    def test_duration_calculation(self):
        """Test duration property calculation."""
        task = TaskProgress(name="test_task", status=TaskStatus.RUNNING)

        # No start time
        assert task.duration is None

        # With start time but no end time
        task.start_time = time.time() - 5
        duration = task.duration
        assert duration is not None
        assert 4.9 < duration < 5.1  # Allow small timing variations

        # With both start and end time
        task.end_time = task.start_time + 10
        assert task.duration == 10

    def test_duration_str(self):
        """Test formatted duration string."""
        task = TaskProgress(name="test_task", status=TaskStatus.RUNNING)

        # No duration
        assert task.duration_str == "--:--"

        # Set specific duration
        task.start_time = 100
        task.end_time = 165  # 1 minute 5 seconds
        assert task.duration_str == "01:05"

        # Large duration
        task.end_time = task.start_time + 3665  # 1 hour 1 minute 5 seconds
        assert task.duration_str == "61:05"


class TestProgressDisplay:
    """Test ProgressDisplay class."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True)
    def test_initialization(self, mock_isatty):
        """Test progress display initialization."""
        display = ProgressDisplay(
            total_tasks=10,
            max_parallel=4,
            workflow_name="Test Workflow",
            mode=ProgressDisplayMode.RICH,
        )

        assert display.total_tasks == 10
        assert display.max_parallel == 4
        assert display.workflow_name == "Test Workflow"
        assert display.mode == ProgressDisplayMode.RICH
        assert len(display.task_progress) == 0

    @patch.dict(os.environ, {"CI": "true"})
    def test_ci_environment_detection(self):
        """Test that CI environments default to simple mode."""
        display = ProgressDisplay(
            total_tasks=5,
            max_parallel=2,
            mode=ProgressDisplayMode.RICH,  # Try to force rich mode
        )

        # Should fall back to simple mode in CI
        assert display.mode == ProgressDisplayMode.SIMPLE

    @patch.dict(os.environ, {"PROMPTER_PROGRESS_MODE": "none"})
    def test_force_no_progress(self):
        """Test forcing no progress display via environment variable."""
        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
        )

        assert display.mode == ProgressDisplayMode.NONE

    @patch.dict(os.environ, {"PROMPTER_PROGRESS_MODE": "simple"})
    def test_force_simple_progress(self):
        """Test forcing simple progress display via environment variable."""
        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
        )

        assert display.mode == ProgressDisplayMode.SIMPLE

    @patch.dict(os.environ, {"TERM": "dumb"})
    def test_dumb_terminal_detection(self):
        """Test that dumb terminals get simple mode."""
        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
        )

        assert display.mode == ProgressDisplayMode.SIMPLE

    def test_task_update(self):
        """Test updating task progress."""
        display = ProgressDisplay(
            total_tasks=3,
            max_parallel=2,
            mode=ProgressDisplayMode.NONE,  # Disable output for tests
        )

        # Update a new task
        display.update_task("task1", TaskStatus.PENDING, dependencies=["task0"])

        assert "task1" in display.task_progress
        task = display.task_progress["task1"]
        assert task.name == "task1"
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == ["task0"]

        # Update to running
        display.update_task(
            "task1", TaskStatus.RUNNING, progress=0.5, message="Processing"
        )
        task = display.task_progress["task1"]
        assert task.status == TaskStatus.RUNNING
        assert task.progress == 0.5
        assert task.message == "Processing"
        assert task.start_time is not None

        # Update to completed
        display.update_task("task1", TaskStatus.COMPLETED, progress=1.0)
        task = display.task_progress["task1"]
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0
        assert task.end_time is not None

    def test_task_update_with_error(self):
        """Test updating task with error."""
        display = ProgressDisplay(
            total_tasks=1, max_parallel=1, mode=ProgressDisplayMode.NONE
        )

        display.update_task("task1", TaskStatus.FAILED, error="Connection timeout")

        task = display.task_progress["task1"]
        assert task.status == TaskStatus.FAILED
        assert task.error == "Connection timeout"

    @patch("sys.stdout.isatty")
    def test_non_tty_detection(self, mock_isatty):
        """Test that non-TTY environments get simple mode."""
        mock_isatty.return_value = False

        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
        )

        assert display.mode == ProgressDisplayMode.SIMPLE

    @patch("prompter.progress_display.sys.platform", "win32")
    @patch.dict(
        os.environ, {"WT_SESSION": "12345", "TERM": "xterm-256color"}, clear=True
    )
    @patch("sys.stdout.isatty", return_value=True)
    def test_windows_terminal_detection(self, mock_isatty):
        """Test Windows Terminal detection."""
        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
        )

        # Modern Windows Terminal should support rich
        assert display._supports_rich_display()

    def test_context_manager(self):
        """Test progress display as context manager."""
        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.NONE
        )

        with patch.object(display, "start") as mock_start:
            with patch.object(display, "stop") as mock_stop:
                with display:
                    mock_start.assert_called_once()
                mock_stop.assert_called_once()

    @patch("builtins.print")
    def test_simple_mode_output(self, mock_print):
        """Test simple mode output formatting."""
        display = ProgressDisplay(
            total_tasks=3,
            max_parallel=2,
            workflow_name="Test Workflow",
            mode=ProgressDisplayMode.SIMPLE,
        )

        # Test start message
        display.start()
        mock_print.assert_called_with("\nStarting Test Workflow with 3 tasks...\n")

        # Test running task update
        display.update_task(
            "task1", TaskStatus.RUNNING, progress=0.0, message="Starting"
        )
        # Should print timestamp, status symbol, and message
        call_args = mock_print.call_args[0][0]
        assert "[>]" in call_args
        assert "task1" in call_args
        assert "Starting" in call_args

        # Test progress update
        display.update_task(
            "task1", TaskStatus.RUNNING, progress=0.5, message="Processing"
        )
        call_args = mock_print.call_args[0][0]
        assert "[##########----------]" in call_args
        assert "50%" in call_args

        # Test completion
        display.update_task("task1", TaskStatus.COMPLETED, progress=1.0)
        call_args = mock_print.call_args[0][0]
        assert "[+]" in call_args
        assert "Completed" in call_args

        # Test failure
        display.update_task(
            "task2",
            TaskStatus.FAILED,
            error="Test error message that is very long and should be truncated",
        )
        call_args = mock_print.call_args[0][0]
        assert "[x]" in call_args
        assert "Failed" in call_args
        assert "Test error message" in call_args

    @patch("builtins.print")
    def test_simple_mode_summary(self, mock_print):
        """Test simple mode final summary."""
        display = ProgressDisplay(
            total_tasks=4,
            max_parallel=2,
            mode=ProgressDisplayMode.SIMPLE,
            workflow_name="Test Pipeline",
        )

        # Simulate some task completions
        display.update_task("task1", TaskStatus.COMPLETED)
        display.update_task("task2", TaskStatus.COMPLETED)
        display.update_task("task3", TaskStatus.FAILED, error="Connection failed")
        display.update_task("task4", TaskStatus.SKIPPED)

        # Stop should print summary
        display.stop()

        # Check that summary was printed
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "Workflow Summary: Test Pipeline" in printed_output
        assert "Total tasks:     4" in printed_output
        assert "Completed:       2 (50.0%)" in printed_output
        assert "Failed:          1 (25.0%)" in printed_output
        assert "Skipped:         1" in printed_output
        assert "Failed tasks:" in printed_output
        assert "task3: Connection failed" in printed_output

    @pytest.mark.slow
    def test_thread_safety(self):
        """Test thread-safe task updates."""
        import threading

        display = ProgressDisplay(
            total_tasks=100, max_parallel=10, mode=ProgressDisplayMode.NONE
        )

        def update_tasks(start_idx):
            for i in range(10):
                task_name = f"task_{start_idx + i}"
                display.update_task(task_name, TaskStatus.RUNNING)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
                display.update_task(task_name, TaskStatus.COMPLETED)

        # Start multiple threads updating tasks
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_tasks, args=(i * 10,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all tasks were updated correctly
        assert len(display.task_progress) == 100
        for task in display.task_progress.values():
            assert task.status == TaskStatus.COMPLETED

    def test_ci_environment_variables(self):
        """Test detection of various CI environment variables."""
        ci_vars = [
            "CI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "CIRCLECI",
            "TRAVIS",
            "JENKINS_URL",
            "TEAMCITY_VERSION",
            "BUILDKITE",
        ]

        for var in ci_vars:
            with patch.dict(os.environ, {var: "true"}):
                display = ProgressDisplay(
                    total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
                )
                assert display.mode == ProgressDisplayMode.SIMPLE

    @patch("prompter.progress_display.Live")
    @patch("sys.stdout.isatty", return_value=True)
    @patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True)
    def test_rich_mode_lifecycle(self, mock_isatty, mock_live_class):
        """Test rich mode start and stop."""
        mock_live = MagicMock()
        mock_live_class.return_value = mock_live

        display = ProgressDisplay(
            total_tasks=5, max_parallel=2, mode=ProgressDisplayMode.RICH
        )

        # Start should create and start Live
        display.start()
        mock_live_class.assert_called_once()
        mock_live.start.assert_called_once()

        # Stop should stop Live
        display.stop()
        mock_live.stop.assert_called_once()
        assert display.live is None
