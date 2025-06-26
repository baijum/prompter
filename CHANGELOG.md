# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2025-06-27

### 🚀 New Features

- **Task-Specific System Prompts**
  - New `system_prompt` task configuration option allows customizing Claude's behavior for individual tasks
  - Enables enforcing planning before execution, setting expertise context, and adding safety constraints
  - Particularly powerful for critical operations, complex refactoring, and multi-phase workflows
  - Can be combined with `resume_previous_session` for context-aware, role-specific task execution
  - Example use cases:
    - Enforce detailed planning before making changes
    - Set Claude as a domain expert (security, database, performance, etc.)
    - Add safety constraints for production deployments
    - Control output style and approach for different tasks

### 🔧 Configuration

- **New Task Option: `system_prompt`**
  - Optional string that customizes Claude's behavior for the specific task
  - When not specified, Claude uses its default behavior
  - Example configuration:
    ```toml
    [[tasks]]
    name = "careful_refactor"
    prompt = "Refactor the payment processing module"
    system_prompt = "You are a senior engineer working on payment systems. Safety is paramount. Before making ANY changes, create a detailed plan including: 1) What will be changed, 2) Potential risks, 3) How to test each change. Present the plan and wait for approval."
    verify_command = "python -m pytest tests/payment/"
    ```

### 📚 Documentation

- Added comprehensive documentation section on system prompts with common patterns
- Created three new example workflows:
  - `planning-workflow.toml` - Demonstrates enforcing planning before implementation
  - `safe-production-deploy.toml` - Shows safety-critical deployment with multiple system prompts
  - `code-review-workflow.toml` - Multi-perspective automated code review
- Updated CLAUDE.md with system prompt behavior documentation

## [0.8.0] - 2025-06-27

### 🚀 New Features

- **Claude Session Resumption for Context Preservation**
  - New `resume_previous_session` task configuration option enables maintaining full context across tasks
  - Tasks can now preserve Claude's entire conversation history from previous task executions
  - Allows building complex, context-aware workflows where later tasks can reference and build upon earlier results
  - Maintains Claude's understanding of the codebase, modifications made, and project structure
  - Particularly useful for multi-step refactoring, progressive code improvements, and iterative development workflows

### 🔧 Configuration

- **New Task Option: `resume_previous_session`**
  - Boolean option (default: `false`) that controls whether to resume the previous Claude session
  - When `true`, the task starts with the full conversation history from the previous task
  - Example configuration:
    ```toml
    [[tasks]]
    name = "analyze_code"
    prompt = "Analyze the codebase for potential improvements"
    verify_command = "echo 'Analysis complete'"

    [[tasks]]
    name = "implement_improvements"
    prompt = "Based on your analysis, implement the top 3 improvements"
    resume_previous_session = true
    verify_command = "python -m pytest"
    ```

### 📚 Documentation

- Updated configuration documentation to explain session resumption feature
- Added examples demonstrating context-aware task workflows
- Enhanced best practices guide for using session resumption effectively

## [0.7.5] - 2025-06-26

### ✨ New Features

- **Added `--version` CLI flag**
  - Users can now check the installed version with `prompter --version`
  - The `__version__` variable in `__init__.py` now has a practical purpose

### 🔧 Developer Experience

- **Version synchronization enforcement**
  - Added automated script to check version consistency between `pyproject.toml` and `__init__.py`
  - Version sync check integrated into GitHub Actions CI/CD pipelines
  - Pre-commit hook ensures versions stay synchronized during development

- **Pre-commit hooks setup**
  - Added comprehensive pre-commit configuration for code quality
  - Includes ruff linting/formatting, YAML/TOML validation, trailing whitespace removal
  - Added `pre-commit` to dev dependencies for easy setup

### 📚 Documentation

- **Enhanced developer documentation**
  - Added CI/CD pipeline details to CONTRIBUTING.md
  - Documented pre-commit setup and usage
  - Moved development-related content from README.md to CONTRIBUTING.md

### 🐛 Bug Fixes

- **Fixed subprocess security warning**
  - Added S603 to ruff ignore list for legitimate subprocess usage from config files
  - Commands from TOML configs are properly sanitized with `shlex.split()`

## [0.7.4] - 2025-06-26

### 🐛 Bug Fixes

- **Fixed version mismatch between `__init__.py` and `pyproject.toml`**
  - Both files now correctly show the same version number
  - Added mandatory check in CLAUDE.md to prevent future mismatches

- **Removed broken import in `cli.py`**
  - Removed import of non-existent `generate_sample_config` function
  - This was causing ImportError when using the CLI module directly

- **Fixed shell injection vulnerability**
  - Replaced `shell=True` with `shlex.split()` for safer command execution
  - Verification commands are now properly parsed to prevent injection attacks

### 🔧 Code Quality Improvements

- **Major code refactoring**
  - Split 258-line `main()` function into 7 focused, testable functions
  - Removed dead code: unused `TaskRunner.run_all_tasks()` method
  - Fixed `locals()` anti-pattern by properly initializing variables
  - Added missing type hints to all `__init__` methods

- **Created constants module**
  - Extracted magic numbers (timeouts, limits) to `constants.py`
  - Improved maintainability and configurability

- **Enhanced test coverage**
  - Added comprehensive tests for `resource_loader.py` module
  - Overall test coverage increased to 84.35%

### 📚 Documentation

- Added mandatory rule in CLAUDE.md to ensure version synchronization during releases

## [0.7.3] - 2025-06-26

### 🐛 Bug Fixes

- **Fixed `prompter --init` hanging issue**
  - Removed incorrect monkey patch that was causing TaskGroup errors with Claude Code SDK
  - The monkey patch was incorrectly replacing `open_process` with `run_process` which are incompatible

- **Improved `--init` command performance**
  - Simplified AI analysis prompt to reduce response time significantly
  - Added key project files detection to provide context without full directory scan
  - Removed large system prompt that was causing excessive delays
  - Analysis now completes in seconds rather than timing out

- **Enhanced error handling and debugging**
  - Added detailed logging for Claude SDK interactions
  - Improved error messages to help diagnose SDK issues
  - Better handling of TaskGroup exceptions from the SDK

### 🔧 Code Quality

- Fixed all linting errors and improved code style
- Added missing newline at end of `__main__.py`
- Improved async event loop handling using `asyncio.run()`

## [0.7.2] - 2025-06-26

### 🐛 Bug Fixes

- Added configurable timeout for `--init` command via `PROMPTER_INIT_TIMEOUT` environment variable
- Improved error message to guide users when AI analysis times out
- Fixed hardcoded 30-second timeout that was too short for larger projects

### 📚 Documentation

- Removed unimplemented CLI options (`--language`, `--yes`, `--working-dir`) from documentation
- Added environment variable documentation across all docs
- Clarified that only `--init` and `--init <filename>` options are currently supported

## [0.7.1] - 2025-06-26

### 🐛 Bug Fixes

- Added missing `pytest-asyncio` dependency to fix CI test failures
- Configured pytest with `asyncio_mode = auto` for proper async test support
- Added asyncio marker to pytest configuration

### 📚 Documentation

- Updated documentation to properly showcase AI-powered --init features
- Enhanced README with comprehensive AI analysis section
- Updated examples documentation with AI initialization guidance

## [0.7.0] - 2025-06-26

### 🚀 New Features

- **AI-Powered Project Analysis with --init**
  - New `prompter --init` command that uses Claude to analyze your project
  - Automatically detects project language, tools, and structure
  - Identifies improvement opportunities (tests, linting, security, etc.)
  - Generates customized TOML configurations based on project needs
  - Interactive mode to confirm and refine AI suggestions
  - Support for multiple language-specific templates

### 🛡️ Improvements

- **Enhanced System Prompt**
  - Added strict task length constraints (7 lines max per prompt)
  - Added atomic task design examples with BAD vs GOOD patterns
  - Made verification speed requirement explicit (<5 seconds)
  - Added forbidden patterns section to prevent common mistakes
  - Added BDD workflow example for behavior-driven development
  - Added rollback option for destructive operations
  - Strengthened configuration priorities and safety guidelines

### 🐛 Bug Fixes

- Fixed importlib.resources deprecation warning by migrating to files() API
- Fixed RuntimeWarning in tests by properly handling async iterators
- Removed problematic TaskResult import to avoid async warnings

### 📚 Documentation

- Updated CLAUDE.md with mandatory date command rule
- Enhanced system prompt documentation with clearer constraints
- Added comprehensive examples for atomic task design

## [0.6.0] - 2025-01-26

### 🚀 New Features

- **Task Jumping and Conditional Workflows**
  - Tasks can now jump to specific tasks by name in `on_success` and `on_failure`
  - Reserved action words (`next`, `stop`, `retry`, `repeat`) cannot be used as task names
  - Enables complex conditional workflows and error handling paths
  - Built-in infinite loop protection: tasks are automatically skipped if they attempt to execute twice
  - New `allow_infinite_loops` setting to explicitly allow loops for monitoring/polling use cases
  - Safety limit of 1000 iterations even when infinite loops are allowed
  - Example: `on_success = "deploy"` jumps to the "deploy" task

### 🚀 Improvements

- **Enhanced TOML parsing error messages**
  - Error messages now show the exact line and column where the error occurred
  - Displays context with surrounding lines and a visual pointer to the problem
  - Provides helpful hints for common errors (e.g., unescaped backslashes)
  - Suggests alternative syntax options (single quotes, triple quotes) for file paths

### 📚 Documentation

- Added troubleshooting entry for TOML backslash escaping errors in README.md
- Added examples of task jumping and conditional workflows
- Updated configuration reference to document task name restrictions
- Added comprehensive warnings about infinite loop prevention
- Created examples for continuous monitoring with `allow_infinite_loops`

## [0.5.0] - 2025-01-26

### 🚀 Initial Release of Task Jumping Feature

- Basic implementation of task jumping functionality
- Initial documentation updates

## [0.4.4] - 2025-06-26

### 📚 Documentation

- Fixed incorrect repository URL in CONTRIBUTING.md
- Refactored PROMPTER_SYSTEM_PROMPT.md for improved clarity and better workflow guidance

### 🧹 Maintenance

- Fixed resource warnings in logging module by properly closing file handlers before removal
- Improved test stability by addressing file handle cleanup

## [0.4.3] - 2025-01-26

### 🚀 Added

- **Timeout functionality for Claude Code execution**
  - Tasks can now specify an optional `timeout` parameter in seconds
  - When timeout is specified, Claude Code execution stops after the given time
  - When timeout is not specified, Claude Code runs without any time limit
  - Timeouts integrate with retry logic - failed attempts due to timeout count towards `max_attempts`
  - Uses `asyncio.wait_for()` for reliable timeout enforcement

### 📚 Documentation

- **Enhanced timeout documentation**
  - Added comprehensive timeout behavior section to CLAUDE.md with examples
  - Updated README.md configuration reference to clarify timeout behavior
  - Added examples showing tasks with and without timeout
  - Updated PROMPTER_SYSTEM_PROMPT.md to clarify timeout is optional

### 🧪 Testing

- **Added comprehensive timeout tests**
  - Test for asyncio.TimeoutError handling
  - Test for execution without timeout specified
  - Test for successful execution with timeout
  - Test for multiple timeout attempts with retry logic

## [0.4.2] - 2025-01-26

### 🧹 Maintenance

- **Fixed linting and type checking issues**
  - Reorganized imports in `runner.py` to comply with ruff's import order rules
  - Added proper type ignore and noqa comments for the claude-code-sdk monkey patch
  - Ensures all quality checks pass (ruff, mypy, pytest) for cleaner development experience

## [0.4.1] - 2025-01-25

### 🐛 Fixed

- **Added monkey patch for claude-code-sdk subprocess issue**
  - Temporarily patches `anyio.open_process` to use `anyio.run_process`
  - Works around issue [#32](https://github.com/anthropics/claude-code-sdk-python/issues/32) in claude-code-sdk-python
  - This patch will be removed once the upstream issue is resolved

## [0.4.0] - 2025-01-25

### 🚀 Added

- **Comprehensive example configurations** for real-world use cases
  - Security audit workflow for identifying vulnerabilities
  - Codebase refactoring workflow for modernization
  - BDD workflow for test-driven development
  - Detailed README with usage patterns and best practices

- **Advanced system prompt** (`PROMPTER_SYSTEM_PROMPT.md`)
  - Comprehensive guidance for Claude Code interactions
  - Built-in safety checks and verification patterns
  - Task-specific strategies for different code operations
  - Best practices for large-scale code transformations

### 📚 Documentation

- **Enhanced README** with quick start guide and resource links
- **Example workflows** with detailed comments and explanations
- **System prompt documentation** for advanced customization

### 🔧 Improved

- Better project documentation structure
- More intuitive examples for common use cases
- Enhanced configuration templates

## [0.3.0] - 2025-01-25

### 🚀 Added

- **Extensive diagnostic logging with `--debug` flag**
  - New `-d/--debug` flag enables comprehensive diagnostic logging throughout the codebase
  - Extended log formatter shows timestamps with milliseconds, process/thread IDs, file locations, and function names
  - Detailed logging for Claude SDK interactions including execution timing and message processing
  - State transition logging for tracking task progress and file operations
  - Configuration parsing and validation logging with detailed error information
  - Execution flow tracking in main CLI for better debugging
  - Support for saving logs to file with `--log-file` option
  - Helps diagnose complex issues like TaskGroup errors by providing detailed diagnostic information

### 🔧 Improved

- **Enhanced logging infrastructure**
  - Debug mode automatically enables debug logging for Claude SDK operations
  - Proper use of `logger.exception()` for better error tracking
  - Contextual logging throughout all major components
  - Performance timing for Claude SDK and verification command execution

### 🧹 Maintenance

- Updated all logging calls to follow best practices
- Fixed linting issues related to logging
- All 107 tests continue to pass with 90.77% code coverage

## [0.2.1] - 2025-01-25

### 🐛 Fixed

- **Removed deprecated `claude_command` configuration**
  - The `claude_command` setting is no longer needed since the tool uses the Claude Code Python SDK directly
  - Removed all references from configuration files, sample configs, and test files
  - This cleanup improves clarity and prevents confusion about the SDK-based architecture

### 🧹 Maintenance

- Cleaned up legacy configuration options
- Simplified configuration structure
- All 107 tests continue to pass

## [0.2.0] - 2025-01-25

### 🚀 Added

- **New `--init` command** for generating sample configuration files
  - Creates comprehensive TOML configuration with examples and detailed comments
  - Supports custom filenames: `prompter --init my-config.toml`
  - Default filename: `prompter --init` creates `prompter.toml`
  - Includes examples for multiple programming languages (Python, JavaScript, Go, Rust, C/C++, Java)
  - Built-in overwrite protection with user confirmation
  - Provides clear next-steps guidance after generation

- **Enhanced CI/CD pipeline** with format checking
  - Added `ruff format --check` to GitHub Actions workflow
  - New `make format-check` target for local development
  - Updated `make all` to include format validation

### 🔧 Improved

- **Major CLI module refactoring** for better maintainability
  - Split monolithic 364-line `cli.py` into organized package structure:
    - `cli/arguments.py` - CLI argument parsing (79 lines)
    - `cli/sample_config.py` - Sample configuration generation (136 lines)
    - `cli/status.py` - Status display functionality (22 lines)
    - `cli/main.py` - Main orchestration logic (141 lines)
  - Maintained full backward compatibility with thin wrapper
  - Improved code organization with single responsibility principle
  - Enhanced testability with isolated components

- **Comprehensive test coverage** for new functionality
  - Added 6 new tests for `--init` functionality
  - All 107 tests passing with 91.87% code coverage
  - Updated test import paths for new module structure

### 📚 Documentation

- **Enhanced CLI help** with `--init` examples
- **Improved code organization** with better separation of concerns
- **Comprehensive sample configurations** with practical examples

### 🛠️ Development

- **Better code maintainability** through modular architecture
- **Improved developer experience** with enhanced Makefile targets
- **Stronger quality assurance** with format checking in CI

### 🔄 Migration Guide

This release is fully backward compatible. No changes required for existing usage.

The new `--init` command provides an easy way for new users to get started:

```bash
# Generate a sample configuration file
prompter --init

# Or with a custom name
prompter --init my-project.toml
```

---

## [0.1.5] - 2024-12-XX

### Added
- Improved documentation for PyPI and contributors

### Fixed
- Codecov rate limiting issues

## [0.1.4] - 2024-12-XX

### Fixed
- Codecov integration and rate limiting

## [0.1.3] - 2024-12-XX

### Fixed
- Code formatting improvements

## [0.1.2] - 2024-12-XX

### Added
- Version bump and stability improvements

## [0.1.1] - 2024-12-XX

### Fixed
- Linting issues and code quality improvements

## [0.1.0] - 2024-12-XX

### Added
- Initial release of claude-code-prompter
- Core functionality for running prompts sequentially
- TOML configuration support
- Task state management
- Dry run mode
- Claude Code SDK integration
