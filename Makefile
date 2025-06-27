.PHONY: help install install-dev test test-unit test-integration test-slow test-fast coverage coverage-html coverage-unit lint type-check format format-check clean

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install the package with development dependencies
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests only (exclude integration and slow tests)
	pytest -m "not integration and not slow"

test-integration:  ## Run integration tests only
	pytest -m integration

test-slow:  ## Run slow tests only
	pytest -m slow

test-fast:  ## Run fast tests only (exclude slow tests)
	pytest -m "not slow"

coverage:  ## Run tests with coverage report
	pytest --cov=src/prompter --cov-report=term --cov-report=html --cov-report=xml

coverage-html:  ## Run tests with coverage and open HTML report
	pytest --cov=src/prompter --cov-report=html
	@echo "Opening coverage report in browser..."
	@python -m webbrowser htmlcov/index.html

coverage-report:  ## Show coverage report in terminal
	pytest --cov=src/prompter --cov-report=term-missing

coverage-unit:  ## Run unit tests with coverage (exclude integration and slow tests)
	pytest -m "not integration and not slow" --cov=src/prompter --cov-report=term-missing

lint:  ## Run linting checks
	ruff check .

type-check:  ## Run type checking
	mypy src/

format:  ## Format code
	ruff format .

format-check:  ## Check code formatting
	ruff format --check .

clean:  ## Clean build artifacts and coverage reports
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -f coverage.xml
	rm -f .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

all: lint format-check type-check test coverage  ## Run all checks and tests
