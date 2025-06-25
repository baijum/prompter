"""Configuration parser for prompter TOML files."""

import tomllib
from pathlib import Path
from typing import Any

from .logging import get_logger


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
        self.logger = get_logger("config")
        self.logger.debug(f"Loading configuration from {self.config_path}")
        self._config = self._load_config()

        # Parse settings
        settings = self._config.get("settings", {})
        self.check_interval: int = settings.get("check_interval", 3600)
        self.max_retries: int = settings.get("max_retries", 3)
        self.working_directory: str | None = settings.get("working_directory")

        self.logger.debug(
            f"Configuration settings: check_interval={self.check_interval}s, "
            f"max_retries={self.max_retries}, working_directory={self.working_directory}"
        )

        # Parse tasks
        self.tasks: list[TaskConfig] = []
        for i, task_config in enumerate(self._config.get("tasks", [])):
            self.logger.debug(
                f"Parsing task {i + 1}: {task_config.get('name', 'unnamed')}"
            )
            self.tasks.append(TaskConfig(task_config))

        self.logger.debug(f"Loaded {len(self.tasks)} tasks from configuration")

    def _load_config(self) -> dict[str, Any]:
        """Load and parse the TOML configuration file."""
        if not self.config_path.exists():
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, "rb") as f:
                config = tomllib.load(f)
                self.logger.debug(
                    f"Successfully parsed TOML file with {len(config)} top-level sections"
                )
                return config
        except tomllib.TOMLDecodeError:
            self.logger.exception("Failed to parse TOML file")
            raise

    def get_task_by_name(self, name: str) -> TaskConfig | None:
        """Get a task configuration by name."""
        self.logger.debug(f"Looking for task named '{name}'")
        for task in self.tasks:
            if task.name == name:
                self.logger.debug(f"Found task '{name}'")
                return task
        self.logger.debug(f"Task '{name}' not found")
        return None

    def validate(self) -> list[str]:
        """Validate the configuration and return any errors."""
        self.logger.debug("Validating configuration")
        errors = []

        if not self.tasks:
            errors.append("No tasks defined in configuration")
            self.logger.debug("Validation error: No tasks defined")

        for i, task in enumerate(self.tasks):
            task_errors = []
            if not task.name:
                task_errors.append(f"Task {i}: name is required")
            if not task.prompt:
                task_errors.append(f"Task {i} ({task.name}): prompt is required")
            if not task.verify_command:
                task_errors.append(
                    f"Task {i} ({task.name}): verify_command is required"
                )
            if task.on_success not in ["next", "stop", "repeat"]:
                task_errors.append(
                    f"Task {i} ({task.name}): on_success must be 'next', 'stop', or 'repeat'"
                )
            if task.on_failure not in ["retry", "stop", "next"]:
                task_errors.append(
                    f"Task {i} ({task.name}): on_failure must be 'retry', 'stop', or 'next'"
                )
            if task.max_attempts < 1:
                task_errors.append(f"Task {i} ({task.name}): max_attempts must be >= 1")

            if task_errors:
                self.logger.debug(
                    f"Validation errors for task {i} ({task.name}): {len(task_errors)} errors"
                )
                errors.extend(task_errors)
            else:
                self.logger.debug(f"Task {i} ({task.name}) validation passed")

        self.logger.debug(
            f"Configuration validation complete: {len(errors)} errors found"
        )
        return errors
