# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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