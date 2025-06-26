"""Main orchestration logic for the prompter CLI."""

import sys
import tomllib
from pathlib import Path
from typing import Any

from prompter.config import PrompterConfig
from prompter.constants import MAX_TASK_ITERATIONS
from prompter.logging import get_logger, setup_logging
from prompter.runner import TaskRunner
from prompter.state import StateManager

from .arguments import create_parser
from .status import print_status


def handle_status_command(state_manager: StateManager, verbose: bool) -> int:
    """Handle the status command."""
    logger = get_logger("cli")
    logger.debug("Handling status command")
    print_status(state_manager, verbose)
    return 0


def handle_clear_state_command(state_manager: StateManager) -> int:
    """Handle the clear-state command."""
    logger = get_logger("cli")
    logger.debug("Handling clear-state command")
    state_manager.clear_state()
    print("State cleared.")
    return 0


def handle_init_command(init_path: str) -> int:
    """Handle the init command."""
    logger = get_logger("cli")
    logger.debug(f"Handling init command: generating AI-powered config at {init_path}")
    from .init.generator import ConfigGenerator

    generator = ConfigGenerator(init_path)
    generator.generate()
    return 0


def load_and_validate_config(config_path: Path) -> PrompterConfig | None:
    """Load and validate the configuration file.

    Returns:
        PrompterConfig if successful, None if there are errors.
    """
    logger = get_logger("cli")
    logger.debug(f"Loading configuration from {config_path}")

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return None

    logger.debug("Loading and validating configuration")
    config = PrompterConfig(config_path)
    errors = config.validate()
    if errors:
        logger.error(f"Configuration validation failed with {len(errors)} errors")
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return None
    logger.debug("Configuration loaded and validated successfully")
    return config


def determine_tasks_to_run(
    config: PrompterConfig, task_name: str | None
) -> list | None:
    """Determine which tasks to run based on command line arguments.

    Returns:
        List of tasks to run, or None if there's an error.
    """
    logger = get_logger("cli")

    if task_name:
        logger.debug(f"Running specific task: {task_name}")
        task = config.get_task_by_name(task_name)
        if not task:
            logger.error(f"Task '{task_name}' not found in configuration")
            print(
                f"Error: Task '{task_name}' not found in configuration", file=sys.stderr
            )
            return None
        return [task]
    logger.debug(f"Running all {len(config.tasks)} tasks")
    return config.tasks


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging
    setup_logging(
        level="DEBUG" if args.verbose or args.debug else "INFO",
        log_file=args.log_file,
        verbose=args.verbose,
        debug=args.debug,
    )

    logger = get_logger("cli")
    logger.debug(f"Starting prompter with arguments: {vars(args)}")

    # Initialize state manager
    logger.debug(f"Initializing state manager with file: {args.state_file}")
    state_manager = StateManager(args.state_file)

    # Handle special commands
    if args.status:
        return handle_status_command(state_manager, args.verbose)

    if args.clear_state:
        return handle_clear_state_command(state_manager)

    if args.init:
        return handle_init_command(args.init)

    # Require config file for other operations
    if not args.config:
        parser.error(
            "Configuration file is required unless using --status, --clear-state, or --init"
        )

    config_path = Path(args.config)

    try:
        # Load and validate configuration
        config = load_and_validate_config(config_path)
        if not config:
            return 1

        # Initialize task runner
        logger.debug(f"Initializing task runner (dry_run={args.dry_run})")
        runner = TaskRunner(config, dry_run=args.dry_run)

        # Determine which tasks to run
        tasks_to_run = determine_tasks_to_run(config, args.task)
        if not tasks_to_run:
            return 1

        # Execute tasks
        return execute_tasks(config, runner, tasks_to_run, state_manager, args)

    except tomllib.TOMLDecodeError as e:
        # For TOML errors, the enhanced message is already in the exception
        print(f"\n{e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unhandled exception")
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def execute_tasks(
    config: PrompterConfig,
    runner: TaskRunner,
    tasks_to_run: list,
    state_manager: StateManager,
    args: Any,
) -> int:
    """Execute tasks with support for task jumping.

    Returns:
        0 if all tasks succeeded, 1 if any failed.
    """
    logger = get_logger("cli")

    print(f"Running {len(tasks_to_run)} task(s)...")
    if args.dry_run:
        print("[DRY RUN MODE - No actual changes will be made]")

    # Create a mapping of task names to tasks for jumping
    task_map = {task.name: task for task in config.tasks}

    # Track which tasks have been executed to avoid infinite loops
    executed_tasks = set()

    # Safety counter for when infinite loops are allowed
    iteration_count = 0

    # Start with the list of tasks to run
    current_task_idx = 0
    tasks_list = tasks_to_run

    while current_task_idx < len(tasks_list):
        # Safety check for runaway loops even when infinite loops are allowed
        iteration_count += 1
        if iteration_count > MAX_TASK_ITERATIONS:
            logger.error(
                f"Maximum iteration limit ({MAX_TASK_ITERATIONS}) reached. Stopping to prevent runaway loop."
            )
            print(
                f"\nError: Maximum iteration limit ({MAX_TASK_ITERATIONS}) reached. Stopping execution."
            )
            break

        task = tasks_list[current_task_idx]

        # Check for infinite loop (unless explicitly allowed)
        if task.name in executed_tasks and not config.allow_infinite_loops:
            logger.warning(
                f"Task '{task.name}' has already been executed, skipping to avoid loop"
            )
            current_task_idx += 1
            continue

        logger.debug(f"Processing task: {task.name}")
        print(f"\nExecuting task: {task.name}")
        if args.verbose:
            print(f"  Prompt: {task.prompt}")
            print(f"  Verify command: {task.verify_command}")

        # Mark task as executed
        executed_tasks.add(task.name)

        # Execute the task and handle its result
        result = execute_single_task(runner, task, state_manager)

        # Handle the task result and determine next action
        current_task_idx = handle_task_result(
            result,
            task,
            task_map,
            tasks_list,
            current_task_idx,
            executed_tasks,
            args.verbose,
        )

        if current_task_idx == -1:  # Signal to stop execution
            break

    # Print final status
    print("\nFinal status:")
    print_status(state_manager, args.verbose)

    # Return appropriate exit code
    failed_tasks = state_manager.get_failed_tasks()
    logger.debug(f"Execution complete: {len(failed_tasks)} failed tasks")
    return 1 if failed_tasks else 0


def execute_single_task(
    runner: TaskRunner, task: Any, state_manager: StateManager
) -> Any:
    """Execute a single task and update state.

    Returns:
        TaskResult from the execution.
    """
    logger = get_logger("cli")

    # Mark task as running
    logger.debug(f"Marking task {task.name} as running")
    state_manager.mark_task_running(task.name)

    # Execute the task
    logger.debug(f"Executing task {task.name}")
    result = runner.run_task(task, state_manager)

    # Update state
    logger.debug(f"Updating state for task {task.name}: success={result.success}")
    state_manager.update_task_state(result)

    return result


def handle_task_result(
    result: Any,
    task: Any,
    task_map: dict,
    tasks_list: list,
    current_task_idx: int,
    executed_tasks: set,
    verbose: bool,
) -> int:
    """Handle the result of a task execution and determine next action.

    Returns:
        Next task index, or -1 to signal stopping execution.
    """
    if result.success:
        print(f"  ✓ Task completed successfully (attempts: {result.attempts})")
        if verbose and result.verification_output:
            print(f"  Verification output: {result.verification_output}")

        # Handle success action
        next_action = task.on_success
        return handle_next_action(
            next_action,
            task.name,
            task_map,
            tasks_list,
            current_task_idx,
            executed_tasks,
            True,
        )
    print(f"  ✗ Task failed (attempts: {result.attempts})")
    print(f"  Error: {result.error}")

    # Handle failure action
    next_action = task.on_failure
    return handle_next_action(
        next_action,
        task.name,
        task_map,
        tasks_list,
        current_task_idx,
        executed_tasks,
        False,
    )


def handle_next_action(
    next_action: str,
    task_name: str,
    task_map: dict,
    tasks_list: list,
    current_task_idx: int,
    executed_tasks: set,
    success: bool,
) -> int:
    """Handle the next action after task completion.

    Returns:
        Next task index, or -1 to signal stopping execution.
    """
    logger = get_logger("cli")

    if next_action == "stop":
        logger.debug(
            f"Task {task_name} {'succeeded' if success else 'failed'} with on_{'success' if success else 'failure'}=stop"
        )
        print(
            f"Stopping execution {'after successful task' if success else 'due to task failure'}."
        )
        return -1

    if next_action == "repeat" and success:
        logger.debug(f"Task {task_name} succeeded with on_success=repeat")
        print("Repeating task...")
        executed_tasks.remove(task_name)  # Allow re-execution
        return current_task_idx

    if next_action == "next" or (next_action == "retry" and not success):
        logger.debug(
            f"Task {task_name} {'succeeded' if success else 'failed'}, continuing to next task"
        )
        return current_task_idx + 1

    if next_action in task_map:
        # Jump to specific task
        logger.debug(
            f"Task {task_name} {'succeeded' if success else 'failed'}, jumping to task '{next_action}'"
        )
        print(f"Jumping to task: {next_action}")

        # Find the task in the original list or add it
        if next_action not in [t.name for t in tasks_list]:
            tasks_list.append(task_map[next_action])

        # Set index to jump to the task
        for idx, t in enumerate(tasks_list):
            if t.name == next_action:
                return idx

    # Default: move to next task
    return current_task_idx + 1


if __name__ == "__main__":
    sys.exit(main())
