# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Prompter** is a Python-based tool for orchestrating AI-powered code maintenance workflows using Claude Code. It supports both sequential task execution and conditional workflows with task jumping.

## Development Environment Setup

This project requires Python 3.11 or higher.

1. Set up a Python virtual environment:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

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

### Test Coverage

The project has comprehensive test coverage infrastructure:

```bash
# Run tests with coverage report
make coverage

# Generate and open HTML coverage report
make coverage-html

# Show coverage report with missing lines
make coverage-report

# Run with pytest directly
pytest --cov=src/prompter --cov-report=term-missing

# Run with multiple output formats
pytest --cov=src/prompter --cov-report=term --cov-report=html --cov-report=xml
```

Coverage configuration is in:
- `pyproject.toml` - Main coverage settings
- `.coveragerc` - Additional coverage configuration
- `tox.ini` - Multi-version testing configuration

The CI pipeline automatically generates coverage reports and can upload to Codecov.

### Linting and Code Quality

```bash
ruff check .
ruff format .
mypy src/
```

## Important Rules

**MANDATORY**: Always use the `date` command to get the current date when working with dates in documentation or code. Never rely on hardcoded or assumed dates.

**MANDATORY**: When making changes that affect the version number, ensure the version is synchronized between `pyproject.toml` and `src/prompter/__init__.py`. Both files must have the exact same version string. The version is typically updated during the release process, but if you need to fix a version mismatch, update both locations to match the version in `pyproject.toml`.

## Architecture Notes

The project automates code tidying tasks through Claude Code SDK (Python):

### Core Components
- **Configuration Parser** (`src/prompter/config.py`): Handles TOML configuration parsing and validation
- **Task Runner** (`src/prompter/runner.py`): Executes Claude Code tasks via SDK and verifies results
- **State Manager** (`src/prompter/state.py`): Tracks task progress and persists state between runs
- **CLI Interface** (`src/prompter/cli.py`): Command-line interface with comprehensive options

### TOML Configuration Structure
Tasks are defined in TOML files with:
- `prompt`: The instruction to give Claude Code
- `verify_command`: Command to check if the task succeeded
- `verify_success_code`: Expected exit code (default: 0)
- `on_success`/`on_failure`: What to do next ("next", "stop", "retry")
- `max_attempts`: Maximum retry attempts
- `timeout`: Optional timeout in seconds for Claude execution (no timeout if not specified)
- `system_prompt`: Optional custom system prompt to control Claude's behavior for the task
- `resume_previous_session`: Whether to resume from the previous task's Claude session (default: false)

### State Persistence
The tool maintains state in `.prompter_state.json` to:
- Track task progress across sessions
- Handle interruptions and resumption
- Provide status reporting
- Maintain execution history

### Timeout Behavior
The `timeout` parameter controls how long Claude Code is allowed to run for each task attempt:
- **Not specified**: Claude Code runs without any time limit until completion
- **Specified (e.g., `timeout = 300`)**: Execution stops after the specified seconds
- When a timeout occurs, it counts as a failed attempt and respects the `on_failure` setting
- Timeouts work with retry logic - if `max_attempts > 1`, the task will retry after a timeout

Example configuration with timeout:
```toml
[[tasks]]
name = "quick_fix"
prompt = "Fix the simple linting error"
verify_command = "ruff check ."
timeout = 60  # 1 minute timeout
max_attempts = 3
on_failure = "retry"
```

### System Prompt Behavior
The `system_prompt` parameter allows customizing Claude's behavior for specific tasks:
- **Not specified**: Claude uses its default behavior
- **Specified**: Claude adopts the specified role, constraints, or approach
- System prompts are particularly useful for:
  - Enforcing planning before execution
  - Setting expertise context (e.g., "You are a security expert")
  - Adding safety constraints for critical operations
  - Controlling output style and approach

Example configuration with system prompt:
```toml
[[tasks]]
name = "careful_refactor"
prompt = "Refactor the payment processing module"
system_prompt = "You are a senior engineer working on payment systems. Safety is paramount. Before making ANY changes, create a detailed plan including: 1) What will be changed, 2) Potential risks, 3) How to test each change. Present the plan and wait for approval."
verify_command = "python -m pytest tests/payment/"
timeout = 1800  # 30 minutes for careful work
```

This is especially powerful when combined with `resume_previous_session` for multi-phase workflows where different expertise is needed at each stage.

### Usage Patterns
1. Define tasks in a TOML configuration file
2. Run `prompter config.toml` to execute all tasks
3. Monitor progress with `prompter --status`
4. Use `--dry-run` for testing configurations

### Environment Variables
- `PROMPTER_INIT_TIMEOUT`: Controls the timeout (in seconds) for AI project analysis during `prompter --init`. Default is 120 seconds. Useful for large projects that need more time for analysis:
  ```bash
  export PROMPTER_INIT_TIMEOUT=300  # 5 minutes
  prompter --init
  ```
