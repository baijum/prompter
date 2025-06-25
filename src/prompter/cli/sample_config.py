"""Sample configuration generation for the prompter tool."""

import sys
from pathlib import Path


def generate_sample_config(filename: str) -> None:
    """Generate a sample configuration file with examples and comments."""
    sample_config = """# Prompter Configuration File
# This file defines tasks for automated code tidying using Claude Code
# Each task runs a prompt against your codebase and verifies the result

[settings]
# Global settings for all tasks

# How long to wait (in seconds) between task execution attempts
check_interval = 3600  # 1 hour

# Maximum number of retries for failed tasks (can be overridden per task)
max_retries = 3

# Command to use for Claude Code (typically just "claude")
claude_command = "claude"

# Working directory for all operations (optional, defaults to current directory)
# working_directory = "/path/to/your/project"

# Common task patterns for code maintenance

# Task 1: Fix compilation errors and warnings
[[tasks]]
name = "fix_compiler_errors"
prompt = "Please fix all compilation errors and warnings in this codebase. Focus on resolving actual issues rather than just suppressing warnings. Ensure the code compiles cleanly."
verify_command = "make"  # Replace with your build command (e.g., "npm run build", "cargo build", "python -m py_compile .")
verify_success_code = 0
on_success = "next"      # Options: "next" (continue), "stop" (halt), "repeat" (run again)
on_failure = "retry"     # Options: "retry", "stop", "next"
max_attempts = 5
timeout = 7200           # 2 hours timeout for Claude execution

# Task 2: Code formatting and style cleanup
[[tasks]]
name = "format_code"
prompt = "Format all code in the project according to established style guidelines. Run any available formatters and ensure consistent code style throughout the codebase."
verify_command = "make lint"  # Replace with your linting command (e.g., "npm run lint", "ruff check .", "gofmt -d .")
verify_success_code = 0
on_success = "next"
on_failure = "retry"
max_attempts = 3

# Task 3: Update and improve documentation
[[tasks]]
name = "update_documentation"
prompt = "Review and update all code documentation, comments, and README files. Ensure all public APIs are properly documented and examples are current."
verify_command = "make docs"  # Replace with your documentation build command
verify_success_code = 0
on_success = "next"
on_failure = "next"      # Continue even if documentation build fails
max_attempts = 2

# Task 4: Test maintenance and coverage
[[tasks]]
name = "improve_tests"
prompt = "Review and improve the test suite. Add missing tests for new functionality, update outdated tests, and improve test coverage where needed."
verify_command = "make test"  # Replace with your test command (e.g., "npm test", "pytest", "go test ./...")
verify_success_code = 0
on_success = "next"
on_failure = "stop"      # Stop if tests can't be fixed
max_attempts = 3

# Task 5: Performance optimization
[[tasks]]
name = "optimize_performance"
prompt = "Analyze the codebase for performance improvements. Look for inefficient algorithms, unnecessary computations, and opportunities for optimization."
verify_command = "make benchmark"  # Replace with your performance test command
verify_success_code = 0
on_success = "next"
on_failure = "next"      # Continue even if benchmarks fail
max_attempts = 2

# Task 6: Security review
[[tasks]]
name = "security_review"
prompt = "Perform a security review of the codebase. Identify potential vulnerabilities, insecure patterns, and recommend fixes following security best practices."
verify_command = "make security-check"  # Replace with your security scanning command
verify_success_code = 0
on_success = "next"
on_failure = "next"      # Continue even if security check fails
max_attempts = 2

# Task 7: Dependency updates
[[tasks]]
name = "update_dependencies"
prompt = "Review and update project dependencies. Update to latest compatible versions, remove unused dependencies, and ensure all dependencies are secure."
verify_command = "make test"  # Verify updates don't break anything
verify_success_code = 0
on_success = "stop"      # Stop after successful dependency updates
on_failure = "stop"
max_attempts = 2

# Customization Tips:
# 1. Replace verify_command with commands appropriate for your project
# 2. Adjust prompts to match your specific coding standards and practices
# 3. Modify max_attempts based on task complexity
# 4. Use on_success/on_failure to control task flow
# 5. Set timeouts for long-running tasks
# 6. Add or remove tasks based on your maintenance needs

# Common verify_command examples:
# - Python: "python -m py_compile .", "pytest", "ruff check ."
# - JavaScript/Node: "npm run build", "npm test", "npm run lint"
# - Go: "go build ./...", "go test ./...", "gofmt -d ."
# - Rust: "cargo build", "cargo test", "cargo clippy"
# - C/C++: "make", "make test", "clang-format --dry-run *.c"
# - Java: "mvn compile", "mvn test", "mvn checkstyle:check"
"""

    config_path = Path(filename)
    if config_path.exists():
        response = input(f"File '{filename}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ("y", "yes"):
            print("Configuration generation cancelled.")
            return

    try:
        with open(config_path, "w") as f:
            f.write(sample_config)
        print(f"Sample configuration generated: {filename}")
        print("")
        print("Next steps:")
        print(f"1. Edit {filename} to match your project's build/test commands")
        print("2. Customize the prompts for your specific needs")
        print(f"3. Run: prompter {filename} --dry-run")
        print(f"4. When ready: prompter {filename}")
    except Exception as e:
        print(f"Error generating configuration: {e}", file=sys.stderr)
