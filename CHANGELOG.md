# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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