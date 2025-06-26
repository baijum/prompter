# Contributing to Prompter

Thank you for your interest in contributing to Prompter! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Development Workflow](#development-workflow)
- [Release Process](#release-process)

## Code of Conduct

This project follows a standard code of conduct. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/baijum/prompter.git
   cd prompter
   ```
3. **Set up the development environment** (see below)
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Environment Setup

1. **Create and activate a virtual environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install the package with development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Verify the installation**:
   ```bash
   prompter --help
   pytest --version
   ruff --version
   mypy --version
   ```

## Running Tests

We maintain comprehensive test coverage with 101+ test cases.

### Basic Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/prompter --cov-report=term-missing

# Run tests with HTML coverage report
pytest --cov=src/prompter --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Test Categories

```bash
# Run only unit tests (excluding integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run specific test file
pytest tests/test_config.py

# Run tests matching a pattern
pytest -k "test_config"

# Run tests with verbose output
pytest -v
```

### Using Make Commands

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run tests with coverage
make coverage

# Generate and open HTML coverage report
make coverage-html

# Show coverage report in terminal with missing lines
make coverage-report
```

### Using Tox for Multi-Version Testing

```bash
# Test across all Python versions
tox

# Test specific Python version
tox -e py311

# Run linting
tox -e lint

# Run type checking
tox -e type

# Generate coverage report
tox -e coverage
```

## Code Quality

We maintain high code quality standards with automated tools.

### Linting and Formatting

```bash
# Run linting
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Format code
ruff format .

# Check formatting without changes
ruff format . --check
```

### Type Checking

```bash
# Run type checking
mypy src/

# Type check with strict settings
mypy --strict src/
```

### All Quality Checks

```bash
# Run all checks using Make
make lint        # Linting
make type-check  # Type checking
make format      # Code formatting
make all         # All checks + tests
```

## Making Changes

### Code Style Guidelines

1. **Follow PEP 8** - enforced by ruff
2. **Add type hints** - checked by mypy
3. **Write docstrings** for public functions and classes
4. **Keep functions focused** - single responsibility principle
5. **Use descriptive variable names**

### Testing Guidelines

1. **Write tests for all new features**
2. **Maintain or improve test coverage**
3. **Use the test helpers** in `tests/test_helpers.py`
4. **Follow existing test patterns**
5. **Test edge cases and error conditions**

### Test Structure

```python
# Example test structure
class TestFeatureName:
    """Tests for the feature name functionality."""
    
    def test_basic_functionality(self):
        """Test basic feature behavior."""
        # Arrange
        input_data = create_test_data()
        
        # Act
        result = feature_function(input_data)
        
        # Assert
        assert result.success is True
        assert result.output == expected_output
    
    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ExpectedException):
            feature_function(invalid_input)
```

### Adding New Features

1. **Write tests first** (TDD approach recommended)
2. **Implement the feature**
3. **Update documentation** if needed
4. **Add configuration examples** if applicable
5. **Test integration** with existing features

## Submitting Changes

### Pull Request Process

1. **Ensure all tests pass**:
   ```bash
   make all  # Runs tests, linting, and type checking
   ```

2. **Update version** if needed (for maintainers only)

3. **Write clear commit messages**:
   ```
   feat: add support for custom success codes
   
   - Allow tasks to specify custom exit codes for verification
   - Add verify_success_code configuration option
   - Update tests and documentation
   
   Fixes #123
   ```

4. **Create pull request** with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots if UI-related
   - Testing instructions

### Commit Message Format

Use conventional commits format:
- `feat:` - new features
- `fix:` - bug fixes
- `docs:` - documentation changes
- `test:` - adding or updating tests
- `refactor:` - code refactoring
- `style:` - formatting changes
- `ci:` - CI/CD changes

## Reporting Issues

### Bug Reports

Include in your bug report:
1. **Python version** and operating system
2. **Prompter version**: `pip show claude-code-prompter`
3. **Steps to reproduce** the issue
4. **Expected vs actual behavior**
5. **Error messages** or logs
6. **Configuration file** (sanitized)

### Feature Requests

Include in your feature request:
1. **Clear description** of the proposed feature
2. **Use case** - why is this needed?
3. **Proposed implementation** (if you have ideas)
4. **Examples** of how it would be used

### Configuration for Bug Reports

```toml
# Example configuration for bug reports
[settings]
working_directory = "/path/to/test/project"

[[tasks]]
name = "reproduce_bug"
prompt = "Minimal example that reproduces the issue"
verify_command = "echo 'test'"
# ... other relevant settings
```

## Development Workflow

### CI/CD Pipeline

Our GitHub Actions workflow:
1. **Tests** on Python 3.11 and 3.12
2. **Linting** with ruff
3. **Type checking** with mypy
4. **Coverage reporting** to Codecov
5. **Package building** and validation

### Local Development Loop

```bash
# 1. Make changes
vim src/prompter/feature.py

# 2. Run tests
pytest tests/test_feature.py -v

# 3. Check code quality
make lint
make type-check

# 4. Run all tests
make test

# 5. Commit changes
git add .
git commit -m "feat: implement new feature"
```

### Debugging Tips

```bash
# Run with verbose output
prompter config.toml --verbose

# Enable debug logging
prompter config.toml --log-file debug.log

# Use dry run for testing
prompter config.toml --dry-run

# Check current state
prompter --status
```

### Environment Variables

Prompter supports the following environment variables:

```bash
# Set timeout for AI analysis during --init (default: 120 seconds)
PROMPTER_INIT_TIMEOUT=300 prompter --init

# Example: Quick timeout for testing
PROMPTER_INIT_TIMEOUT=30 prompter --init
```

## Project Structure

```
prompter/
├── src/prompter/          # Main package
│   ├── __init__.py
│   ├── cli.py             # CLI wrapper (for compatibility)
│   ├── cli/               # CLI module package
│   │   ├── __init__.py
│   │   ├── arguments.py   # CLI argument parsing
│   │   ├── main.py        # Main orchestration logic
│   │   ├── sample_config.py # Sample configuration generation
│   │   └── status.py      # Status display functionality
│   ├── config.py          # Configuration parsing
│   ├── runner.py          # Task execution with Claude SDK
│   ├── state.py           # State management
│   └── logging.py         # Logging setup
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py        # pytest configuration
│   ├── test_cli.py        # CLI tests
│   ├── test_config.py     # Configuration tests
│   ├── test_runner.py     # Runner tests
│   ├── test_state.py      # State management tests
│   ├── test_logging.py    # Logging tests
│   ├── test_integration.py # End-to-end tests
│   └── test_helpers.py    # Test utilities
├── examples/              # Example configurations
│   ├── README.md          # Examples documentation
│   ├── bdd-workflow.toml  # BDD automation example
│   ├── refactor-codebase.toml # Refactoring example
│   └── security-audit.toml # Security scanning example
├── .github/               # GitHub specific files
│   ├── workflows/         # CI/CD pipelines
│   │   ├── ci.yml         # Continuous integration
│   │   └── publish.yml    # PyPI publishing
│   └── RELEASE_TEMPLATE.md # Release checklist template
├── pyproject.toml         # Project configuration
├── README.md              # User documentation
├── CONTRIBUTING.md        # This file
├── RELEASING.md           # Release process guide
├── CHANGELOG.md           # Version history
├── CLAUDE.md              # AI assistant instructions
└── PROMPTER_SYSTEM_PROMPT.md # System prompt for AI tools
```

## Release Process

For maintainers creating a new release:

1. **Follow the release guide**: See [RELEASING.md](RELEASING.md) for detailed instructions
2. **Version bump**: Update version in `pyproject.toml`
3. **Update CHANGELOG.md**: Document all changes
4. **Run quality checks**: Ensure `make all` passes
5. **Create release**: Use git tags and GitHub releases
6. **Publish to PyPI**: Follow the publishing steps

### Quick Release Commands

```bash
# Prepare release
make all                                    # Run all checks
git add pyproject.toml CHANGELOG.md
git commit -m "Release v0.x.x - Description"
git tag -a v0.x.x -m "Release v0.x.x"

# Push and create GitHub release
git push origin v0.x.x
gh release create v0.x.x --title "..." --notes "..."

# Publish to PyPI
python -m build
python -m twine upload dist/*
```

For the complete release process, including checklists and troubleshooting, see [RELEASING.md](RELEASING.md).

## Getting Help

- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Code Review**: Maintainers will review pull requests

Thank you for contributing to Prompter! 🚀