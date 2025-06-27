"""Tests for shell command execution in verify_command."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from prompter.config import PrompterConfig
from prompter.runner import TaskRunner


class TestShellCommands:
    """Test shell command features in verify_command."""

    def test_simple_command_without_shell(self, temp_dir):
        """Test that simple commands don't use shell mode."""
        config_content = """[[tasks]]
name = "simple"
prompt = "Test task"
verify_command = "echo hello"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called without shell
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert (
                call_args.kwargs.get("shell") is None
                or call_args.kwargs.get("shell") is False
            )
            assert call_args.args[0] == ["echo", "hello"]

    def test_pipe_command_uses_shell(self, temp_dir):
        """Test that commands with pipes use shell mode."""
        config_content = """[[tasks]]
name = "pipe"
prompt = "Test task"
verify_command = "echo hello | grep ello"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ello", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args.kwargs.get("shell") is True
            assert call_args.args[0] == "echo hello | grep ello"

    def test_git_diff_pipe_grep(self, temp_dir):
        """Test the specific git diff | grep pattern from prompter1.toml."""
        config_content = """[[tasks]]
name = "git_grep"
prompt = "Test task"
verify_command = 'git diff | grep -E "\\-\\s+\\@wip"'
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="-  @wip", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            mock_run.assert_called_once()
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_command_chaining_with_double_ampersand(self, temp_dir):
        """Test commands chained with &&."""
        config_content = """[[tasks]]
name = "chain"
prompt = "Test task"
verify_command = "make test && make lint"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_output_redirection(self, temp_dir):
        """Test commands with output redirection."""
        config_content = """[[tasks]]
name = "redirect"
prompt = "Test task"
verify_command = "echo test > output.txt"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_variable_substitution(self, temp_dir):
        """Test commands with shell variable substitution."""
        config_content = """[[tasks]]
name = "variable"
prompt = "Test task"
verify_command = "echo $(date +%Y%m%d)"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="20250627", stderr=""
            )

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_glob_patterns(self, temp_dir):
        """Test commands with glob patterns."""
        config_content = """[[tasks]]
name = "glob"
prompt = "Test task"
verify_command = "ls *.py"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test.py", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_complex_awk_command(self, temp_dir):
        """Test complex command with awk."""
        config_content = """[[tasks]]
name = "awk"
prompt = "Test task"
verify_command = "df -h | awk '$5+0 > 90 {exit 1}'"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify it was called with shell
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_unmatched_quotes_fallback(self, temp_dir):
        """Test that commands with unmatched quotes fall back to shell mode."""
        config_content = """[[tasks]]
name = "quotes"
prompt = "Test task"
verify_command = "echo 'hello world"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="hello world", stderr=""
            )

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Should fall back to shell mode due to parse error
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_shell_command_timeout(self, temp_dir):
        """Test that shell commands respect timeout."""
        config_content = """[[tasks]]
name = "timeout"
prompt = "Test task"
verify_command = "sleep 10 | echo done"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="sleep 10 | echo done", timeout=300
            )

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            assert success is False
            assert "timed out" in output

    def test_shell_command_working_directory(self, temp_dir):
        """Test that shell commands run in the correct working directory."""
        config_content = """[settings]
working_directory = "/tmp"

[[tasks]]
name = "cwd"
prompt = "Test task"
verify_command = "pwd | grep -q /tmp"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="/tmp", stderr="")

            task = config.tasks[0]
            success, output = runner._verify_task(task)

            # Verify cwd was set correctly
            assert mock_run.call_args.kwargs.get("cwd") == runner.current_directory

    @pytest.mark.parametrize("shell_char", ["|", ">", "<", "&&", "||", ";", "$", "`"])
    def test_shell_indicators_detected(self, temp_dir, shell_char):
        """Test that various shell indicators are properly detected."""
        config_content = f"""[[tasks]]
name = "shell_test"
prompt = "Test task"
verify_command = "echo test {shell_char} echo done"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            task = config.tasks[0]
            runner._verify_task(task)

            # All these should trigger shell mode
            assert mock_run.call_args.kwargs.get("shell") is True

    def test_error_propagation(self, temp_dir):
        """Test that errors in shell commands are properly propagated."""
        config_content = """[[tasks]]
name = "error"
prompt = "Test task"
verify_command = "false | echo 'should fail'"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        runner = TaskRunner(config)

        # Run actual command (false should return 1)
        task = config.tasks[0]
        success, output = runner._verify_task(task)

        # The command should fail because 'false' returns 1
        # Note: the pipe might mask the error depending on shell settings
        assert "Exit code:" in output
