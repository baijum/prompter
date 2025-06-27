"""Progress visualization for parallel task execution using rich."""

import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .logging import get_logger
from .parallel_coordinator import TaskStatus


@dataclass
class TaskProgress:
    """Track progress information for a single task."""

    name: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    start_time: float | None = None
    end_time: float | None = None
    error: str | None = None
    dependencies: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float | None:
        """Get task duration in seconds."""
        if self.start_time:
            end = self.end_time or time.time()
            return end - self.start_time
        return None

    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        duration = self.duration
        if duration is None:
            return "--:--"

        minutes, seconds = divmod(int(duration), 60)
        return f"{minutes:02d}:{seconds:02d}"


class ProgressDisplayMode(Enum):
    """Display modes for progress visualization."""

    RICH = "rich"  # Full rich terminal UI
    SIMPLE = "simple"  # Simple progress bars
    NONE = "none"  # No progress display


class ProgressDisplay:
    """Rich terminal display for parallel task execution progress."""

    def __init__(
        self,
        total_tasks: int,
        max_parallel: int,
        workflow_name: str = "Workflow",
        mode: ProgressDisplayMode = ProgressDisplayMode.RICH,
    ) -> None:
        self.total_tasks = total_tasks
        self.max_parallel = max_parallel
        self.workflow_name = workflow_name
        self.mode = mode
        self.logger = get_logger("progress")

        # Task tracking
        self.task_progress: dict[str, TaskProgress] = {}
        self._lock = threading.Lock()
        self.start_time = time.time()

        # Rich components
        self.console = Console()
        self.live: Live | None = None

        # Check and adjust display mode based on terminal capabilities
        self._adjust_display_mode()

    def _adjust_display_mode(self) -> None:
        """Adjust display mode based on environment and terminal capabilities."""
        # Check for forced mode via environment variable
        force_mode = os.environ.get("PROMPTER_PROGRESS_MODE", "").lower()
        if force_mode == "rich":
            self.logger.debug("Rich display forced via PROMPTER_PROGRESS_MODE=rich")
            self.mode = ProgressDisplayMode.RICH
            return
        if force_mode == "simple":
            self.logger.debug("Simple display forced via PROMPTER_PROGRESS_MODE=simple")
            self.mode = ProgressDisplayMode.SIMPLE
            return
        if force_mode == "none":
            self.logger.debug("No display forced via PROMPTER_PROGRESS_MODE=none")
            self.mode = ProgressDisplayMode.NONE
            return

        # If mode is RICH, check if terminal supports it
        if self.mode == ProgressDisplayMode.RICH and not self._supports_rich_display():
            self.mode = ProgressDisplayMode.SIMPLE
            self.logger.info("Terminal doesn't support rich display, using simple mode")

    def _supports_rich_display(self) -> bool:
        """Check if the terminal supports rich display."""
        # Disable in CI environments (comprehensive list)
        ci_env_vars = [
            "CI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "CIRCLECI",
            "TRAVIS",
            "JENKINS_URL",
            "TEAMCITY_VERSION",
            "BUILDKITE",
            "DRONE",
            "CODEBUILD_BUILD_ID",
            "APPVEYOR",
            "TF_BUILD",
            "BITBUCKET_PIPELINES_UUID",
            "BUDDY_WORKSPACE_ID",
        ]
        if any(os.environ.get(var) for var in ci_env_vars):
            self.logger.debug("CI environment detected, disabling rich display")
            return False

        # Check if stdout is a terminal
        if not sys.stdout.isatty():
            self.logger.debug("stdout is not a TTY, disabling rich display")
            return False

        # Check terminal type
        term = os.environ.get("TERM", "").lower()
        if term in ["dumb", "unknown", ""]:
            self.logger.debug(f"Unsupported terminal type: {term}")
            return False

        # Check for Windows terminal compatibility
        if sys.platform == "win32":
            # Check if we're in Windows Terminal or modern console
            if os.environ.get("WT_SESSION") or os.environ.get("TERMINAL_EMULATOR"):
                self.logger.debug("Modern Windows terminal detected")
                return True
            # Legacy Windows console might not support rich
            try:
                import colorama

                colorama.init()
                self.logger.debug("Windows console with colorama support")
                return True
            except ImportError:
                self.logger.debug("Legacy Windows console without colorama")
                return False

        # Check for specific terminal emulators that might have issues
        term_program = os.environ.get("TERM_PROGRAM", "").lower()
        if term_program in ["mintty"]:  # Some terminals have known issues
            self.logger.debug(
                f"Terminal program {term_program} may have limited support"
            )

        self.logger.debug("Terminal supports rich display")
        return True

    def start(self) -> None:
        """Start the progress display."""
        if self.mode == ProgressDisplayMode.RICH:
            self.live = Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=4,
                transient=False,
            )
            self.live.start()
        elif self.mode == ProgressDisplayMode.SIMPLE:
            print(f"\nStarting {self.workflow_name} with {self.total_tasks} tasks...\n")

    def stop(self) -> None:
        """Stop the progress display."""
        if self.live:
            self.live.stop()
            self.live = None
        elif self.mode == ProgressDisplayMode.SIMPLE:
            # Print final summary for simple mode
            self._print_simple_summary()

    def update_task(
        self,
        task_name: str,
        status: TaskStatus,
        progress: float = 0.0,
        message: str = "",
        error: str | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """Update task progress information."""
        with self._lock:
            if task_name not in self.task_progress:
                self.task_progress[task_name] = TaskProgress(
                    name=task_name, status=status, dependencies=dependencies or []
                )

            task = self.task_progress[task_name]
            task.status = status
            task.progress = progress
            task.message = message

            if error:
                task.error = error

            # Track timing
            if status == TaskStatus.RUNNING and task.start_time is None:
                task.start_time = time.time()
            elif (
                status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                and task.end_time is None
            ):
                task.end_time = time.time()

        # Update display
        if self.mode == ProgressDisplayMode.RICH and self.live:
            self.live.update(self._create_layout())
        elif self.mode == ProgressDisplayMode.SIMPLE:
            self._print_simple_update(task_name, status, progress, message)

    def _create_layout(self) -> Layout:
        """Create the main layout for rich display."""
        layout = Layout()

        # Create main sections
        layout.split_column(
            Layout(self._create_header(), size=4),
            Layout(self._create_active_tasks(), size=10),
            Layout(self._create_waiting_tasks(), size=6),
            Layout(self._create_summary(), size=3),
        )

        return layout

    def _create_header(self) -> Panel:
        """Create header panel with workflow info."""
        elapsed = time.time() - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))

        # Count tasks by status
        with self._lock:
            running = sum(
                1 for t in self.task_progress.values() if t.status == TaskStatus.RUNNING
            )
            completed = sum(
                1
                for t in self.task_progress.values()
                if t.status == TaskStatus.COMPLETED
            )
            failed = sum(
                1 for t in self.task_progress.values() if t.status == TaskStatus.FAILED
            )

        header_text = Text()
        header_text.append("Workflow: ", style="bold")
        header_text.append(self.workflow_name, style="cyan")
        header_text.append(f"\nTotal Tasks: {self.total_tasks} | ")
        header_text.append(f"Running: {running}/{self.max_parallel} | ", style="blue")
        header_text.append(f"Completed: {completed} | ", style="green")
        if failed > 0:
            header_text.append(f"Failed: {failed} | ", style="red")
        header_text.append(f"Elapsed: {elapsed_str}")

        return Panel(
            header_text, title="🚀 Parallel Task Execution", border_style="blue"
        )

    def _create_active_tasks(self) -> Panel:
        """Create panel showing active tasks."""
        table = Table(title="Active Tasks", show_header=True, header_style="bold")
        table.add_column("Task", style="cyan", width=30)
        table.add_column("Status", width=15)
        table.add_column("Progress", width=30)
        table.add_column("Duration", width=10)

        with self._lock:
            # Show running tasks first
            running_tasks = [
                (name, task)
                for name, task in self.task_progress.items()
                if task.status == TaskStatus.RUNNING
            ]

            for name, task in running_tasks:
                status_style = "blue"
                status_text = "Running"

                # Create progress bar
                if task.progress > 0:
                    filled = int(task.progress * 20)
                    empty = 20 - filled
                    progress_bar = f"[{'█' * filled}{'░' * empty}] {task.progress:.0%}"
                else:
                    progress_bar = (
                        f"[░░░░░░░░░░░░░░░░░░░░] {task.message or 'Starting...'}"
                    )

                table.add_row(
                    name,
                    Text(status_text, style=status_style),
                    progress_bar,
                    task.duration_str,
                )

            # Show recently completed/failed tasks
            recent_tasks = [
                (name, task)
                for name, task in self.task_progress.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            ]
            recent_tasks.sort(key=lambda x: x[1].end_time or 0, reverse=True)

            for name, task in recent_tasks[:5]:  # Show last 5
                if task.status == TaskStatus.COMPLETED:
                    status_style = "green"
                    status_text = "✓ Complete"
                    progress_bar = "[████████████████████] 100%"
                else:
                    status_style = "red"
                    status_text = "✗ Failed"
                    progress_bar = f"[████████████████████] {task.error or 'Error'}"

                table.add_row(
                    name,
                    Text(status_text, style=status_style),
                    Text(progress_bar, style=status_style),
                    task.duration_str,
                )

        return Panel(table, border_style="green")

    def _create_waiting_tasks(self) -> Panel:
        """Create panel showing waiting tasks."""
        content = Text()

        with self._lock:
            waiting_tasks = [
                (name, task)
                for name, task in self.task_progress.items()
                if task.status in (TaskStatus.PENDING, TaskStatus.READY)
            ]

            if waiting_tasks:
                for name, task in waiting_tasks[:10]:  # Show up to 10
                    content.append(f"• {name}", style="yellow")
                    if task.dependencies:
                        deps_str = ", ".join(task.dependencies)
                        content.append(f" → waiting for: {deps_str}", style="dim")
                    content.append("\n")

                if len(waiting_tasks) > 10:
                    content.append(
                        f"... and {len(waiting_tasks) - 10} more", style="dim"
                    )
            else:
                content.append("No tasks waiting", style="dim")

        return Panel(content, title="⏳ Waiting Tasks", border_style="yellow")

    def _create_summary(self) -> Panel:
        """Create summary panel with overall progress."""
        with self._lock:
            completed = sum(
                1
                for t in self.task_progress.values()
                if t.status == TaskStatus.COMPLETED
            )
            failed = sum(
                1 for t in self.task_progress.values() if t.status == TaskStatus.FAILED
            )

            # Overall progress
            done_tasks = completed + failed
            progress = done_tasks / self.total_tasks if self.total_tasks > 0 else 0

            # Create progress bar
            bar_width = 40
            filled = int(progress * bar_width)
            empty = bar_width - filled
            progress_bar = f"[{'█' * filled}{'░' * empty}] {progress:.0%}"

            # ETA calculation (simple estimate)
            if done_tasks > 0 and progress < 1.0:
                elapsed = time.time() - self.start_time
                rate = done_tasks / elapsed
                remaining = self.total_tasks - done_tasks
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_str = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta_str = "--:--"

        summary = Text()
        summary.append("Overall Progress: ", style="bold")
        summary.append(progress_bar, style="cyan")
        if progress < 1.0:
            summary.append(f" | ETA: {eta_str}", style="dim")

        return Panel(summary, border_style="magenta")

    def _print_simple_update(
        self, task_name: str, status: TaskStatus, progress: float, message: str
    ) -> None:
        """Print simple progress update for non-rich terminals."""
        # Use ASCII symbols for better compatibility
        status_symbols = {
            TaskStatus.PENDING: "[.]",
            TaskStatus.READY: "[~]",
            TaskStatus.RUNNING: "[>]",
            TaskStatus.COMPLETED: "[+]",
            TaskStatus.FAILED: "[x]",
            TaskStatus.SKIPPED: "[-]",
        }

        symbol = status_symbols.get(status, "[?]")
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")

        if status == TaskStatus.RUNNING:
            if progress > 0:
                # Show a simple progress bar
                bar_width = 20
                filled = int(progress * bar_width)
                empty = bar_width - filled
                progress_bar = f"[{'#' * filled}{'-' * empty}]"
                print(
                    f"{timestamp} {symbol} {task_name}: {progress_bar} {progress:.0%} - {message}"
                )
            else:
                print(f"{timestamp} {symbol} {task_name}: {message or 'Starting...'}")
        elif status == TaskStatus.COMPLETED:
            task = self.task_progress.get(task_name)
            duration = f" ({task.duration_str})" if task and task.duration else ""
            print(f"{timestamp} {symbol} {task_name}: Completed{duration}")
        elif status == TaskStatus.FAILED:
            task = self.task_progress.get(task_name)
            error_msg = f" - {task.error[:50]}..." if task and task.error else ""
            print(f"{timestamp} {symbol} {task_name}: Failed{error_msg}")
        elif status == TaskStatus.READY:
            print(f"{timestamp} {symbol} {task_name}: Ready (dependencies satisfied)")
        elif status == TaskStatus.PENDING:
            task = self.task_progress.get(task_name)
            if task and task.dependencies:
                deps = ", ".join(task.dependencies[:3])
                if len(task.dependencies) > 3:
                    deps += f" +{len(task.dependencies) - 3} more"
                print(f"{timestamp} {symbol} {task_name}: Waiting for {deps}")

    def _print_simple_summary(self) -> None:
        """Print final summary for simple mode."""
        with self._lock:
            completed = sum(
                1
                for t in self.task_progress.values()
                if t.status == TaskStatus.COMPLETED
            )
            failed = sum(
                1 for t in self.task_progress.values() if t.status == TaskStatus.FAILED
            )
            skipped = sum(
                1 for t in self.task_progress.values() if t.status == TaskStatus.SKIPPED
            )

            elapsed = time.time() - self.start_time
            elapsed_str = str(timedelta(seconds=int(elapsed)))

            print(f"\n{'=' * 60}")
            print(f"Workflow Summary: {self.workflow_name}")
            print(f"{'=' * 60}")
            print(f"Total tasks:     {self.total_tasks}")
            print(
                f"Completed:       {completed} ({completed / self.total_tasks * 100:.1f}%)"
            )
            if failed > 0:
                print(
                    f"Failed:          {failed} ({failed / self.total_tasks * 100:.1f}%)"
                )
            if skipped > 0:
                print(f"Skipped:         {skipped}")
            print(f"Execution time:  {elapsed_str}")
            print(f"{'=' * 60}")

            # List failed tasks if any
            if failed > 0:
                print("\nFailed tasks:")
                for name, task in self.task_progress.items():
                    if task.status == TaskStatus.FAILED:
                        error = task.error[:60] if task.error else "Unknown error"
                        print(f"  - {name}: {error}")

    def __enter__(self) -> "ProgressDisplay":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.stop()
