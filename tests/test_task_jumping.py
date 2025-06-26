"""Tests for task jumping functionality."""

from prompter.config import RESERVED_ACTIONS, PrompterConfig


class TestTaskJumping:
    """Test task jumping functionality."""

    def test_reserved_words_validation(self, temp_dir):
        """Test that reserved words cannot be used as task names."""
        for reserved_word in RESERVED_ACTIONS:
            config_content = f"""[[tasks]]
name = "{reserved_word}"
prompt = "Test task"
verify_command = "echo ok"
"""
            config_file = temp_dir / f"reserved_{reserved_word}.toml"
            config_file.write_text(config_content)

            config = PrompterConfig(config_file)
            errors = config.validate()

            assert len(errors) > 0
            assert any(
                f"name '{reserved_word}' is a reserved word" in error
                for error in errors
            )

    def test_task_jump_on_success(self, temp_dir):
        """Test jumping to a specific task on success."""
        config_content = """[[tasks]]
name = "task1"
prompt = "First task"
verify_command = "true"
on_success = "task3"

[[tasks]]
name = "task2"
prompt = "Second task"
verify_command = "true"

[[tasks]]
name = "task3"
prompt = "Third task"
verify_command = "true"
"""
        config_file = temp_dir / "jump_success.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        errors = config.validate()

        # Should be valid
        assert len(errors) == 0
        assert config.tasks[0].on_success == "task3"

    def test_task_jump_on_failure(self, temp_dir):
        """Test jumping to a specific task on failure."""
        config_content = """[[tasks]]
name = "task1"
prompt = "First task"
verify_command = "false"
on_failure = "error_handler"

[[tasks]]
name = "error_handler"
prompt = "Handle error"
verify_command = "true"
"""
        config_file = temp_dir / "jump_failure.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        errors = config.validate()

        # Should be valid
        assert len(errors) == 0
        assert config.tasks[0].on_failure == "error_handler"

    def test_invalid_task_reference(self, temp_dir):
        """Test validation fails when referencing non-existent task."""
        config_content = """[[tasks]]
name = "task1"
prompt = "First task"
verify_command = "true"
on_success = "non_existent_task"
"""
        config_file = temp_dir / "invalid_ref.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        errors = config.validate()

        assert len(errors) > 0
        assert any("on_success 'non_existent_task'" in error for error in errors)
        assert any("must be one of" in error for error in errors)
        assert any("or a valid task name" in error for error in errors)

    def test_mix_reserved_and_task_names(self, temp_dir):
        """Test mixing reserved actions and task names."""
        config_content = """[[tasks]]
name = "task1"
prompt = "First task"
verify_command = "true"
on_success = "next"
on_failure = "cleanup"

[[tasks]]
name = "task2"
prompt = "Second task"
verify_command = "true"
on_success = "stop"

[[tasks]]
name = "cleanup"
prompt = "Cleanup task"
verify_command = "true"
on_failure = "retry"
"""
        config_file = temp_dir / "mixed.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        errors = config.validate()

        # Should be valid
        assert len(errors) == 0
        assert config.tasks[0].on_success == "next"  # Reserved action
        assert config.tasks[0].on_failure == "cleanup"  # Task name
        assert config.tasks[1].on_success == "stop"  # Reserved action
        assert config.tasks[2].on_failure == "retry"  # Reserved action

    def test_complex_task_flow(self, temp_dir):
        """Test a complex task flow with multiple jumps."""
        config_content = """[[tasks]]
name = "check_environment"
prompt = "Check if environment is ready"
verify_command = "test -f .env"
on_success = "build"
on_failure = "setup_environment"

[[tasks]]
name = "setup_environment"
prompt = "Setup the environment"
verify_command = "test -f .env"
on_success = "build"
on_failure = "stop"

[[tasks]]
name = "build"
prompt = "Build the project"
verify_command = "test -f build/output"
on_success = "test"
on_failure = "fix_build"

[[tasks]]
name = "fix_build"
prompt = "Fix build issues"
verify_command = "test -f build/output"
on_success = "test"
on_failure = "stop"

[[tasks]]
name = "test"
prompt = "Run tests"
verify_command = "test -f test-results.xml"
on_success = "deploy"
on_failure = "stop"

[[tasks]]
name = "deploy"
prompt = "Deploy the application"
verify_command = "curl -s http://localhost:8080/health"
on_success = "stop"
on_failure = "rollback"

[[tasks]]
name = "rollback"
prompt = "Rollback deployment"
verify_command = "true"
on_success = "stop"
on_failure = "stop"
"""
        config_file = temp_dir / "complex_flow.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        errors = config.validate()

        # Should be valid
        assert len(errors) == 0

        # Check the flow
        check_env = config.get_task_by_name("check_environment")
        assert check_env.on_success == "build"
        assert check_env.on_failure == "setup_environment"

        build = config.get_task_by_name("build")
        assert build.on_success == "test"
        assert build.on_failure == "fix_build"

    def test_self_reference_allowed(self, temp_dir):
        """Test that a task can reference itself (for retry patterns)."""
        config_content = """[[tasks]]
name = "retry_task"
prompt = "Task that might need multiple attempts"
verify_command = "test -f success_marker"
on_success = "next"
on_failure = "retry_task"
max_attempts = 1
"""
        config_file = temp_dir / "self_ref.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        errors = config.validate()

        # Should be valid - self-reference is allowed
        assert len(errors) == 0
        assert config.tasks[0].on_failure == "retry_task"
