# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Prompter** is a Python-based tool designed to run prompts sequentially to tidy large code bases using Claude Code. The project is currently in its initial setup phase.

## Development Environment Setup

Since this is a new Python project without dependencies defined yet, you'll need to:

1. Set up a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies once a requirements.txt or pyproject.toml is created

## Common Development Tasks

### Installation and Setup

```bash
# Install the package in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Running the Tool

```bash
# Run all tasks from a configuration file
prompter example.toml

# Dry run to see what would be executed
prompter example.toml --dry-run

# Run a specific task
prompter example.toml --task fix_compiler_warnings

# Check current status
prompter --status

# Clear saved state
prompter --clear-state
```

### Testing

The project uses pytest with comprehensive test coverage:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/prompter --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run tests matching pattern
pytest -k "test_config"

# Run tests with verbose output
pytest -v

# Run only unit tests (excluding integration)
pytest -m "not integration"
```

**Test Structure:**
- `tests/test_config.py` - Configuration parsing and validation
- `tests/test_runner.py` - Task execution with mocked subprocess calls  
- `tests/test_state.py` - State management with file system mocking
- `tests/test_cli.py` - CLI argument parsing and integration
- `tests/test_integration.py` - End-to-end integration tests
- `tests/test_helpers.py` - Test utilities and builder patterns

### Linting and Code Quality

```bash
ruff check .
ruff format .
mypy src/
```

## Architecture Notes

The project automates code tidying tasks through:

### Core Components
- **Configuration Parser** (`src/prompter/config.py`): Handles TOML configuration parsing and validation
- **Task Runner** (`src/prompter/runner.py`): Executes Claude Code commands and verifies results
- **State Manager** (`src/prompter/state.py`): Tracks task progress and persists state between runs
- **CLI Interface** (`src/prompter/cli.py`): Command-line interface with comprehensive options

### TOML Configuration Structure
Tasks are defined in TOML files with:
- `prompt`: The instruction to give Claude Code
- `verify_command`: Command to check if the task succeeded
- `verify_success_code`: Expected exit code (default: 0)
- `on_success`/`on_failure`: What to do next ("next", "stop", "retry")
- `max_attempts`: Maximum retry attempts
- `timeout`: Optional timeout for Claude execution

### State Persistence
The tool maintains state in `.prompter_state.json` to:
- Track task progress across sessions
- Handle interruptions and resumption
- Provide status reporting
- Maintain execution history

### Usage Patterns
1. Define tasks in a TOML configuration file
2. Run `prompter config.toml` to execute all tasks
3. Monitor progress with `prompter --status`
4. Use `--dry-run` for testing configurations