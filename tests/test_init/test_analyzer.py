"""Tests for the AI project analyzer."""

import anyio
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from prompter.cli.init.analyzer import AnalysisResult, ProjectAnalyzer


class TestAnalysisResult:
    """Test the AnalysisResult dataclass."""

    def test_default_initialization(self):
        """Test default values are properly initialized."""
        result = AnalysisResult()
        assert result.language is None
        assert result.build_system is None
        assert result.issues == []
        assert result.suggestions == []
        assert result.custom_commands == {}

    def test_full_initialization(self):
        """Test initialization with all fields."""
        result = AnalysisResult(
            language="Python",
            build_system="make",
            build_command="make build",
            test_framework="pytest",
            test_command="pytest",
            linter="ruff",
            lint_command="ruff check .",
            formatter="black",
            format_command="black .",
            documentation_tool="sphinx",
            doc_command="make docs",
            issues=["Issue 1"],
            suggestions=[{"name": "task1", "prompt": "Fix", "verify_command": "test"}],
            custom_commands={"custom": "command"},
        )

        assert result.language == "Python"
        assert result.build_system == "make"
        assert result.build_command == "make build"
        assert len(result.issues) == 1
        assert len(result.suggestions) == 1
        assert result.custom_commands["custom"] == "command"


class TestProjectAnalyzer:
    """Test the ProjectAnalyzer class."""

    def test_initialization(self, tmp_path):
        """Test analyzer initialization."""
        analyzer = ProjectAnalyzer(tmp_path)
        assert analyzer.project_path == tmp_path
        assert "You are an AI assistant" in analyzer.system_prompt

    @pytest.mark.asyncio()
    async def test_analyze_with_timeout_success(self, tmp_path):
        """Test successful analysis within timeout."""
        analyzer = ProjectAnalyzer(tmp_path)

        # Mock the analyze method to return a coroutine
        mock_result = AnalysisResult(language="Python")

        async def mock_analyze():
            return mock_result

        with patch.object(analyzer, "analyze", side_effect=mock_analyze):
            result = await analyzer.analyze_with_timeout(timeout=5)
            assert result.language == "Python"

    @pytest.mark.asyncio()
    async def test_analyze_with_timeout_failure(self, tmp_path):
        """Test analysis timeout."""
        analyzer = ProjectAnalyzer(tmp_path)

        # Mock analyze to take too long
        async def slow_analyze():
            await anyio.sleep(2)
            return AnalysisResult()

        with patch.object(analyzer, "analyze", side_effect=slow_analyze):
            with pytest.raises(TimeoutError) as exc:
                await analyzer.analyze_with_timeout(timeout=0.1)

            assert "timed out after" in str(exc.value)

    def test_build_analysis_prompt(self, tmp_path):
        """Test building the analysis prompt."""
        analyzer = ProjectAnalyzer(tmp_path)
        prompt = analyzer._build_analysis_prompt()

        # Check key elements
        assert "JSON object" in prompt
        assert '"language"' in prompt
        assert '"suggestions"' in prompt
        assert "IMPORTANT" in prompt

    def test_parse_analysis_response_valid_json(self):
        """Test parsing valid JSON response."""
        analyzer = ProjectAnalyzer(Path.cwd())

        response = """
        Here's the analysis:
        {
            "language": "Python",
            "test_framework": "pytest",
            "test_command": "pytest",
            "issues": ["No tests found"],
            "suggestions": [{
                "name": "add_tests",
                "prompt": "Add unit tests",
                "verify_command": "pytest"
            }]
        }
        Done.
        """

        result = analyzer._parse_analysis_response(response)
        assert result.language == "Python"
        assert result.test_framework == "pytest"
        assert result.test_command == "pytest"
        assert len(result.issues) == 1
        assert len(result.suggestions) == 1

    def test_parse_analysis_response_invalid_json(self):
        """Test parsing with invalid JSON falls back to text parsing."""
        analyzer = ProjectAnalyzer(Path.cwd())

        response = """
        I found that this is a python project using pytest for testing.
        The linter appears to be ruff.
        Build system: make
        """

        result = analyzer._parse_analysis_response(response)
        assert result.language == "Python"
        assert result.test_framework == "pytest"
        assert result.test_command == "pytest"
        assert result.linter == "ruff"
        assert result.lint_command == "ruff check ."
        assert result.build_system == "make"
        assert result.build_command == "make"

    def test_parse_text_response_python(self):
        """Test text parsing for Python project."""
        analyzer = ProjectAnalyzer(Path.cwd())

        response = "This is a Python project with pytest and mypy"
        result = analyzer._parse_text_response(response)

        assert result.language == "Python"
        assert result.test_framework == "pytest"
        assert result.test_command == "pytest"
        assert result.linter == "mypy"
        assert result.lint_command == "mypy ."

    def test_parse_text_response_javascript(self):
        """Test text parsing for JavaScript project."""
        analyzer = ProjectAnalyzer(Path.cwd())

        response = "JavaScript project using jest and eslint with npm build"
        result = analyzer._parse_text_response(response)

        assert result.language == "JavaScript"
        assert result.test_framework == "jest"
        assert result.test_command == "npm test"
        assert result.linter == "eslint"
        assert result.lint_command == "npm run lint"
        assert result.build_system == "npm"
        assert result.build_command == "npm run build"

    def test_parse_text_response_default_suggestions(self):
        """Test that default suggestions are added when none found."""
        analyzer = ProjectAnalyzer(Path.cwd())

        response = "Empty analysis"
        result = analyzer._parse_text_response(response)

        assert len(result.suggestions) == 1
        assert result.suggestions[0]["name"] == "improve_code_quality"

    @pytest.mark.asyncio()
    async def test_analyze_full_flow(self, tmp_path):
        """Test full analysis flow with mocked Claude SDK."""
        analyzer = ProjectAnalyzer(tmp_path)

        # Mock the query function
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps(
            {
                "language": "Python",
                "test_framework": "pytest",
                "test_command": "pytest -xvs",
                "suggestions": [
                    {
                        "name": "fix_tests",
                        "prompt": "Fix failing tests",
                        "verify_command": "pytest",
                    }
                ],
            }
        )
        mock_message.content = [mock_content]

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch("prompter.cli.init.analyzer.query", side_effect=mock_query):
            result = await analyzer.analyze()

        assert result.language == "Python"
        assert result.test_framework == "pytest"
        assert result.test_command == "pytest -xvs"
        assert len(result.suggestions) == 1
