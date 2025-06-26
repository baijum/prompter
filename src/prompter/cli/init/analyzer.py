"""AI-powered project analysis using Claude Code SDK."""

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, query


@dataclass
class AnalysisResult:
    """Results from AI project analysis."""

    language: str | None = None
    build_system: str | None = None
    build_command: str | None = None
    test_framework: str | None = None
    test_command: str | None = None
    linter: str | None = None
    lint_command: str | None = None
    formatter: str | None = None
    format_command: str | None = None
    documentation_tool: str | None = None
    doc_command: str | None = None
    issues: list[str] = field(default_factory=list)
    suggestions: list[dict[str, str]] = field(default_factory=list)
    custom_commands: dict[str, str] = field(default_factory=dict)


class ProjectAnalyzer:
    """Analyzes projects using Claude Code SDK."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        # Temporarily use a minimal system prompt to avoid SDK issues
        self.system_prompt = "You are an AI assistant analyzing a software project."

    async def analyze_with_timeout(self, timeout: int = 30) -> AnalysisResult:
        """Analyze project with timeout."""
        try:
            return await asyncio.wait_for(self.analyze(), timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"Analysis timed out after {timeout} seconds")
        except Exception as e:
            # Handle any other exceptions that might occur during analysis
            raise RuntimeError(f"Analysis failed: {e!s}") from e

    async def analyze(self) -> AnalysisResult:
        """Perform comprehensive project analysis."""
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(f"Starting analysis for project at: {self.project_path}")
        analysis_prompt = self._build_analysis_prompt()

        options = ClaudeCodeOptions(
            cwd=str(self.project_path), permission_mode="bypassPermissions"
        )

        # Collect analysis results
        response_text = ""
        try:
            logger.debug("Calling Claude SDK query...")
            message_count = 0
            async for message in query(prompt=analysis_prompt, options=options):
                message_count += 1
                logger.debug(
                    f"Received message {message_count}: {type(message).__name__}"
                )
                if hasattr(message, "content"):
                    for content in message.content:
                        if hasattr(content, "text"):
                            response_text += content.text
                            logger.debug(f"  Added text: {content.text[:100]}...")
            logger.debug(f"Query completed. Total messages: {message_count}")
        except Exception as e:
            # If the Claude SDK query fails, provide a helpful error message
            logger.exception(f"Claude SDK query failed: {type(e).__name__}")
            error_msg = str(e)
            if "TaskGroup" in error_msg:
                error_message = (
                    "Claude Code SDK encountered an internal error. "
                    "Please ensure Claude Code is properly installed and running."
                )
                raise RuntimeError(error_message) from e
            raise RuntimeError(f"Failed to query Claude Code SDK: {error_msg}") from e

        # Parse results
        logger.debug(f"Response text length: {len(response_text)}")
        logger.debug(f"Response text: {response_text}")
        return self._parse_analysis_response(response_text)

    def _build_analysis_prompt(self) -> str:
        """Build the analysis prompt."""
        # Get key files to help with analysis
        key_files = self._get_key_project_files()

        return f"""IMPORTANT: Respond with ONLY a JSON object, no other text.

Key files in this project:
{key_files}

Analyze and return JSON:
{{
    "language": "detected language",
    "build_command": "build command",
    "test_framework": "test framework",
    "test_command": "test command",
    "linter": "linter name",
    "lint_command": "lint command",
    "suggestions": [{{"name": "task", "prompt": "description", "verify_command": "command"}}]
}}"""

    def _get_key_project_files(self) -> str:
        """Get list of key project files for analysis."""
        key_files = []

        # Look for common project files
        patterns = [
            "package.json",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Makefile",
            "CMakeLists.txt",
            ".gitignore",
            "README*",
        ]

        for pattern in patterns:
            for file in self.project_path.glob(pattern):
                if file.is_file():
                    key_files.append(f"- {file.name}")

        # Check for test directories
        for test_dir in ["tests", "test", "spec", "__tests__"]:
            if (self.project_path / test_dir).is_dir():
                key_files.append(f"- {test_dir}/ (directory)")

        return "\n".join(key_files[:10])  # Limit to 10 files

    def _parse_analysis_response(self, response: str) -> AnalysisResult:
        """Parse AI response into AnalysisResult."""
        # Try to extract and parse JSON
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            try:
                data = json.loads(json_str)
                return AnalysisResult(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                # JSON parsing failed, will fall back to text parsing
                pass

        # If no JSON found or parsing failed, use text parsing
        return self._parse_text_response(response)

    def _parse_text_response(self, response: str) -> AnalysisResult:
        """Parse text response as fallback."""
        result = AnalysisResult()

        # Try to extract key information from text
        lines = response.lower().split("\n")

        for line in lines:
            if "python" in line and not result.language:
                result.language = "Python"
            elif "javascript" in line and not result.language:
                result.language = "JavaScript"
            elif "typescript" in line and not result.language:
                result.language = "TypeScript"
            elif "rust" in line and not result.language:
                result.language = "Rust"

            if "pytest" in line and not result.test_framework:
                result.test_framework = "pytest"
                result.test_command = "pytest"
            elif "jest" in line and not result.test_framework:
                result.test_framework = "jest"
                result.test_command = "npm test"

            if "ruff" in line and not result.linter:
                result.linter = "ruff"
                result.lint_command = "ruff check ."
            elif "eslint" in line and not result.linter:
                result.linter = "eslint"
                result.lint_command = "npm run lint"
            elif "mypy" in line and not result.linter:
                result.linter = "mypy"
                result.lint_command = "mypy ."

            if "make" in line and not result.build_system:
                result.build_system = "make"
                result.build_command = "make"
            elif "npm" in line and not result.build_system:
                result.build_system = "npm"
                result.build_command = "npm run build"
            elif "cargo" in line and not result.build_system:
                result.build_system = "cargo"
                result.build_command = "cargo build"

        # Default suggestions if nothing specific found
        if not result.suggestions:
            result.suggestions = [
                {
                    "name": "improve_code_quality",
                    "prompt": "Review the codebase and fix any obvious issues or improvements",
                    "verify_command": "echo 'Manual review complete'",
                }
            ]

        return result
