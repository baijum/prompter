"""Resource loading utilities for accessing bundled resources."""

import importlib.resources


def get_system_prompt() -> str:
    """Get the system prompt for AI analysis.

    Returns:
        The system prompt content.
    """
    try:
        # Try to load from bundled resources
        files = importlib.resources.files("prompter.resources")
        return (files / "PROMPTER_SYSTEM_PROMPT.md").read_text()
    except (FileNotFoundError, ModuleNotFoundError):
        # Fallback to basic prompt if resource not found
        return _get_fallback_system_prompt()


def get_example_config(language: str) -> str | None:
    """Get example configuration for a specific language.

    Args:
        language: Programming language name (e.g., "python", "javascript")

    Returns:
        Example configuration content, or None if not found.
    """
    try:
        filename = f"{language.lower()}_example.toml"
        files = importlib.resources.files("prompter.resources.examples")
        return (files / filename).read_text()
    except (FileNotFoundError, ModuleNotFoundError):
        return None


def list_available_examples() -> list[str]:
    """List all available example configurations.

    Returns:
        List of available language examples.
    """
    try:
        # List all files in examples directory
        examples = []
        for file in importlib.resources.files("prompter.resources.examples").iterdir():
            if file.name.endswith("_example.toml"):
                language = file.name.replace("_example.toml", "")
                examples.append(language)
        return sorted(examples)
    except (AttributeError, ModuleNotFoundError):
        return []


def get_workflow_examples() -> dict[str, str]:
    """Get workflow examples to include in prompts.

    Returns:
        Dictionary mapping workflow names to example content.
    """
    examples = {}

    # Define key example snippets that demonstrate various patterns
    examples["basic_workflow"] = """
# Basic linear workflow example
[[tasks]]
name = "run_tests"
prompt = "Run all tests and report any failures"
verify_command = "pytest"
on_success = "next"
on_failure = "fix_test_failures"

[[tasks]]
name = "fix_test_failures"
prompt = "Analyze and fix failing tests"
verify_command = "pytest"
on_success = "next"
on_failure = "stop"
max_attempts = 3
"""

    examples["conditional_workflow"] = """
# Conditional workflow with task jumping
[[tasks]]
name = "check_environment"
prompt = "Check if development environment is properly configured"
verify_command = "which python && which pip"
on_success = "run_linter"
on_failure = "setup_environment"

[[tasks]]
name = "setup_environment"
prompt = "Install missing development tools"
verify_command = "pip install -r requirements-dev.txt"
on_success = "run_linter"
on_failure = "stop"
"""

    examples["security_workflow"] = """
# Security scanning workflow
[[tasks]]
name = "security_scan"
prompt = "Scan for security vulnerabilities in dependencies"
verify_command = "safety check || pip-audit"
on_success = "next"
on_failure = "fix_vulnerabilities"
timeout = 300

[[tasks]]
name = "fix_vulnerabilities"
prompt = "Update vulnerable dependencies to secure versions"
verify_command = "safety check"
on_success = "next"
on_failure = "document_issues"
max_attempts = 2
"""

    return examples


def _get_fallback_system_prompt() -> str:
    """Get a basic fallback system prompt."""
    return """You are an AI assistant helping to analyze a software project and generate
a configuration file for the prompter tool. Your goal is to:

1. Identify the project's primary language
2. Detect build systems, test frameworks, and linters
3. Find areas that could benefit from automated code maintenance
4. Generate specific, actionable tasks for the prompter tool

Be thorough but concise in your analysis."""
