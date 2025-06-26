"""Tests for allow_infinite_loops setting."""

from prompter.config import PrompterConfig


class TestAllowInfiniteLoops:
    """Test allow_infinite_loops configuration setting."""

    def test_default_setting_is_false(self, temp_dir):
        """Test that allow_infinite_loops defaults to False."""
        config_content = """[[tasks]]
name = "test"
prompt = "Test task"
verify_command = "echo test"
"""
        config_file = temp_dir / "default.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.allow_infinite_loops is False

    def test_explicit_false_setting(self, temp_dir):
        """Test explicitly setting allow_infinite_loops to false."""
        config_content = """[settings]
allow_infinite_loops = false

[[tasks]]
name = "test"
prompt = "Test task"
verify_command = "echo test"
"""
        config_file = temp_dir / "explicit_false.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.allow_infinite_loops is False

    def test_explicit_true_setting(self, temp_dir):
        """Test explicitly setting allow_infinite_loops to true."""
        config_content = """[settings]
allow_infinite_loops = true

[[tasks]]
name = "test"
prompt = "Test task"
verify_command = "echo test"
"""
        config_file = temp_dir / "explicit_true.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.allow_infinite_loops is True

    def test_setting_with_other_settings(self, temp_dir):
        """Test allow_infinite_loops with other settings."""
        config_content = """[settings]
working_directory = "/tmp"
check_interval = 60
max_retries = 5
allow_infinite_loops = true

[[tasks]]
name = "test"
prompt = "Test task"
verify_command = "echo test"
"""
        config_file = temp_dir / "multiple_settings.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.working_directory == "/tmp"
        assert config.check_interval == 60
        assert config.max_retries == 5
        assert config.allow_infinite_loops is True

    def test_loop_config_with_setting_enabled(self, temp_dir):
        """Test a loop configuration with allow_infinite_loops enabled."""
        config_content = """[settings]
allow_infinite_loops = true

[[tasks]]
name = "loop_task"
prompt = "Task that loops"
verify_command = "echo loop"
on_success = "loop_task"  # Self-reference

[[tasks]]
name = "other_task"
prompt = "Another task"
verify_command = "echo other"
"""
        config_file = temp_dir / "loop_enabled.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.allow_infinite_loops is True

        # Verify the loop configuration is valid
        errors = config.validate()
        assert len(errors) == 0

        # Check the self-reference exists
        loop_task = config.get_task_by_name("loop_task")
        assert loop_task.on_success == "loop_task"

    def test_intentional_infinite_loop_scenario(self, temp_dir):
        """Test a scenario where infinite loops might be intentionally useful."""
        config_content = """[settings]
# Enable infinite loops for continuous monitoring
allow_infinite_loops = true

[[tasks]]
name = "monitor_system"
prompt = "Check system health and alert on issues"
verify_command = "systemctl is-active myservice"
on_success = "wait_and_check"
on_failure = "alert_and_fix"

[[tasks]]
name = "wait_and_check"
prompt = "Wait 60 seconds"
verify_command = "sleep 60"
on_success = "monitor_system"  # Loop back to monitoring

[[tasks]]
name = "alert_and_fix"
prompt = "Send alert and attempt to fix the service"
verify_command = "systemctl restart myservice && systemctl is-active myservice"
on_success = "monitor_system"  # Return to monitoring
on_failure = "stop"  # Stop if we can't fix it
"""
        config_file = temp_dir / "monitoring.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.allow_infinite_loops is True

        # This creates an intentional monitoring loop
        monitor = config.get_task_by_name("monitor_system")
        wait = config.get_task_by_name("wait_and_check")
        alert = config.get_task_by_name("alert_and_fix")

        # Verify the loop structure
        assert monitor.on_success == "wait_and_check"
        assert wait.on_success == "monitor_system"
        assert alert.on_success == "monitor_system"
        assert alert.on_failure == "stop"  # Has an exit condition

    def test_complex_workflow_with_loops_allowed(self, temp_dir):
        """Test complex workflow where some loops are intentional."""
        config_content = """[settings]
allow_infinite_loops = true

# Continuous integration workflow that runs indefinitely
[[tasks]]
name = "poll_for_changes"
prompt = "Check for new commits in the repository"
verify_command = "git fetch && git status | grep 'Your branch is behind'"
on_success = "pull_and_build"  # New changes found
on_failure = "wait_for_changes"  # No changes

[[tasks]]
name = "wait_for_changes"
prompt = "Wait 5 minutes before checking again"
verify_command = "sleep 300"
on_success = "poll_for_changes"  # Loop back

[[tasks]]
name = "pull_and_build"
prompt = "Pull latest changes and build"
verify_command = "git pull && make build"
on_success = "run_tests"
on_failure = "notify_build_failure"

[[tasks]]
name = "run_tests"
prompt = "Run the test suite"
verify_command = "make test"
on_success = "deploy_staging"
on_failure = "notify_test_failure"

[[tasks]]
name = "deploy_staging"
prompt = "Deploy to staging environment"
verify_command = "make deploy-staging"
on_success = "poll_for_changes"  # Loop back to polling
on_failure = "rollback_staging"

[[tasks]]
name = "notify_build_failure"
prompt = "Send build failure notification"
verify_command = "send-notification 'Build failed'"
on_success = "poll_for_changes"  # Continue monitoring

[[tasks]]
name = "notify_test_failure"
prompt = "Send test failure notification"
verify_command = "send-notification 'Tests failed'"
on_success = "poll_for_changes"  # Continue monitoring

[[tasks]]
name = "rollback_staging"
prompt = "Rollback staging deployment"
verify_command = "make rollback-staging"
on_success = "poll_for_changes"  # Continue monitoring
"""
        config_file = temp_dir / "ci_workflow.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        assert config.allow_infinite_loops is True

        # Verify all tasks eventually loop back to polling
        poll_task = config.get_task_by_name("poll_for_changes")
        assert poll_task is not None

        # All paths should eventually lead back to poll_for_changes
        # This is an intentional design for continuous integration
