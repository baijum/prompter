"""Status display functionality for the prompter tool."""

from prompter.state import StateManager


def print_status(state_manager: StateManager, verbose: bool = False) -> None:
    """Print current task status."""
    summary = state_manager.get_summary()

    print(f"Session ID: {summary['session_id']}")
    print(f"Total tasks: {summary['total_tasks']}")
    print(f"Completed: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Running: {summary['running']}")
    print(f"Pending: {summary['pending']}")

    if verbose and state_manager.task_states:
        print("\\nTask Details:")
        for name, state in state_manager.task_states.items():
            print(f"  {name}: {state.status} (attempts: {state.attempts})")
            if state.error_message:
                print(f"    Error: {state.error_message}")
