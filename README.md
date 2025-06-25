# Prompter

A Python tool for running prompts sequentially to tidy large code bases using Claude Code SDK.

[![PyPI version](https://badge.fury.io/py/claude-code-prompter.svg)](https://badge.fury.io/py/claude-code-prompter)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **📚 Resources**: [GitHub Repository](https://github.com/baijum/prompter) | [Examples](https://github.com/baijum/prompter/tree/main/examples) | [System Prompt](https://github.com/baijum/prompter/blob/main/PROMPTER_SYSTEM_PROMPT.md)

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

## Quick Start

1. **Generate a sample configuration** to get started quickly:
   ```bash
   prompter --init
   ```

2. **Customize the configuration** file (`prompter.toml`) for your project:
   - Replace `make` commands with your project's build/test commands
   - Adjust prompts to match your coding standards
   - Modify task flow and retry settings

3. **Test your configuration** with a dry run:
   ```bash
   prompter prompter.toml --dry-run
   ```

4. **Run the tasks** when ready:
   ```bash
   prompter prompter.toml
   ```

## Usage

### Basic Commands

```bash
# Generate a sample configuration file to get started
prompter --init                     # Creates prompter.toml
prompter --init my-config.toml      # Creates custom-named config

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

# Enable extensive diagnostic logging (new in v0.3.0)
prompter config.toml --debug

# Save logs to a file
prompter config.toml --log-file debug.log

# Combine debug mode with log file for comprehensive diagnostics
prompter config.toml --debug --log-file debug.log
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

### Configuration Reference

#### Settings (Optional)
- `working_directory`: Base directory for command execution (default: current directory)
- `check_interval`: Seconds to wait between task completion and verification (default: 3600)
- `max_retries`: Global retry limit for all tasks (default: 3)

#### Task Fields
- `name` (required): Unique identifier for the task
- `prompt` (required): Instructions for Claude Code to execute
- `verify_command` (required): Shell command to verify task success
- `verify_success_code`: Expected exit code for success (default: 0)
- `on_success`: Action when task succeeds - `"next"`, `"stop"`, or `"repeat"` (default: "next")
- `on_failure`: Action when task fails - `"retry"`, `"stop"`, or `"next"` (default: "retry")
- `max_attempts`: Maximum retry attempts for this task (default: 3)
- `timeout`: Task timeout in seconds (optional)

## Examples and Templates

The project includes ready-to-use workflow templates in the `examples/` directory:

- **bdd-workflow.toml**: Automated BDD scenario implementation
- **refactor-codebase.toml**: Safe code refactoring with testing
- **security-audit.toml**: Security scanning and remediation

Find these examples in the [GitHub repository](https://github.com/baijum/prompter/tree/main/examples).

## AI-Assisted Configuration Generation

For complex workflows, you can use AI assistance to generate TOML configurations. We provide a comprehensive system prompt that helps AI assistants understand all the intricacies of the prompter tool.

### Using the System Prompt

1. **Get the system prompt** from the [GitHub repository](https://github.com/baijum/prompter/blob/main/PROMPTER_SYSTEM_PROMPT.md)

2. **Ask your AI assistant** (Claude, ChatGPT, etc.):
   ```
   [Paste the system prompt]
   
   Now create a prompter TOML configuration for: [describe your workflow]
   ```

3. **The AI will generate** a properly structured TOML that:
   - Breaks down complex tasks to avoid JSON parsing issues
   - Uses appropriate verification commands
   - Implements proper error handling
   - Follows best practices for the tool

4. **Validate the generated TOML**:
   ```bash
   # Test configuration without executing anything
   prompter generated-config.toml --dry-run
   
   # This will:
   # - Validate TOML syntax
   # - Check all required fields
   # - Display what would be executed
   # - Show any configuration errors
   ```

### Important: Avoiding Claude SDK Limitations

The Claude SDK currently has a JSON parsing bug with large responses. To avoid this:

1. **Keep prompts focused and concise** - Each task should have a single, clear objective
2. **Break complex workflows into smaller tasks** - This is better for reliability anyway
3. **Avoid asking Claude to echo large files** - Use specific, targeted instructions
4. **Use the `--debug` flag** if you encounter issues to see detailed error messages

Example of breaking down a complex task:

❌ **Bad (too complex, might fail)**:
```toml
[[tasks]]
name = "refactor_everything"
prompt = """
Analyze the entire codebase, identify all issues, fix all problems,
update all tests, improve documentation, and commit everything.
"""
```

✅ **Good (focused tasks)**:
```toml
[[tasks]]
name = "analyze_code"
prompt = "Identify the top 3 refactoring opportunities in the codebase"
verify_command = "test -f refactoring_plan.md"

[[tasks]]
name = "refactor_duplicates"
prompt = "Extract the most common duplicate code into shared utilities"
verify_command = "python -m py_compile **/*.py"

[[tasks]]
name = "run_tests"
prompt = "Run all tests and report any failures"
verify_command = "pytest"
```

## Troubleshooting

### Common Issues

1. **"JSONDecodeError: Unterminated string"** - Your prompt is generating responses that are too large
   - Solution: Break down the task into smaller, focused prompts
   - Use `--debug` to see the full error details

2. **Task keeps retrying** - The verify_command might not be testing the right thing
   - Solution: Ensure verify_command actually validates what the task accomplished

3. **"State file corrupted"** - Rare issue with interrupted execution
   - Solution: Run `prompter --clear-state` to start fresh

### Debug Mode

Run with extensive logging to diagnose issues:
```bash
prompter config.toml --debug --log-file debug.log
```

This provides:
- Detailed execution traces
- Claude SDK interaction logs
- State transition information
- Timing data for each operation

## License

MIT