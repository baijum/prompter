"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Sample configuration data for testing."""
    return {
        "settings": {
            "check_interval": 3600,
            "max_retries": 3,
            "claude_command": "claude",
        },
        "tasks": [
            {
                "name": "test_task_1",
                "prompt": "Fix all warnings",
                "verify_command": "make",
                "verify_success_code": 0,
                "on_success": "next",
                "on_failure": "retry",
                "max_attempts": 3,
            },
            {
                "name": "test_task_2",
                "prompt": "Update documentation",
                "verify_command": "make docs",
                "verify_success_code": 0,
                "on_success": "stop",
                "on_failure": "next",
                "max_attempts": 2,
                "timeout": 600,
            },
        ],
    }


@pytest.fixture
def sample_toml_config(temp_dir, sample_config) -> Path:
    """Create a sample TOML configuration file."""
    config_content = """[settings]
check_interval = 3600
max_retries = 3
claude_command = "claude"

[[tasks]]
name = "test_task_1"
prompt = "Fix all warnings"
verify_command = "make"
verify_success_code = 0
on_success = "next"
on_failure = "retry"
max_attempts = 3

[[tasks]]
name = "test_task_2"
prompt = "Update documentation"
verify_command = "make docs"
verify_success_code = 0
on_success = "stop"
on_failure = "next"
max_attempts = 2
timeout = 600
"""

    config_file = temp_dir / "config.toml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def invalid_toml_config(temp_dir) -> Path:
    """Create an invalid TOML configuration file."""
    config_content = """[settings]
check_interval = 3600

[[tasks]]
# Missing required fields
name = "incomplete_task"
"""
    config_file = temp_dir / "invalid_config.toml"
    config_file.write_text(config_content)
    return config_file
