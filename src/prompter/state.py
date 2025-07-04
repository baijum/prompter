"""State management for tracking task progress and persistence."""

import json
import threading
import time
import contextlib
from pathlib import Path
from typing import Any

from .logging import get_logger
from .runner import TaskResult


class TaskState:
    """State information for a single task."""

    def __init__(
        self,
        name: str,
        status: str = "pending",
        attempts: int = 0,
        last_attempt: float | None = None,
        last_success: float | None = None,
        error_message: str = "",
        claude_session_id: str | None = None,
    ) -> None:
        self.name = name
        self.status = status  # pending, running, completed, failed
        self.attempts = attempts
        self.last_attempt = last_attempt
        self.last_success = last_success
        self.error_message = error_message
        self.claude_session_id = claude_session_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "attempts": self.attempts,
            "last_attempt": self.last_attempt,
            "last_success": self.last_success,
            "error_message": self.error_message,
            "claude_session_id": self.claude_session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            status=data.get("status", "pending"),
            attempts=data.get("attempts", 0),
            last_attempt=data.get("last_attempt"),
            last_success=data.get("last_success"),
            error_message=data.get("error_message", ""),
            claude_session_id=data.get("claude_session_id"),
        )


class StateManager:
    """Manages persistent state for task execution with thread-safe operations."""

    def __init__(self, state_file: Path | None = None) -> None:
        self.state_file = state_file or Path(".prompter_state.json")
        self.session_id = str(int(time.time()))
        self.start_time = time.time()
        self.task_states: dict[str, TaskState] = {}
        self.results_history: list[dict[str, Any]] = []
        self.logger = get_logger("state")

        # Thread safety lock for concurrent access
        self._lock = threading.Lock()

        # Load existing state if available
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if self.state_file.exists():
            self.logger.debug(f"Loading state from {self.state_file}")
            try:
                with open(self.state_file) as f:
                    data = json.load(f)

                self.logger.debug(
                    f"State file loaded successfully, found {len(data.get('task_states', []))} task states"
                )

                # Load task states
                for task_data in data.get("task_states", []):
                    state = TaskState.from_dict(task_data)
                    self.task_states[state.name] = state
                    self.logger.debug(
                        f"Loaded task state: {state.name} - status={state.status}, attempts={state.attempts}"
                    )

                # Load results history
                self.results_history = data.get("results_history", [])
                self.logger.debug(
                    f"Loaded {len(self.results_history)} results from history"
                )

            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Could not load state file: {e}")
        else:
            self.logger.debug(f"No existing state file found at {self.state_file}")

    def save_state(self) -> None:
        """Save current state to file (thread-safe)."""
        with self._lock:
            data = {
                "session_id": self.session_id,
                "start_time": self.start_time,
                "last_update": time.time(),
                "task_states": [state.to_dict() for state in self.task_states.values()],
                "results_history": self.results_history,
            }

            self.logger.debug(
                f"Saving state to {self.state_file}: {len(self.task_states)} tasks, {len(self.results_history)} results"
            )

            try:
                # Use atomic write to prevent corruption during concurrent access
                temp_file = self.state_file.with_suffix(".tmp")
                with open(temp_file, "w") as f:
                    json.dump(data, f, indent=2)
                temp_file.replace(self.state_file)
                self.logger.debug(f"State saved successfully to {self.state_file}")
            except OSError as e:
                self.logger.warning(f"Could not save state file: {e}")
                # Clean up temp file if it exists
                if temp_file.exists():
                    with contextlib.suppress(Exception):
                        temp_file.unlink()

    def get_task_state(self, task_name: str) -> TaskState:
        """Get state for a task, creating if it doesn't exist (thread-safe)."""
        with self._lock:
            if task_name not in self.task_states:
                self.logger.debug(f"Creating new task state for {task_name}")
                self.task_states[task_name] = TaskState(task_name)
            return self.task_states[task_name]

    def update_task_state(self, result: TaskResult) -> None:
        """Update task state based on execution result (thread-safe)."""
        with self._lock:
            self.logger.debug(
                f"Updating task state for {result.task_name}: success={result.success}, attempts={result.attempts}"
            )
            # Get task state without lock since we already have it
            if result.task_name not in self.task_states:
                self.logger.debug(f"Creating new task state for {result.task_name}")
                self.task_states[result.task_name] = TaskState(result.task_name)
            state = self.task_states[result.task_name]

            old_status = state.status
            state.attempts = result.attempts
            state.last_attempt = result.timestamp

            # Update claude_session_id if available
            if result.session_id:
                state.claude_session_id = result.session_id
                self.logger.debug(
                    f"Updated Claude session ID for {result.task_name}: {result.session_id}"
                )

            if result.success:
                state.status = "completed"
                state.last_success = result.timestamp
                state.error_message = ""
                self.logger.debug(
                    f"Task {result.task_name} status changed: {old_status} -> completed"
                )
            else:
                state.status = "failed"
                state.error_message = result.error
                self.logger.debug(
                    f"Task {result.task_name} status changed: {old_status} -> failed, error: {result.error[:100]}..."
                )

            # Add to results history
            self.results_history.append(
                {
                    "session_id": self.session_id,
                    "claude_session_id": result.session_id,
                    "task_name": result.task_name,
                    "success": result.success,
                    "attempts": result.attempts,
                    "timestamp": result.timestamp,
                    "output": result.output[:500]
                    if result.output
                    else "",  # Truncate for storage
                    "error": result.error[:500] if result.error else "",
                }
            )

        # Save state after releasing lock to minimize contention
        self.save_state()

    def mark_task_running(self, task_name: str) -> None:
        """Mark a task as currently running (thread-safe)."""
        with self._lock:
            # Get task state without lock since we already have it
            if task_name not in self.task_states:
                self.logger.debug(f"Creating new task state for {task_name}")
                self.task_states[task_name] = TaskState(task_name)
            state = self.task_states[task_name]
            old_status = state.status
            state.status = "running"
            self.logger.debug(
                f"Task {task_name} status changed: {old_status} -> running"
            )

        # Save state after releasing lock
        self.save_state()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current state (thread-safe)."""
        with self._lock:
            completed = sum(
                1 for state in self.task_states.values() if state.status == "completed"
            )
            failed = sum(
                1 for state in self.task_states.values() if state.status == "failed"
            )
            running = sum(
                1 for state in self.task_states.values() if state.status == "running"
            )
            pending = sum(
                1 for state in self.task_states.values() if state.status == "pending"
            )

            return {
                "session_id": self.session_id,
                "start_time": self.start_time,
                "total_tasks": len(self.task_states),
                "completed": completed,
                "failed": failed,
                "running": running,
                "pending": pending,
                "total_results": len(self.results_history),
            }

    def clear_state(self) -> None:
        """Clear all state (useful for fresh starts) (thread-safe)."""
        with self._lock:
            self.logger.debug(
                f"Clearing all state: {len(self.task_states)} tasks, {len(self.results_history)} results"
            )
            self.task_states.clear()
            self.results_history.clear()
            if self.state_file.exists():
                self.logger.debug(f"Deleting state file: {self.state_file}")
                self.state_file.unlink()
            self.logger.debug("State cleared successfully")

    def get_failed_tasks(self) -> list[str]:
        """Get list of task names that have failed (thread-safe)."""
        with self._lock:
            return [
                name
                for name, state in self.task_states.items()
                if state.status == "failed"
            ]

    def get_completed_tasks(self) -> list[str]:
        """Get list of task names that have completed successfully (thread-safe)."""
        with self._lock:
            return [
                name
                for name, state in self.task_states.items()
                if state.status == "completed"
            ]

    def get_previous_session_id(self, current_task_name: str) -> str | None:
        """Get the Claude session ID from the most recent task execution before the current one."""
        # If no history, return None
        if not self.results_history:
            return None

        # Find the most recent entry with a claude_session_id
        # (regardless of success status since user might want to continue from a "failed" attempt)
        for entry in reversed(self.results_history):
            claude_session_id = entry.get("claude_session_id")
            if claude_session_id and entry.get("task_name") != current_task_name:
                # This is a different task with a session ID, return it
                self.logger.debug(
                    f"Found previous session from task '{entry.get('task_name')}': {claude_session_id}"
                )
                return str(claude_session_id)

        # No previous session found
        self.logger.debug(f"No previous session found for task '{current_task_name}'")
        return None
