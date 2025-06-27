"""Parallel task coordination for executing tasks with dependencies.

This module implements concurrent task execution using anyio for structured concurrency,
respecting task dependencies and resource constraints.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import anyio
from anyio import create_task_group
from anyio.abc import TaskGroup

from .config import PrompterConfig, TaskConfig
from .logging import get_logger
from .runner import TaskResult, TaskRunner
from .state import StateManager


class TaskStatus(Enum):
    """Status of a task in the parallel execution system."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskExecutionState:
    """Tracks the execution state of a task."""

    name: str
    status: TaskStatus = TaskStatus.PENDING
    result: TaskResult | None = None
    start_time: float | None = None
    end_time: float | None = None
    dependencies_met: bool = False

    @property
    def duration(self) -> float | None:
        """Get task execution duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class ResourcePool:
    """Manages available system resources for task scheduling."""

    max_parallel_tasks: int
    running_tasks: set[str] = field(default_factory=set)
    completed_tasks: set[str] = field(default_factory=set)
    failed_tasks: set[str] = field(default_factory=set)
    exclusive_task_running: str | None = None

    # Future: Track CPU, memory, API rate limits
    available_cpu: float = field(default_factory=lambda: 100.0)
    available_memory: int = field(default_factory=lambda: 8192)  # MB

    def can_schedule(self, task: TaskConfig) -> bool:
        """Check if a task can be scheduled given resource constraints."""
        # Check parallel task limit
        if len(self.running_tasks) >= self.max_parallel_tasks:
            return False

        # If an exclusive task is running, nothing else can be scheduled
        if self.exclusive_task_running:
            return False

        # If this is an exclusive task, it can only run if nothing else is running
        return not (task.exclusive and len(self.running_tasks) > 0)

    def allocate(self, task: TaskConfig) -> None:
        """Allocate resources for a task."""
        self.running_tasks.add(task.name)
        if task.exclusive:
            self.exclusive_task_running = task.name
        # Future: Deduct CPU and memory

    def release(self, task: TaskConfig, success: bool) -> None:
        """Release resources after task completion."""
        self.running_tasks.discard(task.name)
        if task.name == self.exclusive_task_running:
            self.exclusive_task_running = None
        if success:
            self.completed_tasks.add(task.name)
        else:
            self.failed_tasks.add(task.name)
        # Future: Return CPU and memory


class ParallelTaskCoordinator:
    """Coordinates parallel execution of tasks with dependency management."""

    def __init__(
        self,
        config: PrompterConfig,
        runner: TaskRunner,
        state_manager: StateManager,
        dry_run: bool = False,
        progress_display: Any | None = None,
    ) -> None:
        self.config = config
        self.runner = runner
        self.state_manager = state_manager
        self.dry_run = dry_run
        self.progress_display = progress_display
        self.logger = get_logger("parallel_coordinator")

        # Build task graph
        self.graph = config.build_task_graph()

        # Initialize execution state
        self.task_states: dict[str, TaskExecutionState] = {}
        for task in config.tasks:
            self.task_states[task.name] = TaskExecutionState(name=task.name)

        # Resource management
        self.resource_pool = ResourcePool(max_parallel_tasks=config.max_parallel_tasks)

        # Synchronization primitives
        self._task_completed_event = anyio.Event()
        self._shutdown_requested = False

    async def execute_all(self) -> dict[str, TaskResult]:
        """Execute all tasks respecting dependencies and parallelism constraints."""
        self.logger.info(
            f"Starting parallel execution of {len(self.config.tasks)} tasks "
            f"(max parallel: {self.config.max_parallel_tasks})"
        )

        # Print dependency graph visualization
        self.logger.info(f"\\n{self.graph.visualize_ascii()}")

        # Initialize progress display for all tasks
        if self.progress_display:
            for task in self.config.tasks:
                self.progress_display.update_task(
                    task.name, TaskStatus.PENDING, dependencies=task.depends_on
                )

        start_time = time.time()
        results: dict[str, TaskResult] = {}

        try:
            async with create_task_group() as tg:
                # Start the scheduler in the background
                tg.start_soon(self._scheduler_loop, tg)

                # Wait for all tasks to complete or shutdown
                await self._wait_for_completion()

        except Exception:
            self.logger.exception("Error during parallel execution")
            raise

        # Collect results
        for name, state in self.task_states.items():
            if state.result:
                results[name] = state.result

        duration = time.time() - start_time
        self.logger.info(
            f"Parallel execution completed in {duration:.2f}s. "
            f"Tasks: {len(self.resource_pool.completed_tasks)} succeeded, "
            f"{len(self.resource_pool.failed_tasks)} failed"
        )

        return results

    async def _scheduler_loop(self, tg: TaskGroup) -> None:
        """Main scheduler loop that assigns ready tasks to workers."""
        self.logger.debug("Scheduler loop started")

        while not self._shutdown_requested:
            # Find tasks that are ready to execute
            ready_tasks = self._get_ready_tasks()

            if not ready_tasks and len(self.resource_pool.running_tasks) == 0:
                # No more tasks to run and nothing running
                self.logger.debug("All tasks completed, scheduler shutting down")
                break

            # Schedule ready tasks that fit within resource constraints
            scheduled_count = 0
            for task_name in ready_tasks:
                task = self.config.get_task_by_name(task_name)
                if task and self.resource_pool.can_schedule(task):
                    self.logger.debug(f"Scheduling task: {task_name}")
                    self.resource_pool.allocate(task)
                    self.task_states[task_name].status = TaskStatus.RUNNING
                    self.task_states[task_name].start_time = time.time()

                    # Update progress display
                    if self.progress_display:
                        self.progress_display.update_task(
                            task_name,
                            TaskStatus.RUNNING,
                            progress=0.0,
                            message="Starting...",
                        )

                    # Start task execution in background
                    tg.start_soon(self._execute_task, task)
                    scheduled_count += 1

            if scheduled_count > 0:
                self.logger.info(
                    f"Scheduled {scheduled_count} tasks. "
                    f"Running: {len(self.resource_pool.running_tasks)}, "
                    f"Completed: {len(self.resource_pool.completed_tasks)}"
                )

            # Wait a bit before checking for new ready tasks
            await anyio.sleep(0.1)

        self.logger.debug("Scheduler loop ended")

    async def _execute_task(self, task: TaskConfig) -> None:
        """Execute a single task and update its state."""
        self.logger.info(f"Starting execution of task: {task.name}")

        try:
            # Mark task as running in state manager
            self.state_manager.mark_task_running(task.name)

            # Update progress: task is running
            if self.progress_display:
                self.progress_display.update_task(
                    task.name,
                    TaskStatus.RUNNING,
                    progress=0.1,
                    message="Executing Claude prompt...",
                )

            # Execute the task (this is synchronous, so run in thread)
            result = await anyio.to_thread.run_sync(
                self.runner.run_task, task, self.state_manager
            )

            # Update execution state
            self.task_states[task.name].result = result
            self.task_states[task.name].end_time = time.time()

            if result.success:
                self.task_states[task.name].status = TaskStatus.COMPLETED
                session_info = (
                    f" (session: {result.session_id})" if result.session_id else ""
                )
                self.logger.info(
                    f"Task {task.name} completed successfully in "
                    f"{self.task_states[task.name].duration:.2f}s{session_info}"
                )

                # Update progress: task completed
                if self.progress_display:
                    self.progress_display.update_task(
                        task.name,
                        TaskStatus.COMPLETED,
                        progress=1.0,
                        message="Complete",
                    )
            else:
                self.task_states[task.name].status = TaskStatus.FAILED
                session_info = (
                    f" (session: {result.session_id})" if result.session_id else ""
                )
                self.logger.error(
                    f"Task {task.name} failed{session_info}: {result.error}"
                )

                # Update progress: task failed
                if self.progress_display:
                    self.progress_display.update_task(
                        task.name,
                        TaskStatus.FAILED,
                        progress=1.0,
                        message="Failed",
                        error=result.error[:50] if result.error else "Unknown error",
                    )

            # Update state manager
            self.state_manager.update_task_state(result)

        except Exception as e:
            self.logger.exception(f"Unexpected error executing task {task.name}")
            self.task_states[task.name].status = TaskStatus.FAILED
            self.task_states[task.name].end_time = time.time()

            # Create a failure result
            result = TaskResult(
                task_name=task.name,
                success=False,
                error=f"Unexpected error: {e!s}",
                attempts=1,
            )
            self.task_states[task.name].result = result
            self.state_manager.update_task_state(result)

            # Update progress: unexpected failure
            if self.progress_display:
                self.progress_display.update_task(
                    task.name,
                    TaskStatus.FAILED,
                    progress=1.0,
                    message="Error",
                    error=str(e)[:50],
                )

        finally:
            # Release resources and signal completion
            self.resource_pool.release(
                task, self.task_states[task.name].status == TaskStatus.COMPLETED
            )
            self._task_completed_event.set()

    def _get_ready_tasks(self) -> list[str]:
        """Get tasks that are ready to execute (dependencies satisfied)."""
        ready = []

        for name, state in self.task_states.items():
            # If already marked as ready, include it
            if state.status == TaskStatus.READY:
                ready.append(name)
                continue

            # Check pending tasks for readiness
            if state.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                task = self.config.get_task_by_name(name)
                if task:
                    # Check dependency status
                    dep_states = [
                        self.task_states.get(dep, TaskExecutionState(dep)).status
                        for dep in task.depends_on
                    ]

                    # If any dependency failed, skip this task
                    if any(status == TaskStatus.FAILED for status in dep_states):
                        state.status = TaskStatus.SKIPPED
                        state.end_time = time.time()
                        self.logger.info(
                            f"Skipping task {name} due to failed dependencies"
                        )

                        # Update progress display
                        if self.progress_display:
                            self.progress_display.update_task(
                                name,
                                TaskStatus.SKIPPED,
                                message="Skipped (dependency failed)",
                            )
                        continue

                    # If all dependencies completed successfully, mark as ready
                    if all(status == TaskStatus.COMPLETED for status in dep_states):
                        ready.append(name)
                        state.status = TaskStatus.READY
                        state.dependencies_met = True

                        # Update progress display
                        if self.progress_display:
                            self.progress_display.update_task(
                                name, TaskStatus.READY, message="Ready to run"
                            )

        return ready

    async def _wait_for_completion(self) -> None:
        """Wait for all tasks to complete."""
        while True:
            # Check if all tasks are done
            all_done = all(
                state.status
                in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)
                for state in self.task_states.values()
            )

            if all_done or self._shutdown_requested:
                break

            # Wait a bit before checking again
            await anyio.sleep(0.1)

    def shutdown(self) -> None:
        """Request graceful shutdown of the coordinator."""
        self.logger.info("Shutdown requested")
        self._shutdown_requested = True
        self._task_completed_event.set()
