# Prompter Examples

This directory contains example TOML configurations demonstrating various use cases for the prompter tool.

## Available Examples

### 1. [bdd-workflow.toml](bdd-workflow.toml)
**Behavior-Driven Development Workflow**
- Automatically finds and implements @wip scenarios
- Runs tests and fixes failures
- Ensures all tests pass before committing

### 2. [refactor-codebase.toml](refactor-codebase.toml)
**Automated Code Refactoring**
- Analyzes code for refactoring opportunities
- Extracts duplicate code
- Simplifies complex functions
- Maintains test coverage throughout

### 3. [security-audit.toml](security-audit.toml)
**Security Scanning and Remediation**
- Scans for vulnerable dependencies
- Identifies code security issues
- Implements fixes automatically
- Maintains functionality with tests

## Getting Started with AI

The easiest way to create a configuration is to let AI analyze your project:

```bash
# Let AI analyze your project and generate a custom configuration
prompter --init

# Generate for a specific language
prompter --init --language python

# Use non-interactive mode
prompter --init --yes
```

This will create a `prompter.toml` file tailored to your project's specific needs.

## Creating Your Own Workflows

When creating TOML configurations manually, remember:

1. **Break Down Complex Tasks**: Avoid large prompts that might trigger JSON parsing errors
2. **Use Meaningful Names**: Task names should clearly indicate what they do
3. **Verify Everything**: Each task needs a `verify_command` that actually tests success
4. **Handle Failures Gracefully**: Use `on_failure = "next"` for diagnostic tasks

## System Prompt for AI Assistance

See [PROMPTER_SYSTEM_PROMPT.md](../PROMPTER_SYSTEM_PROMPT.md) for a comprehensive guide that can help AI assistants generate effective TOML configurations.

## Common Patterns

### Linear Workflow
```toml
on_success = "next"
on_failure = "retry"
```

### Diagnostic Flow
```toml
on_success = "next"
on_failure = "next"  # Continue regardless
```

### Critical Task
```toml
on_success = "next"
on_failure = "stop"  # Don't proceed if this fails
```

## Tips

1. **Start Small**: Test with `--dry-run` first
2. **Use Debug Mode**: Run with `--debug` to see detailed execution logs
3. **Save Logs**: Use `--log-file` to capture output for debugging
4. **Resume Interrupted Work**: Prompter saves state automatically

## Customization

All examples use placeholder commands like `./run-tests.sh` or `pytest`. Update these to match your project:

- `pytest` → `npm test`, `go test`, `cargo test`, etc.
- `ruff` → `flake8`, `eslint`, `rubocop`, etc.
- `mypy` → `tsc`, `flow`, etc.

## Contributing

Have a useful workflow? Consider contributing it as an example! Make sure to:
1. Include clear documentation
2. Use generic commands where possible
3. Explain any project-specific assumptions
4. Test the workflow before submitting