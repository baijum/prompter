"""Main orchestration logic for the prompter CLI."""

import sys
import tomllib
from pathlib import Path

from prompter.config import PrompterConfig
from prompter.logging import get_logger, setup_logging
from prompter.runner import TaskRunner
from prompter.state import StateManager

from .arguments import create_parser
from .sample_config import generate_sample_config
from .status import print_status


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

    # Handle status command
    if args.status:
        logger.debug("Handling status command")
        print_status(state_manager, args.verbose)
        return 0

    # Handle clear state command
    if args.clear_state:
        logger.debug("Handling clear-state command")
        state_manager.clear_state()
        print("State cleared.")
        return 0

    # Handle init command
    if args.init:
        logger.debug(f"Handling init command: generating sample config at {args.init}")
        generate_sample_config(args.init)
        return 0

    # Require config file for other operations
    if not args.config:
        parser.error(
            "Configuration file is required unless using --status, --clear-state, or --init"
        )

    config_path = Path(args.config)
    logger.debug(f"Loading configuration from {config_path}")
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        # Load and validate configuration
        logger.debug("Loading and validating configuration")
        config = PrompterConfig(config_path)
        errors = config.validate()
        if errors:
            logger.error(f"Configuration validation failed with {len(errors)} errors")
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        logger.debug("Configuration loaded and validated successfully")

        # Initialize task runner
        logger.debug(f"Initializing task runner (dry_run={args.dry_run})")
        runner = TaskRunner(config, dry_run=args.dry_run)

        # Determine which tasks to run
        tasks_to_run = []
        if args.task:
            logger.debug(f"Running specific task: {args.task}")
            task = config.get_task_by_name(args.task)
            if not task:
                logger.error(f"Task '{args.task}' not found in configuration")
                print(
                    f"Error: Task '{args.task}' not found in configuration",
                    file=sys.stderr,
                )
                return 1
            tasks_to_run = [task]
        else:
            logger.debug(f"Running all {len(config.tasks)} tasks")
            tasks_to_run = config.tasks

        if not tasks_to_run:
            print("No tasks to run", file=sys.stderr)
            return 1

        # Execute tasks with support for task jumping
        print(f"Running {len(tasks_to_run)} task(s)...")
        if args.dry_run:
            print("[DRY RUN MODE - No actual changes will be made]")

        # Create a mapping of task names to tasks for jumping
        task_map = {task.name: task for task in config.tasks}

        # Track which tasks have been executed to avoid infinite loops
        executed_tasks = set()

        # Safety counter for when infinite loops are allowed
        max_iterations = 1000  # Prevent true infinite loops even when allowed
        iteration_count = 0

        # If running a specific task, start with just that task
        # Otherwise, start with the list of all tasks
        if args.task:
            current_task_idx = 0
            tasks_list = tasks_to_run
        else:
            current_task_idx = 0
            tasks_list = tasks_to_run

        while current_task_idx < len(tasks_list):
            # Safety check for runaway loops even when infinite loops are allowed
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.error(
                    f"Maximum iteration limit ({max_iterations}) reached. Stopping to prevent runaway loop."
                )
                print(
                    f"\nError: Maximum iteration limit ({max_iterations}) reached. Stopping execution."
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

            # Mark task as running
            logger.debug(f"Marking task {task.name} as running")
            state_manager.mark_task_running(task.name)

            # Execute the task
            logger.debug(f"Executing task {task.name}")
            result = runner.run_task(task)

            # Update state
            logger.debug(
                f"Updating state for task {task.name}: success={result.success}"
            )
            state_manager.update_task_state(result)

            # Print result
            if result.success:
                print(f"  ✓ Task completed successfully (attempts: {result.attempts})")
                if args.verbose and result.verification_output:
                    print(f"  Verification output: {result.verification_output}")

                # Handle success action
                next_action = task.on_success
                if next_action == "stop":
                    logger.debug(f"Task {task.name} succeeded with on_success=stop")
                    print("Stopping execution after successful task.")
                    break
                if next_action == "repeat":
                    logger.debug(f"Task {task.name} succeeded with on_success=repeat")
                    print("Repeating task...")
                    executed_tasks.remove(task.name)  # Allow re-execution
                    continue
                if next_action == "next":
                    logger.debug(f"Task {task.name} succeeded with on_success=next")
                    current_task_idx += 1
                elif next_action in task_map:
                    # Jump to specific task
                    logger.debug(
                        f"Task {task.name} succeeded, jumping to task '{next_action}'"
                    )
                    print(f"Jumping to task: {next_action}")
                    # Find the task in the original list or add it
                    if next_action not in [t.name for t in tasks_list]:
                        tasks_list.append(task_map[next_action])
                    # Set index to jump to the task
                    for idx, t in enumerate(tasks_list):
                        if t.name == next_action:
                            current_task_idx = idx
                            break
                else:
                    current_task_idx += 1
            else:
                print(f"  ✗ Task failed (attempts: {result.attempts})")
                print(f"  Error: {result.error}")

                # Handle failure action
                next_action = task.on_failure
                if next_action == "stop":
                    logger.debug(
                        f"Task {task.name} failed with on_failure=stop, stopping execution"
                    )
                    print("Stopping execution due to task failure.")
                    break
                if next_action == "retry":
                    # This is already handled by max_attempts in run_task
                    logger.debug(f"Task {task.name} failed after all retry attempts")
                    current_task_idx += 1
                elif next_action == "next":
                    logger.debug(
                        f"Task {task.name} failed with on_failure=next, continuing to next task"
                    )
                    current_task_idx += 1
                elif next_action in task_map:
                    # Jump to specific task
                    logger.debug(
                        f"Task {task.name} failed, jumping to task '{next_action}'"
                    )
                    print(f"Jumping to task: {next_action}")
                    # Find the task in the original list or add it
                    if next_action not in [t.name for t in tasks_list]:
                        tasks_list.append(task_map[next_action])
                    # Set index to jump to the task
                    for idx, t in enumerate(tasks_list):
                        if t.name == next_action:
                            current_task_idx = idx
                            break
                else:
                    current_task_idx += 1

        # Print final status
        print("\\nFinal status:")
        print_status(state_manager, args.verbose)

        # Return appropriate exit code
        failed_tasks = state_manager.get_failed_tasks()
        logger.debug(f"Execution complete: {len(failed_tasks)} failed tasks")
        return 1 if failed_tasks else 0

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


if __name__ == "__main__":
    sys.exit(main())
