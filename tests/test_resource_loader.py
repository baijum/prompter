"""Tests for the resource_loader module."""

from unittest.mock import MagicMock, patch

from prompter.utils.resource_loader import (
    _get_fallback_system_prompt,
    get_example_config,
    get_system_prompt,
    get_workflow_examples,
    list_available_examples,
)


class TestGetSystemPrompt:
    """Tests for get_system_prompt function."""

    def test_get_system_prompt_success(self):
        """Test loading system prompt from resources."""
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.read_text.return_value = "Test system prompt content"
        mock_files.__truediv__.return_value = mock_file

        with patch("importlib.resources.files", return_value=mock_files):
            result = get_system_prompt()

        assert result == "Test system prompt content"
        mock_files.__truediv__.assert_called_once_with("PROMPTER_SYSTEM_PROMPT.md")
        mock_file.read_text.assert_called_once()

    def test_get_system_prompt_file_not_found(self):
        """Test fallback when resource file is not found."""
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.read_text.side_effect = FileNotFoundError
        mock_files.__truediv__.return_value = mock_file

        with patch("importlib.resources.files", return_value=mock_files):
            result = get_system_prompt()

        # Should return the fallback prompt
        assert "AI assistant helping to analyze" in result
        assert "prompter tool" in result

    def test_get_system_prompt_module_not_found(self):
        """Test fallback when resources module is not found."""
        with patch("importlib.resources.files", side_effect=ModuleNotFoundError):
            result = get_system_prompt()

        # Should return the fallback prompt
        assert "AI assistant helping to analyze" in result
        assert "prompter tool" in result


class TestGetExampleConfig:
    """Tests for get_example_config function."""

    def test_get_example_config_success(self):
        """Test loading example config for a language."""
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.read_text.return_value = "# Python example config"
        mock_files.__truediv__.return_value = mock_file

        with patch("importlib.resources.files", return_value=mock_files):
            result = get_example_config("python")

        assert result == "# Python example config"
        mock_files.__truediv__.assert_called_once_with("python_example.toml")

    def test_get_example_config_lowercase_conversion(self):
        """Test that language name is converted to lowercase."""
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.read_text.return_value = "# Python example config"
        mock_files.__truediv__.return_value = mock_file

        with patch("importlib.resources.files", return_value=mock_files):
            result = get_example_config("PYTHON")

        assert result == "# Python example config"
        mock_files.__truediv__.assert_called_once_with("python_example.toml")

    def test_get_example_config_not_found(self):
        """Test handling when example config is not found."""
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.read_text.side_effect = FileNotFoundError
        mock_files.__truediv__.return_value = mock_file

        with patch("importlib.resources.files", return_value=mock_files):
            result = get_example_config("unknown")

        assert result is None

    def test_get_example_config_module_error(self):
        """Test handling when resources module is not found."""
        with patch("importlib.resources.files", side_effect=ModuleNotFoundError):
            result = get_example_config("python")

        assert result is None


class TestListAvailableExamples:
    """Tests for list_available_examples function."""

    def test_list_available_examples_success(self):
        """Test listing available example configurations."""
        # Mock file objects
        mock_python_file = MagicMock()
        mock_python_file.name = "python_example.toml"

        mock_javascript_file = MagicMock()
        mock_javascript_file.name = "javascript_example.toml"

        mock_other_file = MagicMock()
        mock_other_file.name = "README.md"

        mock_files = MagicMock()
        mock_files.iterdir.return_value = [
            mock_python_file,
            mock_javascript_file,
            mock_other_file,
        ]

        with patch("importlib.resources.files", return_value=mock_files):
            result = list_available_examples()

        assert result == ["javascript", "python"]  # Sorted alphabetically
        mock_files.iterdir.assert_called_once()

    def test_list_available_examples_empty(self):
        """Test when no example files are found."""
        mock_files = MagicMock()
        mock_files.iterdir.return_value = []

        with patch("importlib.resources.files", return_value=mock_files):
            result = list_available_examples()

        assert result == []

    def test_list_available_examples_attribute_error(self):
        """Test handling AttributeError (e.g., iterdir not available)."""
        mock_files = MagicMock()
        mock_files.iterdir.side_effect = AttributeError

        with patch("importlib.resources.files", return_value=mock_files):
            result = list_available_examples()

        assert result == []

    def test_list_available_examples_module_error(self):
        """Test handling when resources module is not found."""
        with patch("importlib.resources.files", side_effect=ModuleNotFoundError):
            result = list_available_examples()

        assert result == []


class TestGetWorkflowExamples:
    """Tests for get_workflow_examples function."""

    def test_get_workflow_examples_content(self):
        """Test that workflow examples contain expected content."""
        result = get_workflow_examples()

        # Check that all expected workflows are present
        assert "basic_workflow" in result
        assert "conditional_workflow" in result
        assert "security_workflow" in result

        # Check basic workflow content
        basic = result["basic_workflow"]
        assert "run_tests" in basic
        assert "fix_test_failures" in basic
        assert "pytest" in basic

        # Check conditional workflow content
        conditional = result["conditional_workflow"]
        assert "check_environment" in conditional
        assert "setup_environment" in conditional
        assert 'on_failure = "setup_environment"' in conditional

        # Check security workflow content
        security = result["security_workflow"]
        assert "security_scan" in security
        assert "fix_vulnerabilities" in security
        assert "safety check" in security
        assert "timeout = 300" in security

    def test_get_workflow_examples_structure(self):
        """Test that workflow examples have valid TOML structure."""
        result = get_workflow_examples()

        for _workflow_name, content in result.items():
            # Check that each workflow has tasks
            assert "[[tasks]]" in content
            assert "name =" in content
            assert "prompt =" in content
            assert "verify_command =" in content


class TestGetFallbackSystemPrompt:
    """Tests for _get_fallback_system_prompt function."""

    def test_fallback_system_prompt_content(self):
        """Test that fallback prompt contains expected content."""
        result = _get_fallback_system_prompt()

        # Check key phrases
        assert "AI assistant" in result
        assert "analyze a software project" in result
        assert "prompter tool" in result

        # Check that it mentions key responsibilities
        assert "primary language" in result
        assert "build systems" in result
        assert "test frameworks" in result
        assert "linters" in result
        assert "automated code maintenance" in result
