"""State management for tracking task progress and persistence."""

import json
import time
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
    ) -> None:
        self.name = name
        self.status = status  # pending, running, completed, failed
        self.attempts = attempts
        self.last_attempt = last_attempt
        self.last_success = last_success
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "attempts": self.attempts,
            "last_attempt": self.last_attempt,
            "last_success": self.last_success,
            "error_message": self.error_message,
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
        )


class StateManager:
    """Manages persistent state for task execution."""

    def __init__(self, state_file: Path | None = None) -> None:
        self.state_file = state_file or Path(".prompter_state.json")
        self.session_id = str(int(time.time()))
        self.start_time = time.time()
        self.task_states: dict[str, TaskState] = {}
        self.results_history: list[dict[str, Any]] = []
        self.logger = get_logger("state")

        # Load existing state if available
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)

                # Load task states
                for task_data in data.get("task_states", []):
                    state = TaskState.from_dict(task_data)
                    self.task_states[state.name] = state

                # Load results history
                self.results_history = data.get("results_history", [])

            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Could not load state file: {e}")

    def save_state(self) -> None:
        """Save current state to file."""
        data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "last_update": time.time(),
            "task_states": [state.to_dict() for state in self.task_states.values()],
            "results_history": self.results_history,
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            self.logger.warning(f"Could not save state file: {e}")

    def get_task_state(self, task_name: str) -> TaskState:
        """Get state for a task, creating if it doesn't exist."""
        if task_name not in self.task_states:
            self.task_states[task_name] = TaskState(task_name)
        return self.task_states[task_name]

    def update_task_state(self, result: TaskResult) -> None:
        """Update task state based on execution result."""
        state = self.get_task_state(result.task_name)

        state.attempts = result.attempts
        state.last_attempt = result.timestamp

        if result.success:
            state.status = "completed"
            state.last_success = result.timestamp
            state.error_message = ""
        else:
            state.status = "failed"
            state.error_message = result.error

        # Add to results history
        self.results_history.append(
            {
                "session_id": self.session_id,
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

        # Save state after each update
        self.save_state()

    def mark_task_running(self, task_name: str) -> None:
        """Mark a task as currently running."""
        state = self.get_task_state(task_name)
        state.status = "running"
        self.save_state()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current state."""
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
        """Clear all state (useful for fresh starts)."""
        self.task_states.clear()
        self.results_history.clear()
        if self.state_file.exists():
            self.state_file.unlink()

    def get_failed_tasks(self) -> list[str]:
        """Get list of task names that have failed."""
        return [
            name for name, state in self.task_states.items() if state.status == "failed"
        ]

    def get_completed_tasks(self) -> list[str]:
        """Get list of task names that have completed successfully."""
        return [
            name
            for name, state in self.task_states.items()
            if state.status == "completed"
        ]
