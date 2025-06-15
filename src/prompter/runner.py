"""Task runner for executing prompts with Claude Code."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    """Executes tasks using Claude Code CLI."""
    
    def __init__(self, config: PrompterConfig, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self.current_directory = Path(config.working_directory) if config.working_directory else Path.cwd()
        self.logger = get_logger("runner")
        
    def run_task(self, task: TaskConfig) -> TaskResult:
        """Execute a single task."""
        self.logger.info(f"Starting task: {task.name}")
        
        if self.dry_run:
            return self._dry_run_task(task)
            
        attempts = 0
        while attempts < task.max_attempts:
            attempts += 1
            self.logger.debug(f"Task {task.name} attempt {attempts}/{task.max_attempts}")
            
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
            else:
                if task.on_failure == "stop":
                    return TaskResult(
                        task.name,
                        success=False,
                        output=claude_result[1],
                        error=f"Verification failed: {verify_result[1]}",
                        verification_output=verify_result[1],
                        attempts=attempts,
                    )
                elif task.on_failure == "next":
                    return TaskResult(
                        task.name,
                        success=False,
                        output=claude_result[1],
                        error=f"Verification failed, moving to next task: {verify_result[1]}",
                        verification_output=verify_result[1],
                        attempts=attempts,
                    )
                # Otherwise retry (continue the loop)
                
        return TaskResult(
            task.name,
            success=False,
            error=f"Task failed after {task.max_attempts} attempts",
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
        
    def _execute_claude_prompt(self, task: TaskConfig) -> Tuple[bool, str]:
        """Execute a Claude Code prompt."""
        try:
            # Construct the Claude Code command
            cmd = [self.config.claude_command, task.prompt]
            
            # Set timeout if specified
            timeout = task.timeout
            
            # Execute the command
            result = subprocess.run(
                cmd,
                cwd=self.current_directory,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"Claude command failed (exit code {result.returncode}): {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, f"Claude command timed out after {timeout} seconds"
        except FileNotFoundError:
            return False, f"Claude command not found: {self.config.claude_command}"
        except Exception as e:
            return False, f"Error executing Claude command: {e}"
            
    def _verify_task(self, task: TaskConfig) -> Tuple[bool, str]:
        """Verify that a task completed successfully."""
        try:
            # Execute the verification command
            result = subprocess.run(
                task.verify_command,
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
            
    def run_all_tasks(self) -> List[TaskResult]:
        """Run all tasks in sequence."""
        results = []
        
        for task in self.config.tasks:
            result = self.run_task(task)
            results.append(result)
            
            if not result.success:
                if task.on_failure == "stop":
                    break
                elif task.on_failure == "next":
                    continue
                    
            if result.success and task.on_success == "stop":
                break
            elif result.success and task.on_success == "repeat":
                # Add the same task again for repetition
                # Note: This could lead to infinite loops, might need better handling
                continue
                
        return results