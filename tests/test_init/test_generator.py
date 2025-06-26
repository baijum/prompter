"""Tests for the main configuration generator orchestration."""

from pathlib import Path
from unittest.mock import patch

import pytest
from prompter.cli.init.analyzer import AnalysisResult
from prompter.cli.init.generator import ConfigGenerator


class TestConfigGenerator:
    """Test the ConfigGenerator class."""

    def test_init_default_filename(self):
        """Test generator initialization with default filename."""
        generator = ConfigGenerator()
        assert generator.filename == "prompter.toml"
        assert generator.project_path == Path.cwd()

    def test_init_custom_filename(self):
        """Test generator initialization with custom filename."""
        generator = ConfigGenerator("custom.toml")
        assert generator.filename == "custom.toml"

    def test_confirm_overwrite_yes(self, capsys):
        """Test confirming file overwrite."""
        generator = ConfigGenerator("test.toml")
        with patch.object(generator.console, "get_input", return_value="y"):
            with patch("pathlib.Path.exists", return_value=True):
                result = generator._confirm_overwrite()
                assert result is True

    def test_confirm_overwrite_no(self, capsys):
        """Test declining file overwrite."""
        generator = ConfigGenerator("test.toml")
        with patch.object(generator.console, "get_input", return_value="n"):
            with patch("pathlib.Path.exists", return_value=True):
                result = generator._confirm_overwrite()
                assert result is False

    def test_missing_claude_sdk(self, capsys):
        """Test error when Claude SDK not available."""
        generator = ConfigGenerator("test.toml")

        # Mock the import to fail
        with patch.dict("sys.modules", {"claude_code_sdk": None}):
            with pytest.raises(SystemExit) as exc:
                generator.generate()

            assert exc.value.code == 1

        captured = capsys.readouterr()
        # Check stderr since error messages go there
        assert (
            "Claude Code SDK is required" in captured.err
            or "Claude Code SDK is required" in captured.out
        )
        assert "https://claude.ai/code" in captured.out

    def test_generate_with_existing_file_cancelled(self):
        """Test generate when existing file and user cancels."""
        generator = ConfigGenerator("test.toml")

        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(generator, "_confirm_overwrite", return_value=False):
                generator.generate()

        # Should exit early without error

    def test_generate_success_quick_setup(self, tmp_path, monkeypatch):
        """Test successful generation with quick setup (ENTER)."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "test.toml"

        generator = ConfigGenerator("test.toml")

        # Mock the SDK check
        with patch.object(generator, "_check_claude_sdk_available", return_value=True):
            # Mock analysis
            mock_analysis = AnalysisResult(
                language="Python",
                test_framework="pytest",
                test_command="pytest",
                linter="ruff",
                lint_command="ruff check .",
                suggestions=[
                    {
                        "name": "fix_imports",
                        "prompt": "Organize imports",
                        "verify_command": "ruff check --select I .",
                    }
                ],
            )

            with patch.object(
                generator, "_perform_ai_analysis", return_value=mock_analysis
            ):
                with patch.object(generator.console, "get_input", return_value=""):
                    generator.generate()

        # Check file was created
        assert config_file.exists()

        # Check content
        import tomllib

        with open(config_file, "rb") as f:
            config = tomllib.load(f)
        assert "settings" in config
        assert "tasks" in config
        assert len(config["tasks"]) >= 2  # At least suggestions + standard tasks

    def test_generate_success_with_customization(self, tmp_path, monkeypatch):
        """Test successful generation with customization."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "test.toml"

        generator = ConfigGenerator("test.toml")

        # Mock the SDK check
        with patch.object(generator, "_check_claude_sdk_available", return_value=True):
            # Mock analysis
            mock_analysis = AnalysisResult(
                language="Python", test_framework="pytest", test_command="pytest"
            )

            # Mock interactive customization
            mock_config = {
                "settings": {"working_directory": "."},
                "tasks": [
                    {
                        "name": "custom_task",
                        "prompt": "Do something",
                        "verify_command": "echo done",
                        "timeout": 300,
                    }
                ],
            }

            with patch.object(
                generator, "_perform_ai_analysis", return_value=mock_analysis
            ):
                with patch.object(generator.console, "get_input", side_effect=["c"]):
                    with patch(
                        "prompter.cli.init.generator.InteractiveConfigurator.customize",
                        return_value=mock_config,
                    ):
                        generator.generate()

        # Check file was created
        assert config_file.exists()

    def test_generate_user_quits(self):
        """Test generate when user chooses to quit."""
        generator = ConfigGenerator("test.toml")

        # Mock the SDK check
        with patch.object(generator, "_check_claude_sdk_available", return_value=True):
            mock_analysis = AnalysisResult()

            with patch.object(
                generator, "_perform_ai_analysis", return_value=mock_analysis
            ):
                with patch.object(generator.console, "get_input", return_value="q"):
                    generator.generate()

        # Should complete without creating file

    def test_analysis_timeout(self):
        """Test handling of analysis timeout."""
        generator = ConfigGenerator("test.toml")

        # Mock the SDK check
        with patch.object(generator, "_check_claude_sdk_available", return_value=True):
            with patch.object(
                generator,
                "_perform_ai_analysis",
                side_effect=Exception(
                    "Analysis timed out after 30 seconds. Please try again."
                ),
            ):
                with pytest.raises(SystemExit) as exc:
                    generator.generate()

                assert exc.value.code == 1

    def test_generate_config_from_analysis(self):
        """Test configuration generation from analysis results."""
        generator = ConfigGenerator()

        analysis = AnalysisResult(
            language="Python",
            build_command="make build",
            test_framework="pytest",
            test_command="pytest -xvs",
            linter="ruff",
            lint_command="ruff check .",
            formatter="black",
            format_command="black .",
            suggestions=[
                {
                    "name": "custom_task",
                    "prompt": "Custom prompt",
                    "verify_command": "echo done",
                }
            ],
        )

        config = generator._generate_config_from_analysis(analysis)

        # Check structure
        assert "settings" in config
        assert "tasks" in config
        assert "tools" in config

        # Check tools
        assert config["tools"]["test_command"] == "pytest -xvs"
        assert config["tools"]["lint_command"] == "ruff check ."

        # Check tasks
        task_names = [t["name"] for t in config["tasks"]]
        assert "custom_task" in task_names
        assert "fix_test_failures" in task_names
        assert "fix_linting_errors" in task_names
        assert "format_code" in task_names

    def test_display_analysis_results(self, capsys):
        """Test display of analysis results."""
        generator = ConfigGenerator()

        analysis = AnalysisResult(
            language="Python",
            build_system="make",
            test_framework="pytest",
            linter="ruff",
            issues=["Issue 1", "Issue 2"],
        )

        generator._display_analysis_results(analysis)

        captured = capsys.readouterr()
        assert "✓ Detected Python project" in captured.out
        assert "✓ Found build system: make" in captured.out
        assert "✓ Found test framework: pytest" in captured.out
        assert "✓ Found linter: ruff" in captured.out
        assert "✓ Found 2 areas for improvement" in captured.out
