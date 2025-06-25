"""Task runner for executing prompts with Claude Code."""

import asyncio
import subprocess
import time
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, query

from .config import PrompterConfig, TaskConfig
from .logging import get_logger


class TaskResult:
    """Result of a task execution."""

    def __init__(
        self,
        task_name: str,
        success: bool,
        output: str = "",
        error: str = "",
        verification_output: str = "",
        attempts: int = 1,
    ) -> None:
        self.task_name = task_name
        self.success = success
        self.output = output
        self.error = error
        self.verification_output = verification_output
        self.attempts = attempts
        self.timestamp = time.time()


class TaskRunner:
    """Executes tasks using Claude Code SDK."""

    def __init__(self, config: PrompterConfig, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self.current_directory = (
            Path(config.working_directory) if config.working_directory else Path.cwd()
        )
        self.logger = get_logger("runner")

    def run_task(self, task: TaskConfig) -> TaskResult:
        """Execute a single task."""
        self.logger.info(f"Starting task: {task.name}")

        if self.dry_run:
            return self._dry_run_task(task)

        attempts = 0
        while attempts < task.max_attempts:
            attempts += 1
            self.logger.debug(
                f"Task {task.name} attempt {attempts}/{task.max_attempts}"
            )

            # Execute the prompt with Claude Code
            claude_result = self._execute_claude_prompt(task)
            if not claude_result[0]:
                if attempts >= task.max_attempts:
                    return TaskResult(
                        task.name,
                        success=False,
                        error=f"Failed to execute Claude prompt after {attempts} attempts: {claude_result[1]}",
                        attempts=attempts,
                    )
                continue

            # Wait for the check interval before verification
            if self.config.check_interval > 0:
                time.sleep(self.config.check_interval)

            # Verify the task was successful
            verify_result = self._verify_task(task)

            if verify_result[0]:
                return TaskResult(
                    task.name,
                    success=True,
                    output=claude_result[1],
                    verification_output=verify_result[1],
                    attempts=attempts,
                )
            if task.on_failure == "stop":
                return TaskResult(
                    task.name,
                    success=False,
                    output=claude_result[1],
                    error=f"Verification failed: {verify_result[1]}",
                    verification_output=verify_result[1],
                    attempts=attempts,
                )
            if task.on_failure == "next":
                return TaskResult(
                    task.name,
                    success=False,
                    output=claude_result[1],
                    error=f"Verification failed, moving to next task: {verify_result[1]}",
                    verification_output=verify_result[1],
                    attempts=attempts,
                )
                # Otherwise retry (continue the loop)

        # Store the last verification output if available
        last_verification_output = ""
        if "verify_result" in locals():
            last_verification_output = verify_result[1]

        return TaskResult(
            task.name,
            success=False,
            error=f"Task failed after {task.max_attempts} attempts",
            verification_output=last_verification_output,
            attempts=attempts,
        )

    def _dry_run_task(self, task: TaskConfig) -> TaskResult:
        """Simulate task execution for dry run."""
        return TaskResult(
            task.name,
            success=True,
            output=f"[DRY RUN] Would execute prompt: {task.prompt[:50]}...",
            verification_output=f"[DRY RUN] Would run verification: {task.verify_command}",
        )

    def _execute_claude_prompt(self, task: TaskConfig) -> tuple[bool, str]:
        """Execute a Claude Code prompt using SDK."""
        try:
            # Run the async query in a synchronous context
            return asyncio.run(self._execute_claude_prompt_async(task))
        except TimeoutError:
            return False, f"Claude SDK task timed out after {task.timeout} seconds"
        except Exception as e:
            return False, f"Error executing Claude SDK task: {e}"

    async def _execute_claude_prompt_async(self, task: TaskConfig) -> tuple[bool, str]:
        """Execute a Claude Code prompt using SDK asynchronously."""
        try:
            # Create options with working directory
            options = ClaudeCodeOptions(
                cwd=str(self.current_directory),
                permission_mode="bypassPermissions",  # Auto-accept all actions for automation
            )

            # Collect all messages from the query
            messages = []
            async for message in query(prompt=task.prompt, options=options):
                messages.append(message)

            # Extract text content from messages
            output_text = ""
            for msg in messages:
                # Check if message has content attribute and extract text
                if hasattr(msg, "content"):
                    for content in msg.content:
                        if hasattr(content, "text"):
                            output_text += content.text + "\n"

            if output_text.strip():
                return True, output_text.strip()
            return False, "Claude SDK returned empty response"

        except TimeoutError:
            raise TimeoutError(f"Task timed out after {task.timeout} seconds")
        except Exception:
            raise

    def _verify_task(self, task: TaskConfig) -> tuple[bool, str]:
        """Verify that a task completed successfully."""
        try:
            # Execute the verification command
            result = subprocess.run(
                task.verify_command,
                check=False,
                shell=True,
                cwd=self.current_directory,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for verification
            )

            success = result.returncode == task.verify_success_code
            output = f"Exit code: {result.returncode}\\nStdout: {result.stdout}\\nStderr: {result.stderr}"

            return success, output

        except subprocess.TimeoutExpired:
            return False, "Verification command timed out"
        except Exception as e:
            return False, f"Error running verification command: {e}"

    def run_all_tasks(self) -> list[TaskResult]:
        """Run all tasks in sequence."""
        results = []

        for task in self.config.tasks:
            result = self.run_task(task)
            results.append(result)

            if not result.success:
                if task.on_failure == "stop":
                    break
                if task.on_failure == "next":
                    continue

            if result.success and task.on_success == "stop":
                break
            if result.success and task.on_success == "repeat":
                # Add the same task again for repetition
                # Note: This could lead to infinite loops, might need better handling
                continue

        return results
