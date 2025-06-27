"""Task runner for executing prompts with Claude Code."""

import asyncio
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from claude_code_sdk import ClaudeCodeOptions, ResultMessage, query

from .config import PrompterConfig, TaskConfig
from .constants import DEFAULT_VERIFICATION_TIMEOUT
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
        session_id: str | None = None,
    ) -> None:
        self.task_name = task_name
        self.success = success
        self.output = output
        self.error = error
        self.verification_output = verification_output
        self.attempts = attempts
        self.session_id = session_id
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

    def _contains_json_error(self, exception: Exception) -> bool:
        """Check if an exception or its nested exceptions contain JSON decode errors."""
        # Check the exception itself
        error_str = str(exception)
        error_type = type(exception).__name__

        json_error_indicators = [
            "JSONDecodeError",
            "CLIJSONDecodeError",
            "Failed to decode JSON",
            "Unterminated string starting at",
            "json.decoder.JSONDecodeError",
        ]

        # Check if this is a direct JSON error
        if any(
            indicator in error_str or indicator in error_type
            for indicator in json_error_indicators
        ):
            return True

        # Handle ExceptionGroup (Python 3.11+)
        if hasattr(
            exception, "exceptions"
        ):  # ExceptionGroup has 'exceptions' attribute
            for sub_exception in exception.exceptions:
                if self._contains_json_error(sub_exception):
                    return True

        # Handle exception with __cause__ chain
        if exception.__cause__ and isinstance(exception.__cause__, Exception):
            return self._contains_json_error(exception.__cause__)

        return False

    def _extract_json_error_details(self, exception: Exception) -> str:
        """Extract detailed JSON error information from nested exceptions."""
        details = []

        # Direct error info
        details.append(
            f"Main error: {type(exception).__name__}: {str(exception)[:300]}"
        )

        # Extract from ExceptionGroup
        if hasattr(exception, "exceptions"):
            for i, sub_exc in enumerate(exception.exceptions):
                details.append(
                    f"  Sub-exception {i + 1}: {type(sub_exc).__name__}: {str(sub_exc)[:300]}"
                )
                if hasattr(sub_exc, "__cause__") and sub_exc.__cause__:
                    details.append(
                        f"    Caused by: {type(sub_exc.__cause__).__name__}: {str(sub_exc.__cause__)[:300]}"
                    )

        # Extract from cause chain
        if exception.__cause__:
            details.append(
                f"Caused by: {type(exception.__cause__).__name__}: {str(exception.__cause__)[:300]}"
            )

        return "\n".join(details)

    def run_task(self, task: TaskConfig, state_manager: Any = None) -> TaskResult:
        """Execute a single task."""
        self.logger.info(f"Starting task: {task.name}")
        self.logger.debug(
            f"Task configuration: name={task.name}, prompt={task.prompt[:100]}..., "
            f"verify_command={task.verify_command}, max_attempts={task.max_attempts}, "
            f"timeout={task.timeout}s, on_success={task.on_success}, on_failure={task.on_failure}, "
            f"resume_previous_session={task.resume_previous_session}, "
            f"system_prompt={'<set>' if task.system_prompt else '<not set>'}"
        )

        if self.dry_run:
            self.logger.debug(f"Dry run mode enabled for task {task.name}")
            return self._dry_run_task(task)

        attempts = 0
        verify_result = (False, "")  # Initialize to avoid locals() check
        last_error_was_json = False  # Track JSON errors for adaptive delays

        while attempts < task.max_attempts:
            attempts += 1

            # Add delay between retry attempts to help with JSON errors
            if attempts > 1:
                if last_error_was_json:
                    # Longer delay after JSON errors (5s, 10s, 15s... max 30s)
                    delay = min(attempts * 5, 30)
                    self.logger.warning(
                        f"Waiting {delay}s before retry due to previous JSON error "
                        f"(attempt {attempts}/{task.max_attempts})"
                    )
                else:
                    # Standard retry delay
                    delay = 3
                    self.logger.debug(
                        f"Waiting {delay}s before retry (attempt {attempts}/{task.max_attempts})"
                    )
                time.sleep(delay)

                # Force garbage collection to clean up resources
                import gc

                gc.collect()

            self.logger.debug(
                f"Task {task.name} attempt {attempts}/{task.max_attempts}"
            )

            # Check if we should resume from previous session
            resume_session_id = None
            if task.resume_previous_session and state_manager:
                resume_session_id = state_manager.get_previous_session_id(task.name)
                if resume_session_id:
                    self.logger.info(
                        f"Resuming from previous Claude session: {resume_session_id}"
                    )
                else:
                    self.logger.info("No previous session found to resume from")

            # Execute the prompt with Claude Code
            self.logger.debug(f"Executing Claude prompt for task {task.name}")
            claude_start_time = time.time()
            claude_result = self._execute_claude_prompt(task, resume_session_id)
            claude_duration = time.time() - claude_start_time
            self.logger.debug(
                f"Claude execution completed in {claude_duration:.2f}s, success={claude_result[0]}"
            )

            if not claude_result[0]:
                # Check if this was a JSON error
                error_msg = str(claude_result[1])
                last_error_was_json = (
                    "JSON" in error_msg
                    or "json" in error_msg
                    or "JSONDecodeError" in error_msg
                    or "CLIJSONDecodeError" in error_msg
                    or "Unterminated string starting at" in error_msg
                    or "unhandled errors in a TaskGroup" in error_msg
                )

                self.logger.debug(f"Claude execution failed: {claude_result[1]}")

                if attempts >= task.max_attempts:
                    return TaskResult(
                        task.name,
                        success=False,
                        error=f"Failed to execute Claude prompt after {attempts} attempts: {claude_result[1]}",
                        attempts=attempts,
                        session_id=claude_result[2] if len(claude_result) > 2 else None,
                    )
                continue

            # Wait for the check interval before verification
            if self.config.check_interval > 0:
                self.logger.debug(
                    f"Waiting {self.config.check_interval}s before verification"
                )
                time.sleep(self.config.check_interval)

            # Verify the task was successful
            self.logger.debug(f"Running verification command: {task.verify_command}")
            verify_start_time = time.time()
            verify_result = self._verify_task(task)
            verify_duration = time.time() - verify_start_time
            self.logger.debug(
                f"Verification completed in {verify_duration:.2f}s, success={verify_result[0]}"
            )

            if verify_result[0]:
                self.logger.debug(
                    f"Task {task.name} completed successfully on attempt {attempts}"
                )
                return TaskResult(
                    task.name,
                    success=True,
                    output=claude_result[1],
                    verification_output=verify_result[1],
                    attempts=attempts,
                    session_id=claude_result[2] if len(claude_result) > 2 else None,
                )
            if task.on_failure == "stop":
                return TaskResult(
                    task.name,
                    success=False,
                    output=claude_result[1],
                    error=f"Verification failed: {verify_result[1]}",
                    verification_output=verify_result[1],
                    attempts=attempts,
                    session_id=claude_result[2] if len(claude_result) > 2 else None,
                )
            if task.on_failure == "next":
                return TaskResult(
                    task.name,
                    success=False,
                    output=claude_result[1],
                    error=f"Verification failed, moving to next task: {verify_result[1]}",
                    verification_output=verify_result[1],
                    attempts=attempts,
                    session_id=claude_result[2] if len(claude_result) > 2 else None,
                )
                # Otherwise retry (continue the loop)

        # Store the last verification output
        last_verification_output = verify_result[1]

        return TaskResult(
            task.name,
            success=False,
            error=f"Task failed after {task.max_attempts} attempts",
            verification_output=last_verification_output,
            attempts=attempts,
            session_id=claude_result[2] if len(claude_result) > 2 else None,
        )

    def _dry_run_task(self, task: TaskConfig) -> TaskResult:
        """Simulate task execution for dry run."""
        return TaskResult(
            task.name,
            success=True,
            output=f"[DRY RUN] Would execute prompt: {task.prompt[:50]}...",
            verification_output=f"[DRY RUN] Would run verification: {task.verify_command}",
        )

    def _execute_claude_prompt(
        self, task: TaskConfig, resume_session_id: str | None = None
    ) -> tuple[bool, str, str | None]:
        """Execute a Claude Code prompt using SDK with JSON error handling."""
        json_retry_count = 0
        max_json_retries = 3

        while json_retry_count < max_json_retries:
            try:
                if json_retry_count > 0:
                    self.logger.warning(
                        f"Retrying after JSON error (attempt {json_retry_count + 1}/{max_json_retries}), "
                        f"waiting {json_retry_count * 2}s..."
                    )
                    time.sleep(json_retry_count * 2)

                    # Force cleanup before retry
                    import gc

                    gc.collect()

                self.logger.debug(
                    "Creating asyncio event loop for Claude SDK execution"
                )
                # Run the async query in a synchronous context
                result = asyncio.run(
                    self._execute_claude_prompt_async(task, resume_session_id)
                )
                self.logger.debug(
                    f"Claude SDK execution completed, result length: {len(result[1]) if result[0] else 0}"
                )
                return result

            except TimeoutError:
                self.logger.exception(
                    f"Claude SDK task timed out after {task.timeout} seconds"
                )
                return (
                    False,
                    f"Claude SDK task timed out after {task.timeout} seconds",
                    None,
                )
            except Exception as e:
                # Check if this is a JSON-related error using our helper
                if self._contains_json_error(e):
                    json_retry_count += 1
                    error_details = self._extract_json_error_details(e)

                    if json_retry_count < max_json_retries:
                        self.logger.warning(
                            f"JSON decoding error detected (attempt {json_retry_count}/{max_json_retries}):\n"
                            f"{error_details}\n"
                            f"Will retry after {json_retry_count * 2}s..."
                        )
                        continue
                    self.logger.exception(
                        f"JSON error persists after {max_json_retries} retries:\n{error_details}"
                    )

                self.logger.exception("Error executing Claude SDK task")
                return False, f"Error executing Claude SDK task: {e}", None

        return False, f"Failed after {max_json_retries} JSON retry attempts", None

    async def _execute_claude_prompt_async(
        self, task: TaskConfig, resume_session_id: str | None = None
    ) -> tuple[bool, str, str | None]:
        """Execute a Claude Code prompt using SDK asynchronously."""

        async def run_query() -> list:
            """Inner function to run the query that can be wrapped with timeout."""
            # Create options with working directory
            options = ClaudeCodeOptions(
                cwd=str(self.current_directory),
                permission_mode="bypassPermissions",  # Auto-accept all actions for automation
                resume=resume_session_id,  # Resume previous session if provided
                system_prompt=task.system_prompt,  # Pass task-specific system prompt if provided
            )

            if resume_session_id:
                self.logger.debug(f"Resuming Claude session: {resume_session_id}")

            # Collect all messages from the query
            messages = []
            async for message in query(prompt=task.prompt, options=options):
                messages.append(message)

            return messages

        try:
            # Execute with timeout if specified
            if task.timeout:
                messages = await asyncio.wait_for(run_query(), timeout=task.timeout)
            else:
                messages = await run_query()

            # Extract text content from messages and look for session_id
            output_text = ""
            session_id = None

            for msg in messages:
                # Check if this is a ResultMessage to extract session_id
                if isinstance(msg, ResultMessage):
                    session_id = msg.session_id
                    self.logger.debug(f"Found Claude session ID: {session_id}")

                # Check if message has content attribute and extract text
                if hasattr(msg, "content"):
                    for content in msg.content:
                        if hasattr(content, "text"):
                            output_text += content.text + "\n"

            if output_text.strip():
                return True, output_text.strip(), session_id
            return False, "Claude SDK returned empty response", session_id

        except TimeoutError:
            raise TimeoutError(f"Task timed out after {task.timeout} seconds")
        except Exception:
            raise

    def _verify_task(self, task: TaskConfig) -> tuple[bool, str]:
        """Verify that a task completed successfully."""
        try:
            # Detect if command requires shell interpretation
            shell_indicators = [
                "|",
                ">",
                "<",
                ">>",
                "&&",
                "||",
                ";",
                "$",
                "`",
                "*",
                "?",
                "[",
                "]",
            ]
            needs_shell = any(
                indicator in task.verify_command for indicator in shell_indicators
            )

            if needs_shell:
                self.logger.debug(
                    f"Shell features detected in command: {task.verify_command[:100]}... "
                    f"Using shell mode for execution."
                )

                # Use shell mode for commands with shell features
                # Security note: Commands come from trusted config files, not user input
                result = subprocess.run(
                    task.verify_command,
                    shell=True,
                    check=False,
                    cwd=self.current_directory,
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_VERIFICATION_TIMEOUT,
                )
            else:
                # Parse the command for simple execution
                try:
                    cmd_args = shlex.split(task.verify_command)
                except ValueError as e:
                    # Handle cases where shlex.split fails (e.g., unmatched quotes)
                    self.logger.warning(
                        f"Failed to parse command with shlex: {e}. "
                        f"Falling back to shell mode."
                    )
                    # Fall back to shell mode if parsing fails
                    result = subprocess.run(
                        task.verify_command,
                        shell=True,
                        check=False,
                        cwd=self.current_directory,
                        capture_output=True,
                        text=True,
                        timeout=DEFAULT_VERIFICATION_TIMEOUT,
                    )
                else:
                    # Execute without shell for simple commands
                    result = subprocess.run(
                        cmd_args,
                        check=False,
                        cwd=self.current_directory,
                        capture_output=True,
                        text=True,
                        timeout=DEFAULT_VERIFICATION_TIMEOUT,
                    )

            success = result.returncode == task.verify_success_code
            output = f"Exit code: {result.returncode}\\nStdout: {result.stdout}\\nStderr: {result.stderr}"

            self.logger.debug(
                f"Verification command completed: exit_code={result.returncode}, "
                f"expected={task.verify_success_code}, success={success}"
            )
            if result.stdout:
                self.logger.debug(
                    f"Verification stdout ({len(result.stdout)} chars): {result.stdout[:500]}..."
                )
            if result.stderr:
                self.logger.debug(
                    f"Verification stderr ({len(result.stderr)} chars): {result.stderr[:500]}..."
                )

            return success, output

        except subprocess.TimeoutExpired:
            return False, "Verification command timed out"
        except Exception as e:
            return False, f"Error running verification command: {e}"
