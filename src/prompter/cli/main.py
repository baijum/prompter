"""Main orchestration logic for the prompter CLI."""

import sys
from pathlib import Path

from prompter.config import PrompterConfig
from prompter.logging import setup_logging
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
        level="DEBUG" if args.verbose else "INFO",
        log_file=args.log_file,
        verbose=args.verbose,
    )

    # Initialize state manager
    state_manager = StateManager(args.state_file)

    # Handle status command
    if args.status:
        print_status(state_manager, args.verbose)
        return 0

    # Handle clear state command
    if args.clear_state:
        state_manager.clear_state()
        print("State cleared.")
        return 0

    # Handle init command
    if args.init:
        generate_sample_config(args.init)
        return 0

    # Require config file for other operations
    if not args.config:
        parser.error(
            "Configuration file is required unless using --status, --clear-state, or --init"
        )

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        # Load and validate configuration
        config = PrompterConfig(config_path)
        errors = config.validate()
        if errors:
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        # Initialize task runner
        runner = TaskRunner(config, dry_run=args.dry_run)

        # Determine which tasks to run
        tasks_to_run = []
        if args.task:
            task = config.get_task_by_name(args.task)
            if not task:
                print(
                    f"Error: Task '{args.task}' not found in configuration",
                    file=sys.stderr,
                )
                return 1
            tasks_to_run = [task]
        else:
            tasks_to_run = config.tasks

        if not tasks_to_run:
            print("No tasks to run", file=sys.stderr)
            return 1

        # Execute tasks
        print(f"Running {len(tasks_to_run)} task(s)...")
        if args.dry_run:
            print("[DRY RUN MODE - No actual changes will be made]")

        for task in tasks_to_run:
            print(f"\\nExecuting task: {task.name}")
            if args.verbose:
                print(f"  Prompt: {task.prompt}")
                print(f"  Verify command: {task.verify_command}")

            # Mark task as running
            state_manager.mark_task_running(task.name)

            # Execute the task
            result = runner.run_task(task)

            # Update state
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
                    print("Stopping execution due to task failure.")
                    break

        # Print final status
        print("\\nFinal status:")
        print_status(state_manager, args.verbose)

        # Return appropriate exit code
        failed_tasks = state_manager.get_failed_tasks()
        return 1 if failed_tasks else 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
