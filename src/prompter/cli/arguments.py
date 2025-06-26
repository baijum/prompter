"""Command-line argument parser for the prompter tool."""

import argparse
from pathlib import Path

from prompter import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Run prompts sequentially to tidy large code base using Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  prompter --init                         # Generate AI-powered prompter.toml
  prompter --init my-config.toml          # Generate AI-powered configuration file
  prompter config.toml                    # Run all tasks from config.toml
  prompter config.toml --dry-run          # Show what would be executed
  prompter config.toml --task fix_warnings # Run only the 'fix_warnings' task
  prompter --status                       # Show current task status
  prompter --clear-state                  # Clear all saved state
        """,
    )

    parser.add_argument(
        "config",
        nargs="?",
        help="Path to the TOML configuration file",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without actually running tasks",
    )

    parser.add_argument(
        "--task",
        help="Run only the specified task by name",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current task status and exit",
    )

    parser.add_argument(
        "--clear-state",
        action="store_true",
        help="Clear all saved state and exit",
    )

    parser.add_argument(
        "--init",
        help="Generate a configuration file with AI assistance (specify filename, defaults to 'prompter.toml')",
        nargs="?",
        const="prompter.toml",
    )

    parser.add_argument(
        "--state-file",
        type=Path,
        help="Path to the state file (default: .prompter_state.json)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable extensive diagnostic logging (includes all debug messages)",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (optional)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"prompter {__version__}",
        help="Show program version and exit",
    )

    return parser
