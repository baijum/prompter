<div align="center">

![Prompter Logo](https://raw.githubusercontent.com/baijum/prompter/main/artifacts/logo-simple.svg)

# Prompter

> **Orchestrate AI-powered code maintenance at scale**

A Python tool for orchestrating AI-powered code maintenance workflows using Claude Code SDK.

[![PyPI version](https://badge.fury.io/py/claude-code-prompter.svg)](https://badge.fury.io/py/claude-code-prompter)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

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

## How It Works

Prompter supports two execution modes:

### 1. Sequential Execution (Default)
Tasks execute one after another in the order they're defined. Use `on_success = "next"` and `on_failure = "retry"` for traditional sequential workflows.

```toml
[[tasks]]
name = "lint"
on_success = "next"  # Continue to the next task in order

[[tasks]]
name = "test"
on_success = "next"  # Continue to the next task

[[tasks]]
name = "build"
on_success = "stop"  # End execution
```

### 2. Conditional Workflows (Task Jumping)
Tasks can jump to specific named tasks, enabling complex branching logic. Perfect for error handling, conditional deployments, and dynamic workflows.

```toml
[[tasks]]
name = "build"
on_success = "test"      # Jump to 'test' task
on_failure = "fix_build" # Jump to 'fix_build' on failure

[[tasks]]
name = "fix_build"
on_success = "build"     # Retry build after fixing
```

> ⚠️ **Warning: Infinite Loop Protection**
> When using task jumping, be careful not to create infinite loops. Prompter automatically detects and prevents infinite loops by tracking executed tasks. If a task tries to execute twice in the same run, it will be skipped with a warning. Always ensure your task flows have a clear termination condition.

## AI-Powered Project Analysis (New in v0.7.0)

Prompter can now analyze your project using Claude and automatically generate a customized configuration file tailored to your specific codebase.

### How It Works

The `--init` command:
1. **Scans your project** to detect languages, frameworks, and tools
2. **Analyzes code quality** to identify improvement opportunities
3. **Generates specific tasks** based on your project's needs
4. **Creates a ready-to-use configuration** with proper verification commands

### Examples

```bash
# Analyze current directory and generate prompter.toml
prompter --init

# Generate configuration with a custom name
prompter --init my-workflow.toml
```

### Supported Languages

The AI analyzer can detect and generate configurations for:
- Python (pytest, mypy, ruff, black)
- JavaScript/TypeScript (jest, eslint, prettier)
- Rust (cargo test, clippy, rustfmt)
- Go (go test, golint, gofmt)
- And more...

### What Gets Analyzed

- **Build Systems**: make, npm, cargo, gradle, etc.
- **Test Frameworks**: pytest, jest, cargo test, go test, etc.
- **Linters**: ruff, eslint, clippy, golint, etc.
- **Type Checkers**: mypy, tsc, etc.
- **Code Issues**: failing tests, linting errors, type issues
- **Security**: outdated dependencies, known vulnerabilities
- **Documentation**: missing docstrings, outdated READMEs

## Quick Start

1. **Let AI analyze your project** and generate a customized configuration:
   ```bash
   prompter --init
   ```
   This will:
   - Detect your project's language and tools automatically
   - Identify specific issues that need fixing
   - Generate tasks tailored to your codebase

2. **Review and customize** the generated configuration (`prompter.toml`):
   - The AI will show you what it found and ask for confirmation
   - You can modify task prompts and commands as needed
   - Adjust retry settings and flow control

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
# AI-powered configuration generation (analyzes your project)
prompter --init                     # Analyze project and create prompter.toml
prompter --init my-config.toml      # Create with custom name

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
timeout = 600  # 10 minutes - task will be terminated if it exceeds this

# Task without timeout (runs until completion)
[[tasks]]
name = "thorough_analysis"
prompt = "Perform comprehensive security audit"
verify_command = "security-scan --full"
# No timeout specified - Claude Code runs without time limit
```

#### Task Jumping and Conditional Workflows
```toml
# Jump to specific tasks based on success/failure
[[tasks]]
name = "build"
prompt = "Build the project"
verify_command = "test -f dist/app.js"
on_success = "test"      # Jump to 'test' task on success
on_failure = "fix_build" # Jump to 'fix_build' task on failure

[[tasks]]
name = "fix_build"
prompt = "Fix build errors and warnings"
verify_command = "test -f dist/app.js"
on_success = "test"  # Jump back to 'test' after fixing
on_failure = "stop"  # Stop if we can't fix the build
max_attempts = 2

[[tasks]]
name = "test"
prompt = "Run the test suite"
verify_command = "npm test"
on_success = "deploy"    # Continue to deploy
on_failure = "fix_tests" # Jump to fix_tests on failure

[[tasks]]
name = "fix_tests"
prompt = "Fix failing tests"
verify_command = "npm test"
on_success = "deploy"    # Continue to deploy after fixing
on_failure = "stop"      # Stop if tests can't be fixed
max_attempts = 1

[[tasks]]
name = "deploy"
prompt = "Deploy to staging environment"
verify_command = "curl -f http://staging.example.com/health"
on_success = "stop"      # All done!
on_failure = "rollback"  # Jump to rollback on failure

[[tasks]]
name = "rollback"
prompt = "Rollback the deployment"
verify_command = "curl -f http://staging.example.com/health"
on_success = "stop"
on_failure = "stop"
```

This creates a workflow where:
- Build failures jump to a fix task, then retry testing
- Test failures jump to a fix task, then continue to deployment
- Deployment failures trigger a rollback
- Tasks are skipped if not referenced in the flow

#### ⚠️ Avoiding Infinite Loops

When designing conditional workflows, be mindful of potential infinite loops:

**Bad Example (Infinite Loop):**
```toml
[[tasks]]
name = "task_a"
on_success = "task_b"

[[tasks]]
name = "task_b"
on_success = "task_a"  # Creates infinite loop!
```

**Good Example (With Exit Condition):**
```toml
[[tasks]]
name = "retry_task"
prompt = "Try to fix the issue"
verify_command = "test -f success_marker"
on_success = "next"       # Exit the loop on success
on_failure = "retry_task" # Retry on failure
max_attempts = 1          # Important: limits retries per execution
```

**Loop Protection:** By default, Prompter prevents infinite loops by tracking which tasks have been executed. If a task attempts to run twice in the same session, it will be skipped with a warning log.

**Allowing Infinite Loops:** For use cases like continuous monitoring or polling, you can enable infinite loops:

```toml
[settings]
allow_infinite_loops = true

[[tasks]]
name = "monitor"
prompt = "Check system status"
verify_command = "systemctl is-active myservice"
on_success = "wait"
on_failure = "alert"

[[tasks]]
name = "wait"
prompt = "Wait before next check"
verify_command = "sleep 60"
on_success = "monitor"  # Loop back to monitoring
```

When `allow_infinite_loops = true`, tasks can execute multiple times. A safety limit of 1000 iterations prevents runaway loops.

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
- `allow_infinite_loops`: Allow tasks to execute multiple times in the same run (default: false)

#### Task Fields
- `name` (required): Unique identifier for the task. Cannot use reserved words: `next`, `stop`, `retry`, `repeat`
- `prompt` (required): Instructions for Claude Code to execute
- `verify_command` (required): Shell command to verify task success
- `verify_success_code`: Expected exit code for success (default: 0)
- `on_success`: Action when task succeeds - `"next"`, `"stop"`, `"repeat"`, or any task name (default: "next")
- `on_failure`: Action when task fails - `"retry"`, `"stop"`, `"next"`, or any task name (default: "retry")
- `max_attempts`: Maximum retry attempts for this task (default: 3)
- `timeout`: Task timeout in seconds (optional, no timeout if not specified)

> **Note on Task Jumping:** When using task names in `on_success` or `on_failure`, ensure your workflow has exit conditions to prevent infinite loops. Prompter will skip tasks that have already executed to prevent infinite loops.

### Environment Variables

Prompter supports the following environment variables for additional configuration:

- `PROMPTER_INIT_TIMEOUT`: Sets the timeout (in seconds) for AI analysis during `--init` command (default: 120)
  ```bash
  # Increase timeout for large projects
  PROMPTER_INIT_TIMEOUT=300 prompter --init

  # Set a shorter timeout for smaller projects
  PROMPTER_INIT_TIMEOUT=60 prompter --init
  ```

## Examples and Templates

The project includes ready-to-use workflow templates in the `examples/` directory:

- **examples/bdd-workflow.toml**: Automated BDD scenario implementation
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

4. **"Unescaped '\' in a string"** - TOML parsing error with backslashes in strings
   - Solution: In TOML, backslashes must be escaped. Use one of these approaches:
     - Double backslashes: `path = "C:\\Users\\name\\project"`
     - Single quotes: `path = 'C:\Users\name\project'`
     - Triple quotes: `path = '''C:\Users\name\project'''`
   - The error message now shows the exact line and column with helpful context

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

```
╭───────────────────────────────╮
│   >  ───  • • •  ───  ✓       │
│   prompt  tasks  verify       │
╰───────────────────────────────╯
```
