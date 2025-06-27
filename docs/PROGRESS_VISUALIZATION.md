# Progress Visualization

Prompter provides real-time progress visualization for parallel task execution, helping you monitor the status of complex workflows with multiple dependencies.

## Overview

The progress visualization system offers three display modes:

1. **Rich Mode** - Full terminal UI with live updates, progress bars, and task status
2. **Simple Mode** - Basic text output suitable for CI/CD environments
3. **None Mode** - No progress output (silent operation)

## Display Modes

### Rich Mode (Default)

When running in a terminal that supports rich output, you'll see:

- Real-time task status updates
- Progress bars for running tasks
- Task dependencies and waiting states
- Overall workflow progress and ETA
- Execution time tracking

```bash
# Rich mode is automatically selected when supported
prompter config.toml
```

### Simple Mode

For environments that don't support rich terminal UI (CI/CD, basic terminals), simple mode provides:

- Timestamped status updates
- ASCII progress indicators
- Final execution summary
- Failed task details

```bash
# Force simple mode
prompter config.toml --simple-progress

# Output example:
14:23:15 [>] build_frontend: Starting...
14:23:16 [>] build_backend: [##########----------] 50% - Compiling modules
14:23:18 [+] build_frontend: Completed (00:03)
14:23:20 [+] build_backend: Completed (00:04)
```

### No Progress Mode

For scripts and automation where progress output isn't needed:

```bash
# Disable all progress output
prompter config.toml --no-progress
```

## Command Line Options

```bash
# Use default progress display (auto-detects terminal capabilities)
prompter config.toml

# Force simple progress mode
prompter config.toml --simple-progress

# Disable progress display entirely
prompter config.toml --no-progress
```

## Environment Variables

### Force Display Mode

You can override the automatic display mode detection:

```bash
# Force rich display (even in CI)
export PROMPTER_PROGRESS_MODE=rich

# Force simple display
export PROMPTER_PROGRESS_MODE=simple

# Disable all progress
export PROMPTER_PROGRESS_MODE=none
```

### CI/CD Detection

The following CI environment variables are automatically detected, causing fallback to simple mode:

- `CI`
- `GITHUB_ACTIONS`
- `GITLAB_CI`
- `CIRCLECI`
- `TRAVIS`
- `JENKINS_URL`
- `TEAMCITY_VERSION`
- `BUILDKITE`
- And many more...

## Configuration Examples

### Basic Parallel Execution

```toml
# Enable parallel execution in your config
[settings]
enable_parallel = true
max_parallel_tasks = 4

[[tasks]]
name = "frontend_build"
prompt = "Build the frontend application"
verify_command = "test -f dist/index.html"

[[tasks]]
name = "backend_build"
prompt = "Build the backend services"
verify_command = "test -f build/server.jar"

[[tasks]]
name = "deploy"
prompt = "Deploy the application"
depends_on = ["frontend_build", "backend_build"]
verify_command = "curl -s http://localhost:8080/health"
```

### Complex Dependency Graph

```toml
[settings]
enable_parallel = true
max_parallel_tasks = 6

# Data processing pipeline with visualization
[[tasks]]
name = "fetch_data"
prompt = "Fetch latest data from API"
verify_command = "test -f data/raw.json"

[[tasks]]
name = "validate_data"
prompt = "Validate data integrity"
depends_on = ["fetch_data"]
verify_command = "python validate.py"

[[tasks]]
name = "transform_data"
prompt = "Transform data to analysis format"
depends_on = ["validate_data"]
verify_command = "test -f data/transformed.parquet"

[[tasks]]
name = "analyze_metrics"
prompt = "Run statistical analysis"
depends_on = ["transform_data"]
verify_command = "test -f reports/metrics.json"

[[tasks]]
name = "generate_visualizations"
prompt = "Create data visualizations"
depends_on = ["transform_data"]
verify_command = "test -d reports/charts/"

[[tasks]]
name = "compile_report"
prompt = "Generate final report"
depends_on = ["analyze_metrics", "generate_visualizations"]
verify_command = "test -f reports/final_report.pdf"
```

## Terminal Compatibility

### Supported Terminals

Rich mode works best with:
- Modern terminal emulators (iTerm2, Terminal.app, GNOME Terminal, etc.)
- Windows Terminal
- VS Code integrated terminal
- Most Linux/macOS terminals with TERM set properly

### Automatic Fallback

The system automatically falls back to simple mode when:
- Running in CI/CD environments
- Terminal doesn't support ANSI escape codes
- TERM is set to "dumb" or "unknown"
- stdout is not a TTY (piped output)

### Windows Support

On Windows, the progress display:
- Automatically detects Windows Terminal for rich mode
- Falls back to simple mode on legacy consoles
- Works with colorama if installed

## Integration with Workflows

### GitHub Actions Example

```yaml
name: Build and Test
on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run prompter tasks
        run: |
          # Progress automatically uses simple mode in GitHub Actions
          prompter build-tasks.toml

      - name: Run with custom progress mode
        run: |
          # Force no progress for cleaner logs
          prompter build-tasks.toml --no-progress
```

### Docker Integration

```dockerfile
FROM python:3.11

# Install prompter
RUN pip install claude-code-prompter

# Copy configuration
COPY prompter.toml .

# Progress automatically uses simple mode in Docker
CMD ["prompter", "prompter.toml"]
```

### Shell Scripts

```bash
#!/bin/bash

# Detect if running interactively
if [ -t 1 ]; then
    # Terminal attached - use default (rich) mode
    prompter tasks.toml
else
    # No terminal - use simple mode
    prompter tasks.toml --simple-progress
fi
```

## Best Practices

1. **Let auto-detection work**: The default behavior usually selects the right mode
2. **Use simple mode in CI/CD**: It's automatically selected, but you can force it with `--simple-progress`
3. **Disable for parsing**: Use `--no-progress` when parsing output programmatically
4. **Test different modes**: Use environment variables to test how your workflow looks in different modes

## Troubleshooting

### Rich mode not working?

Check if your terminal is detected correctly:
```bash
# Force rich mode to test
export PROMPTER_PROGRESS_MODE=rich
prompter config.toml
```

### Progress interfering with logs?

Use simple or none mode:
```bash
# Simple timestamps only
prompter config.toml --simple-progress

# No progress at all
prompter config.toml --no-progress
```

### CI/CD output looks garbled?

The system should auto-detect CI, but you can force simple mode:
```bash
# In your CI configuration
prompter config.toml --simple-progress
```
