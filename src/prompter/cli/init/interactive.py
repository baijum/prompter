"""Interactive configuration customization."""

from dataclasses import dataclass
from typing import Any

from prompter.constants import DEFAULT_TASK_TIMEOUT
from prompter.utils.console import Console

from .analyzer import AnalysisResult


@dataclass
class TaskConfig:
    """Configuration for a single task."""

    name: str
    prompt: str
    verify_command: str
    timeout: int = DEFAULT_TASK_TIMEOUT
    on_success: str = "next"
    on_failure: str = "retry"
    max_attempts: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        return {
            "name": self.name,
            "prompt": self.prompt,
            "verify_command": self.verify_command,
            "timeout": self.timeout,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "max_attempts": self.max_attempts,
        }


class InteractiveConfigurator:
    """Handles interactive configuration customization."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def customize(
        self, config: dict[str, Any], analysis: AnalysisResult
    ) -> dict[str, Any]:
        """Customize configuration based on AI analysis."""
        # Confirm detected tools
        self.console.print_section("Detected Tools:")
        config = self._confirm_tools(config, analysis)

        # Customize tasks
        self.console.print_section("\nProposed Tasks:")
        config["tasks"] = self._customize_tasks(config.get("tasks", []))

        # Add custom tasks
        config["tasks"].extend(self._add_custom_tasks())

        # Global settings
        config["settings"] = self._customize_settings(config.get("settings", {}))

        return config

    def customize_template(
        self, config: dict[str, Any], patterns: list[str]
    ) -> dict[str, Any]:
        """Customize template-based configuration."""
        self.console.print_section("Template Customization")

        # Show what was detected
        self.console.print_info("\nDetected patterns:")
        for pattern in patterns:
            self.console.print_info(f"  • {pattern}")

        # Customize each task in template
        self.console.print_section("\nCustomizing template tasks:")
        config["tasks"] = self._customize_tasks(config.get("tasks", []))

        # Offer to add more tasks
        config["tasks"].extend(self._add_custom_tasks())

        return config

    def _confirm_tools(
        self, config: dict[str, Any], analysis: AnalysisResult
    ) -> dict[str, Any]:
        """Confirm or modify detected tools."""
        tool_mappings = [
            ("Build", analysis.build_system, analysis.build_command, "build_command"),
            ("Tests", analysis.test_framework, analysis.test_command, "test_command"),
            ("Linter", analysis.linter, analysis.lint_command, "lint_command"),
            (
                "Formatter",
                analysis.formatter,
                analysis.format_command,
                "format_command",
            ),
            ("Docs", analysis.documentation_tool, analysis.doc_command, "doc_command"),
        ]

        confirmed_tools = {}

        for tool_type, tool_name, command, key in tool_mappings:
            if tool_name:
                self.console.print_info(f"\n{tool_type}: {tool_name}")
                if command:
                    self.console.print_info(f"  Command: {command}")

                confirm = self.console.get_input("  ✓ Accept this? [Y/n]: ").lower()

                if confirm == "n":
                    custom_cmd = self.console.get_input(
                        f"  Enter {tool_type.lower()} command: "
                    )
                    if custom_cmd:
                        confirmed_tools[key] = custom_cmd
                elif command:
                    confirmed_tools[key] = command

        # Update config with confirmed tools
        if "tools" not in config:
            config["tools"] = {}
        config["tools"].update(confirmed_tools)

        return config

    def _customize_tasks(self, tasks: list[dict[str, Any]]) -> list[TaskConfig]:
        """Customize individual tasks."""
        customized_tasks = []

        for i, task in enumerate(tasks, 1):
            self.console.print_subsection(f"\n{i}. {task['name']}")
            self.console.print_info(f"   Prompt: {task['prompt'][:80]}...")
            self.console.print_info(f"   Verify: {task['verify_command']}")
            self.console.print_info(
                f"   Timeout: {task.get('timeout', DEFAULT_TASK_TIMEOUT)}s"
            )

            action = self.console.get_input(
                "   Action [keep/edit/delete/skip]: "
            ).lower()

            if action in {"keep", ""}:
                customized_tasks.append(TaskConfig(**task))
            elif action == "edit":
                customized_tasks.append(self._edit_task(task))
            elif action == "skip":
                continue
            # 'delete' results in task not being added

        return customized_tasks

    def _edit_task(self, task: dict[str, Any]) -> TaskConfig:
        """Edit a single task."""
        self.console.print_info(
            "\n   Editing task (press ENTER to keep current value):"
        )

        name = self.console.get_input(f"   Name [{task['name']}]: ") or task["name"]

        self.console.print_info(f"   Current prompt: {task['prompt']}")
        new_prompt = self.console.get_input("   New prompt (or ENTER to keep): ")
        prompt = new_prompt if new_prompt else task["prompt"]

        verify = (
            self.console.get_input(f"   Verify command [{task['verify_command']}]: ")
            or task["verify_command"]
        )

        timeout_str = self.console.get_input(
            f"   Timeout in seconds [{task.get('timeout', DEFAULT_TASK_TIMEOUT)}]: "
        )
        timeout = (
            int(timeout_str)
            if timeout_str
            else task.get("timeout", DEFAULT_TASK_TIMEOUT)
        )

        on_success = self.console.get_input(
            f"   On success [next/stop/repeat] [{task.get('on_success', 'next')}]: "
        ) or task.get("on_success", "next")

        on_failure = self.console.get_input(
            f"   On failure [retry/next/stop] [{task.get('on_failure', 'retry')}]: "
        ) or task.get("on_failure", "retry")

        max_attempts_str = self.console.get_input(
            f"   Max attempts [{task.get('max_attempts', 3)}]: "
        )
        max_attempts = (
            int(max_attempts_str) if max_attempts_str else task.get("max_attempts", 3)
        )

        return TaskConfig(
            name=name,
            prompt=prompt,
            verify_command=verify,
            timeout=timeout,
            on_success=on_success,
            on_failure=on_failure,
            max_attempts=max_attempts,
        )

    def _add_custom_tasks(self) -> list[TaskConfig]:
        """Add custom tasks interactively."""
        custom_tasks = []

        while True:
            add_more = self.console.get_input("\nAdd a custom task? [y/N]: ").lower()
            if add_more != "y":
                break

            self.console.print_subsection("Creating custom task:")

            name = self.console.get_input("  Task name: ")
            if not name:
                self.console.print_warning("  Task name is required!")
                continue

            prompt = self.console.get_input("  Task prompt: ")
            if not prompt:
                self.console.print_warning("  Task prompt is required!")
                continue

            verify = self.console.get_input("  Verify command: ")
            if not verify:
                self.console.print_warning("  Verify command is required!")
                continue

            # Optional fields with defaults
            timeout_str = self.console.get_input(
                f"  Timeout in seconds [{DEFAULT_TASK_TIMEOUT}]: "
            )
            timeout = int(timeout_str) if timeout_str else DEFAULT_TASK_TIMEOUT

            on_success = (
                self.console.get_input("  On success [next/stop/repeat] [next]: ")
                or "next"
            )
            on_failure = (
                self.console.get_input("  On failure [retry/next/stop] [retry]: ")
                or "retry"
            )

            max_attempts_str = self.console.get_input("  Max attempts [3]: ")
            max_attempts = int(max_attempts_str) if max_attempts_str else 3

            custom_tasks.append(
                TaskConfig(
                    name=name,
                    prompt=prompt,
                    verify_command=verify,
                    timeout=timeout,
                    on_success=on_success,
                    on_failure=on_failure,
                    max_attempts=max_attempts,
                )
            )

            self.console.print_success("  ✓ Task added!")

        return custom_tasks

    def _customize_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Customize global settings."""
        self.console.print_section("\nGlobal Settings:")

        # Working directory
        current_wd = settings.get("working_directory", ".")
        wd = self.console.get_input(f"Working directory [{current_wd}]: ") or current_wd
        settings["working_directory"] = wd

        # Check interval
        current_interval = settings.get("check_interval", 30)
        interval_str = self.console.get_input(
            f"Check interval in seconds [{current_interval}]: "
        )
        settings["check_interval"] = (
            int(interval_str) if interval_str else current_interval
        )

        # Allow infinite loops
        allow_loops = (
            self.console.get_input("Allow infinite loops? [y/N]: ").lower() == "y"
        )
        if allow_loops:
            settings["allow_infinite_loops"] = True

        return settings
