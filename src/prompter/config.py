"""Configuration parser for prompter TOML files."""

import tomllib
from pathlib import Path
from typing import Any

from .constants import DEFAULT_CHECK_INTERVAL
from .logging import get_logger

# Reserved action words that cannot be used as task names
RESERVED_ACTIONS = {"next", "stop", "retry", "repeat"}
ON_SUCCESS_ACTIONS = {"next", "stop", "repeat"}
ON_FAILURE_ACTIONS = {"retry", "stop", "next"}


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
        self.resume_previous_session: bool = config.get(
            "resume_previous_session", False
        )
        self.system_prompt: str | None = config.get("system_prompt")

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
        self.check_interval: int = settings.get(
            "check_interval", DEFAULT_CHECK_INTERVAL
        )
        self.max_retries: int = settings.get("max_retries", 3)
        self.working_directory: str | None = settings.get("working_directory")
        self.allow_infinite_loops: bool = settings.get("allow_infinite_loops", False)

        self.logger.debug(
            f"Configuration settings: check_interval={self.check_interval}s, "
            f"max_retries={self.max_retries}, working_directory={self.working_directory}, "
            f"allow_infinite_loops={self.allow_infinite_loops}"
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
        except tomllib.TOMLDecodeError as e:
            # Extract line and column information from the error message
            error_msg = str(e)
            line_num = None
            col_num = None

            # Parse error message for line and column
            import re

            match = re.search(r"at line (\d+), column (\d+)", error_msg)
            if match:
                line_num = int(match.group(1))
                col_num = int(match.group(2))

            # Read the problematic line if possible
            context_lines = []
            try:
                with open(self.config_path) as f:
                    lines = f.readlines()
                    if line_num and 0 < line_num <= len(lines):
                        # Show 2 lines before and after for context
                        start = max(0, line_num - 3)
                        end = min(len(lines), line_num + 2)

                        for i in range(start, end):
                            line = lines[i].rstrip()
                            if i + 1 == line_num:
                                # Highlight the problematic line
                                context_lines.append(f">>> {i + 1:4d} | {line}")
                                if col_num:
                                    # Add pointer to specific column
                                    pointer = " " * (col_num + 6) + "^"
                                    context_lines.append(pointer)
                            else:
                                context_lines.append(f"    {i + 1:4d} | {line}")
            except Exception:
                # It's okay to fail here - we're just trying to provide better context
                pass

            # Create enhanced error message
            enhanced_msg = f"TOML parsing error in {self.config_path}:\n{error_msg}"

            if context_lines:
                enhanced_msg += "\n\nContext:\n" + "\n".join(context_lines)

            # Add helpful hints based on the error type
            if "Unescaped '\\'" in error_msg:
                enhanced_msg += "\n\nHint: In TOML strings, backslashes must be escaped. Use '\\\\' for a literal backslash."
                enhanced_msg += "\nFor file paths, consider using single quotes (') or raw strings (''') to avoid escaping."
                enhanced_msg += "\nExample: path = 'C:\\Users\\name' or path = '''C:\\Users\\name'''"

            # Don't log here - the exception will be displayed by the CLI
            raise tomllib.TOMLDecodeError(enhanced_msg) from e

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

        # Get all task names for validation
        task_names = {task.name for task in self.tasks if task.name}

        for i, task in enumerate(self.tasks):
            task_errors = []
            if not task.name:
                task_errors.append(f"Task {i}: name is required")
            elif task.name in RESERVED_ACTIONS:
                task_errors.append(
                    f"Task {i}: name '{task.name}' is a reserved word and cannot be used as a task name. "
                    f"Reserved words are: {', '.join(sorted(RESERVED_ACTIONS))}"
                )

            if not task.prompt:
                task_errors.append(f"Task {i} ({task.name}): prompt is required")
            if not task.verify_command:
                task_errors.append(
                    f"Task {i} ({task.name}): verify_command is required"
                )

            # Validate on_success - can be either a reserved action or a task name
            if (
                task.on_success not in ON_SUCCESS_ACTIONS
                and task.on_success not in task_names
            ):
                task_errors.append(
                    f"Task {i} ({task.name}): on_success '{task.on_success}' must be one of "
                    f"{', '.join(sorted(ON_SUCCESS_ACTIONS))} or a valid task name"
                )

            # Validate on_failure - can be either a reserved action or a task name
            if (
                task.on_failure not in ON_FAILURE_ACTIONS
                and task.on_failure not in task_names
            ):
                task_errors.append(
                    f"Task {i} ({task.name}): on_failure '{task.on_failure}' must be one of "
                    f"{', '.join(sorted(ON_FAILURE_ACTIONS))} or a valid task name"
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
