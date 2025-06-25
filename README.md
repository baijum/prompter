# Prompter

A Python tool for running prompts sequentially to tidy large code bases using Claude Code SDK.

[![PyPI version](https://badge.fury.io/py/claude-code-prompter.svg)](https://badge.fury.io/py/claude-code-prompter)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Requirements

- Python 3.11 or higher
- Claude Code SDK

## Installation

Install from PyPI:

```bash
pip install claude-code-prompter
```

Or install from source:

```bash
# Install the package
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Usage

```bash
# Run all tasks from a configuration file
prompter config.toml

# Dry run to see what would be executed
prompter config.toml --dry-run

# Run a specific task
prompter config.toml --task task_name

# Check current status
prompter --status

# Clear saved state
prompter --clear-state
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run tests with coverage
make coverage

# Generate and open HTML coverage report
make coverage-html

# Show coverage report in terminal with missing lines
make coverage-report
```

### Test Coverage

This project uses pytest-cov for test coverage reporting. Coverage configuration is in `pyproject.toml`.

```bash
# Run tests with coverage using pytest directly
pytest --cov=src/prompter --cov-report=term-missing

# Generate multiple coverage formats
pytest --cov=src/prompter --cov-report=term --cov-report=html --cov-report=xml
```

### Using Tox for Multi-Version Testing

```bash
# Test across all Python versions
tox

# Test specific Python version
tox -e py311

# Run linting
tox -e lint

# Run type checking
tox -e type

# Generate coverage report
tox -e coverage
```

### Code Quality

```bash
# Run linting
make lint

# Run type checking
make type-check

# Format code
make format

# Run all checks
make all
```

### CI/CD

The project uses GitHub Actions for continuous integration. The workflow:
- Tests on Python 3.11 and 3.12
- Runs linting and type checking
- Generates coverage reports
- Uploads coverage to Codecov (if configured)
- Builds and validates the package

## Configuration

Create a TOML configuration file with your tasks:

```toml
[settings]
check_interval = 30
max_retries = 3
working_directory = "/path/to/project"

[[tasks]]
name = "fix_warnings"
prompt = "Fix all compiler warnings in the codebase"
verify_command = "make test"
verify_success_code = 0
on_success = "next"
on_failure = "retry"
max_attempts = 3
timeout = 300
```

## License

MIT