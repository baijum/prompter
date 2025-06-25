"""Tests for the state management module."""

import json
import time
from pathlib import Path
from unittest.mock import mock_open, patch

from prompter.runner import TaskResult
from prompter.state import StateManager, TaskState


class TestTaskState:
    """Tests for TaskState class."""

    def test_task_state_creation_with_defaults(self):
        """Test TaskState creation with default values."""
        state = TaskState("test_task")

        assert state.name == "test_task"
        assert state.status == "pending"
        assert state.attempts == 0
        assert state.last_attempt is None
        assert state.last_success is None
        assert state.error_message == ""

    def test_task_state_creation_with_all_params(self):
        """Test TaskState creation with all parameters."""
        now = time.time()
        state = TaskState(
            name="test_task",
            status="completed",
            attempts=3,
            last_attempt=now,
            last_success=now,
            error_message="Some error",
        )

        assert state.name == "test_task"
        assert state.status == "completed"
        assert state.attempts == 3
        assert state.last_attempt == now
        assert state.last_success == now
        assert state.error_message == "Some error"

    def test_task_state_to_dict(self):
        """Test TaskState serialization to dictionary."""
        now = time.time()
        state = TaskState(
            name="test_task",
            status="running",
            attempts=2,
            last_attempt=now,
            last_success=None,
            error_message="Error occurred",
        )

        expected = {
            "name": "test_task",
            "status": "running",
            "attempts": 2,
            "last_attempt": now,
            "last_success": None,
            "error_message": "Error occurred",
        }

        assert state.to_dict() == expected

    def test_task_state_from_dict(self):
        """Test TaskState deserialization from dictionary."""
        now = time.time()
        data = {
            "name": "test_task",
            "status": "failed",
            "attempts": 4,
            "last_attempt": now,
            "last_success": now - 100,
            "error_message": "Task failed",
        }

        state = TaskState.from_dict(data)

        assert state.name == "test_task"
        assert state.status == "failed"
        assert state.attempts == 4
        assert state.last_attempt == now
        assert state.last_success == now - 100
        assert state.error_message == "Task failed"

    def test_task_state_from_dict_with_defaults(self):
        """Test TaskState deserialization with missing optional fields."""
        data = {"name": "minimal_task"}

        state = TaskState.from_dict(data)

        assert state.name == "minimal_task"
        assert state.status == "pending"
        assert state.attempts == 0
        assert state.last_attempt is None
        assert state.last_success is None
        assert state.error_message == ""


class TestStateManager:
    """Tests for StateManager class."""

    def test_state_manager_initialization(self, temp_dir):
        """Test StateManager initialization."""
        state_file = temp_dir / "test_state.json"
        manager = StateManager(state_file)

        assert manager.state_file == state_file
        assert manager.session_id is not None
        assert manager.start_time > 0
        assert manager.task_states == {}
        assert manager.results_history == []

    def test_state_manager_with_default_file(self):
        """Test StateManager initialization with default file."""
        with patch("prompter.state.Path.exists", return_value=False):
            manager = StateManager()

            assert manager.state_file == Path(".prompter_state.json")

    @patch("builtins.open", new_callable=mock_open)
    @patch("prompter.state.Path.exists", return_value=True)
    def test_load_existing_state(self, mock_exists, mock_file, temp_dir):
        """Test loading existing state from file."""
        state_data = {
            "session_id": "123456789",
            "start_time": 1234567890.0,
            "last_update": 1234567900.0,
            "task_states": [
                {
                    "name": "task1",
                    "status": "completed",
                    "attempts": 2,
                    "last_attempt": 1234567895.0,
                    "last_success": 1234567895.0,
                    "error_message": "",
                }
            ],
            "results_history": [
                {
                    "session_id": "123456789",
                    "task_name": "task1",
                    "success": True,
                    "attempts": 2,
                    "timestamp": 1234567895.0,
                    "output": "Task completed",
                    "error": "",
                }
            ],
        }

        mock_file.return_value.read.return_value = json.dumps(state_data)

        state_file = temp_dir / "existing_state.json"
        manager = StateManager(state_file)

        assert len(manager.task_states) == 1
        assert "task1" in manager.task_states
        assert manager.task_states["task1"].status == "completed"
        assert len(manager.results_history) == 1

    @patch("builtins.open", new_callable=mock_open)
    @patch("prompter.state.Path.exists", return_value=True)
    def test_load_state_with_invalid_json(self, mock_exists, mock_file, temp_dir):
        """Test loading state with invalid JSON."""
        mock_file.return_value.read.return_value = "invalid json"

        state_file = temp_dir / "invalid_state.json"
        manager = StateManager(state_file)

        # Should handle gracefully and start with empty state
        assert manager.task_states == {}
        assert manager.results_history == []

    @patch("builtins.open", new_callable=mock_open)
    def test_save_state(self, mock_file, temp_dir):
        """Test saving state to file."""
        state_file = temp_dir / "save_test.json"
        manager = StateManager(state_file)

        # Add some state
        manager.task_states["test_task"] = TaskState("test_task", "completed")

        manager.save_state()

        # Verify file was written
        mock_file.assert_called_with(state_file, "w")
        # Get the written data from the write call
        write_calls = mock_file.return_value.__enter__.return_value.write.call_args_list
        written_data = "".join(call[0][0] for call in write_calls)
        data = json.loads(written_data)

        assert data["session_id"] == manager.session_id
        assert data["start_time"] == manager.start_time
        assert len(data["task_states"]) == 1
        assert data["task_states"][0]["name"] == "test_task"

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_state_with_io_error(self, mock_file, temp_dir):
        """Test saving state when IO error occurs."""
        state_file = temp_dir / "readonly_state.json"
        manager = StateManager(state_file)

        # Should handle gracefully without raising exception
        manager.save_state()

    def test_get_task_state_new_task(self, temp_dir):
        """Test getting state for a new task."""
        state_file = temp_dir / "new_task_state.json"
        manager = StateManager(state_file)

        state = manager.get_task_state("new_task")

        assert state.name == "new_task"
        assert state.status == "pending"
        assert "new_task" in manager.task_states

    def test_get_task_state_existing_task(self, temp_dir):
        """Test getting state for an existing task."""
        state_file = temp_dir / "existing_task_state.json"
        manager = StateManager(state_file)

        # Add a task state
        original_state = TaskState("existing_task", "running", attempts=1)
        manager.task_states["existing_task"] = original_state

        state = manager.get_task_state("existing_task")

        assert state is original_state
        assert state.status == "running"

    @patch.object(StateManager, "save_state")
    def test_update_task_state_success(self, mock_save, temp_dir):
        """Test updating task state with successful result."""
        state_file = temp_dir / "update_success_state.json"
        manager = StateManager(state_file)

        result = TaskResult(
            task_name="success_task",
            success=True,
            output="Task completed successfully",
            attempts=2,
        )

        manager.update_task_state(result)

        state = manager.task_states["success_task"]
        assert state.status == "completed"
        assert state.attempts == 2
        assert state.last_success == result.timestamp
        assert state.error_message == ""

        # Check results history
        assert len(manager.results_history) == 1
        history_entry = manager.results_history[0]
        assert history_entry["task_name"] == "success_task"
        assert history_entry["success"] is True

        mock_save.assert_called_once()

    @patch.object(StateManager, "save_state")
    def test_update_task_state_failure(self, mock_save, temp_dir):
        """Test updating task state with failed result."""
        state_file = temp_dir / "update_failure_state.json"
        manager = StateManager(state_file)

        result = TaskResult(
            task_name="failed_task",
            success=False,
            error="Task failed with error",
            attempts=3,
        )

        manager.update_task_state(result)

        state = manager.task_states["failed_task"]
        assert state.status == "failed"
        assert state.attempts == 3
        assert state.last_success is None
        assert state.error_message == "Task failed with error"

        mock_save.assert_called_once()

    @patch.object(StateManager, "save_state")
    def test_mark_task_running(self, mock_save, temp_dir):
        """Test marking a task as running."""
        state_file = temp_dir / "running_state.json"
        manager = StateManager(state_file)

        manager.mark_task_running("running_task")

        state = manager.task_states["running_task"]
        assert state.status == "running"
        mock_save.assert_called_once()

    def test_get_summary(self, temp_dir):
        """Test getting state summary."""
        state_file = temp_dir / "summary_state.json"
        manager = StateManager(state_file)

        # Add various task states
        manager.task_states["completed_task"] = TaskState("completed_task", "completed")
        manager.task_states["failed_task"] = TaskState("failed_task", "failed")
        manager.task_states["running_task"] = TaskState("running_task", "running")
        manager.task_states["pending_task"] = TaskState("pending_task", "pending")

        # Add some results history
        manager.results_history = [{"result": 1}, {"result": 2}]

        summary = manager.get_summary()

        assert summary["session_id"] == manager.session_id
        assert summary["start_time"] == manager.start_time
        assert summary["total_tasks"] == 4
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["running"] == 1
        assert summary["pending"] == 1
        assert summary["total_results"] == 2

    def test_clear_state(self, temp_dir):
        """Test clearing all state."""
        state_file = temp_dir / "clear_state.json"
        manager = StateManager(state_file)

        # Add some state
        manager.task_states["task1"] = TaskState("task1")
        manager.results_history = [{"result": 1}]

        # Create the file so it exists
        state_file.write_text('{"test": "data"}')
        assert state_file.exists()

        manager.clear_state()

        assert manager.task_states == {}
        assert manager.results_history == []
        assert not state_file.exists()  # File should be deleted

    def test_get_failed_tasks(self, temp_dir):
        """Test getting list of failed tasks."""
        state_file = temp_dir / "failed_tasks_state.json"
        manager = StateManager(state_file)

        manager.task_states["completed_task"] = TaskState("completed_task", "completed")
        manager.task_states["failed_task1"] = TaskState("failed_task1", "failed")
        manager.task_states["failed_task2"] = TaskState("failed_task2", "failed")
        manager.task_states["pending_task"] = TaskState("pending_task", "pending")

        failed_tasks = manager.get_failed_tasks()

        assert len(failed_tasks) == 2
        assert "failed_task1" in failed_tasks
        assert "failed_task2" in failed_tasks

    def test_get_completed_tasks(self, temp_dir):
        """Test getting list of completed tasks."""
        state_file = temp_dir / "completed_tasks_state.json"
        manager = StateManager(state_file)

        manager.task_states["completed_task1"] = TaskState(
            "completed_task1", "completed"
        )
        manager.task_states["completed_task2"] = TaskState(
            "completed_task2", "completed"
        )
        manager.task_states["failed_task"] = TaskState("failed_task", "failed")
        manager.task_states["pending_task"] = TaskState("pending_task", "pending")

        completed_tasks = manager.get_completed_tasks()

        assert len(completed_tasks) == 2
        assert "completed_task1" in completed_tasks
        assert "completed_task2" in completed_tasks

    def test_results_history_truncation(self, temp_dir):
        """Test that output and error in results history are truncated."""
        state_file = temp_dir / "truncation_state.json"
        manager = StateManager(state_file)

        long_output = "A" * 1000  # 1000 characters
        long_error = "B" * 1000  # 1000 characters

        result = TaskResult(
            task_name="truncation_task",
            success=False,
            output=long_output,
            error=long_error,
        )

        manager.update_task_state(result)

        history_entry = manager.results_history[0]
        assert len(history_entry["output"]) == 500  # Truncated to 500 chars
        assert len(history_entry["error"]) == 500  # Truncated to 500 chars
        assert history_entry["output"] == "A" * 500
        assert history_entry["error"] == "B" * 500
