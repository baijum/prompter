"""Main orchestration logic for the prompter CLI."""

import sys
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

        # Execute tasks
        print(f"Running {len(tasks_to_run)} task(s)...")
        if args.dry_run:
            print("[DRY RUN MODE - No actual changes will be made]")

        for i, task in enumerate(tasks_to_run):
            logger.debug(f"Processing task {i + 1}/{len(tasks_to_run)}: {task.name}")
            print(f"\\nExecuting task: {task.name}")
            if args.verbose:
                print(f"  Prompt: {task.prompt}")
                print(f"  Verify command: {task.verify_command}")

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
            else:
                print(f"  ✗ Task failed (attempts: {result.attempts})")
                print(f"  Error: {result.error}")

                # Handle failure based on task configuration
                if task.on_failure == "stop":
                    logger.debug(
                        f"Task {task.name} failed with on_failure=stop, stopping execution"
                    )
                    print("Stopping execution due to task failure.")
                    break
                if task.on_failure == "next":
                    logger.debug(
                        f"Task {task.name} failed with on_failure=next, continuing to next task"
                    )

        # Print final status
        print("\\nFinal status:")
        print_status(state_manager, args.verbose)

        # Return appropriate exit code
        failed_tasks = state_manager.get_failed_tasks()
        logger.debug(f"Execution complete: {len(failed_tasks)} failed tasks")
        return 1 if failed_tasks else 0

    except Exception as e:
        logger.exception("Unhandled exception")
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
