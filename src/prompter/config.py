"""Configuration parser for prompter TOML files."""

import tomllib
from pathlib import Path
from typing import Any


class TaskConfig:
    """Configuration for a single task."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.name: str = config.get("name", "")
        self.prompt: str = config.get("prompt", "")
        self.verify_command: str = config.get("verify_command", "")
        self.verify_success_code: int = config.get("verify_success_code", 0)
        self.on_success: str = config.get("on_success", "next")
        self.on_failure: str = config.get("on_failure", "retry")
        self.max_attempts: int = config.get("max_attempts", 3)
        self.timeout: int | None = config.get("timeout")

    def __repr__(self) -> str:
        return f"TaskConfig(name='{self.name}')"


class PrompterConfig:
    """Main configuration for the prompter tool."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self._config = self._load_config()

        # Parse settings
        settings = self._config.get("settings", {})
        self.check_interval: int = settings.get("check_interval", 3600)
        self.max_retries: int = settings.get("max_retries", 3)
        # Note: claude_command is deprecated when using SDK but kept for backward compatibility
        self.claude_command: str = settings.get("claude_command", "claude")
        self.working_directory: str | None = settings.get("working_directory")

        # Parse tasks
        self.tasks: list[TaskConfig] = []
        for task_config in self._config.get("tasks", []):
            self.tasks.append(TaskConfig(task_config))

    def _load_config(self) -> dict[str, Any]:
        """Load and parse the TOML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "rb") as f:
            return tomllib.load(f)

    def get_task_by_name(self, name: str) -> TaskConfig | None:
        """Get a task configuration by name."""
        for task in self.tasks:
            if task.name == name:
                return task
        return None

    def validate(self) -> list[str]:
        """Validate the configuration and return any errors."""
        errors = []

        if not self.tasks:
            errors.append("No tasks defined in configuration")

        for i, task in enumerate(self.tasks):
            if not task.name:
                errors.append(f"Task {i}: name is required")
            if not task.prompt:
                errors.append(f"Task {i} ({task.name}): prompt is required")
            if not task.verify_command:
                errors.append(f"Task {i} ({task.name}): verify_command is required")
            if task.on_success not in ["next", "stop", "repeat"]:
                errors.append(
                    f"Task {i} ({task.name}): on_success must be 'next', 'stop', or 'repeat'"
                )
            if task.on_failure not in ["retry", "stop", "next"]:
                errors.append(
                    f"Task {i} ({task.name}): on_failure must be 'retry', 'stop', or 'next'"
                )
            if task.max_attempts < 1:
                errors.append(f"Task {i} ({task.name}): max_attempts must be >= 1")

        return errors
