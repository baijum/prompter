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

### Basic Commands

```bash
# Run all tasks from a configuration file
prompter config.toml

# Dry run to see what would be executed without making changes
prompter config.toml --dry-run

# Run a specific task by name
prompter config.toml --task fix_warnings

# Check current status and progress
prompter --status

# Clear saved state for a fresh start
prompter --clear-state

# Enable verbose output for debugging
prompter config.toml --verbose

# Save logs to a file
prompter config.toml --log-file debug.log
```

### Common Use Cases

#### 1. Code Modernization
```bash
# Create a config file for updating deprecated APIs
cat > modernize.toml << EOF
[settings]
working_directory = "/path/to/your/project"

[[tasks]]
name = "update_apis"
prompt = "Update all deprecated API calls to their modern equivalents"
verify_command = "python -m py_compile *.py"
on_success = "next"
on_failure = "retry"
max_attempts = 2

[[tasks]]
name = "add_type_hints"
prompt = "Add missing type hints to all functions and methods"
verify_command = "mypy --strict ."
on_success = "stop"
EOF

# Run the modernization
prompter modernize.toml
```

#### 2. Documentation Updates
```bash
# Keep docs in sync with code changes
cat > docs.toml << EOF
[[tasks]]
name = "update_docstrings"
prompt = "Update all docstrings to match current function signatures and behavior"
verify_command = "python -m doctest -v *.py"

[[tasks]]
name = "update_readme"
prompt = "Update README.md to reflect recent API changes and new features"
verify_command = "markdownlint README.md"
EOF

prompter docs.toml --dry-run  # Preview changes first
prompter docs.toml            # Apply changes
```

#### 3. Code Quality Improvements
```bash
# Fix linting issues and improve code quality
cat > quality.toml << EOF
[[tasks]]
name = "fix_linting"
prompt = "Fix all linting errors and warnings reported by flake8 and pylint"
verify_command = "flake8 . && pylint *.py"
on_failure = "retry"
max_attempts = 3

[[tasks]]
name = "improve_formatting"
prompt = "Improve code formatting and add missing blank lines for better readability"
verify_command = "black --check ."
EOF

prompter quality.toml
```

### State Management

Prompter automatically tracks your progress:

```bash
# Check what's been completed
prompter --status

# Example output:
# Session ID: 1703123456
# Total tasks: 3
# Completed: 2
# Failed: 0
# Running: 0
# Pending: 1

# Resume from where you left off
prompter config.toml  # Automatically skips completed tasks

# Start fresh if needed
prompter --clear-state
prompter config.toml
```

### Advanced Configuration

#### Task Dependencies and Flow Control
```toml
[settings]
working_directory = "/path/to/project"
check_interval = 30
max_retries = 3

# Task that stops on failure
[[tasks]]
name = "critical_fixes"
prompt = "Fix any critical security vulnerabilities"
verify_command = "safety check"
on_failure = "stop"  # Don't continue if this fails
max_attempts = 1

# Task that continues despite failures
[[tasks]]
name = "optional_cleanup"
prompt = "Remove unused imports and variables"
verify_command = "autoflake --check ."
on_failure = "next"  # Continue to next task even if this fails

# Task with custom timeout
[[tasks]]
name = "slow_operation"
prompt = "Refactor large legacy module"
verify_command = "python -m unittest discover"
timeout = 600  # 10 minutes
```

#### Multiple Project Workflow
```bash
# Process multiple projects in sequence
for project in project1 project2 project3; do
    cd "$project"
    prompter ../shared-config.toml --verbose
    cd ..
done
```

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