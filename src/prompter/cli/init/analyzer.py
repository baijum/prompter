"""AI-powered project analysis using Claude Code SDK."""

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, query

from prompter.utils.resource_loader import get_system_prompt


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

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.system_prompt = get_system_prompt()

    async def analyze_with_timeout(self, timeout: int = 30) -> AnalysisResult:
        """Analyze project with timeout."""
        try:
            return await asyncio.wait_for(self.analyze(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Analysis timed out after {timeout} seconds")
        except Exception as e:
            # Handle any other exceptions that might occur during analysis
            raise RuntimeError(f"Analysis failed: {str(e)}") from e

    async def analyze(self) -> AnalysisResult:
        """Perform comprehensive project analysis."""
        analysis_prompt = self._build_analysis_prompt()

        options = ClaudeCodeOptions(
            cwd=str(self.project_path), permission_mode="bypassPermissions"
        )

        # Collect analysis results
        response_text = ""
        try:
            async for message in query(prompt=analysis_prompt, options=options):
                if hasattr(message, "content"):
                    for content in message.content:
                        if hasattr(content, "text"):
                            response_text += content.text
        except Exception as e:
            # If the Claude SDK query fails, provide a helpful error message
            error_msg = str(e)
            if "TaskGroup" in error_msg:
                raise RuntimeError(
                    "Claude Code SDK encountered an internal error. "
                    "Please ensure Claude Code is properly installed and running."
                ) from e
            else:
                raise RuntimeError(f"Failed to query Claude Code SDK: {error_msg}") from e

        # Parse results
        return self._parse_analysis_response(response_text)

    def _build_analysis_prompt(self) -> str:
        """Build the analysis prompt."""
        return f"""
{self.system_prompt}

Analyze this project directory comprehensively. Your response must be a valid JSON object with this exact structure:

{{
    "language": "primary language (e.g., Python, JavaScript, Rust)",
    "build_system": "build tool name (e.g., make, npm, cargo)",
    "build_command": "exact command to build project",
    "test_framework": "test framework name",
    "test_command": "exact command to run tests",
    "linter": "linter tool name",
    "lint_command": "exact command to run linter",
    "formatter": "code formatter name",
    "format_command": "exact command to format code",
    "documentation_tool": "docs tool name",
    "doc_command": "exact command to build docs",
    "issues": [
        "list of identified issues or areas for improvement"
    ],
    "suggestions": [
        {{
            "name": "task name",
            "prompt": "specific prompt for this task",
            "verify_command": "command to verify task completion"
        }}
    ],
    "custom_commands": {{
        "command_name": "command_value"
    }}
}}

Important:
1. Only include fields where you find actual evidence
2. Commands should be exactly as they would be run
3. Suggestions should be specific to this project
4. Focus on actionable improvements

Start your analysis now. Return ONLY the JSON object, no other text.
"""

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
