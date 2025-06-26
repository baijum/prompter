"""Main configuration generator orchestration."""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import tomli_w

from prompter.constants import DEFAULT_INIT_TIMEOUT, DEFAULT_TASK_TIMEOUT
from prompter.utils.console import Console

from .analyzer import AnalysisResult, ProjectAnalyzer
from .interactive import InteractiveConfigurator


class ConfigGenerator:
    """Orchestrates the entire configuration generation process."""

    def __init__(self, filename: str = "prompter.toml") -> None:
        self.filename = filename
        self.console = Console()
        self.project_path = Path.cwd()

    def generate(self) -> None:
        """Main entry point for configuration generation."""
        self.console.print_header("🚀 Prompter Configuration Generator")

        # Check if file exists
        if Path(self.filename).exists() and not self._confirm_overwrite():
            self.console.print_info("Configuration generation cancelled.")
            return

        # Check for Claude SDK availability
        if not self._check_claude_sdk_available():
            self._show_sdk_required_error()
            sys.exit(1)

        # Perform AI analysis
        try:
            analysis = self._perform_ai_analysis()
            self._handle_ai_flow(analysis)
        except TimeoutError as e:
            self.console.print_error(f"\n❌ {e}")
            self.console.print_info(
                "\nTip: For large projects, increase the timeout with:"
            )
            self.console.print_info(
                f"  export PROMPTER_INIT_TIMEOUT={DEFAULT_TASK_TIMEOUT}"
            )
            sys.exit(1)
        except RuntimeError as e:
            self.console.print_error(f"\n❌ {e}")
            if "Claude Code SDK" in str(e):
                self.console.print_info(
                    "\nPlease ensure Claude Code is properly installed and running:"
                )
                self.console.print_info(
                    "  1. Check installation: claude-code --version"
                )
                self.console.print_info("  2. Verify it's running: claude-code status")
                self.console.print_info("  3. Try restarting: claude-code restart")
            sys.exit(1)
        except Exception as e:
            self.console.print_error(f"\n❌ Unexpected error: {e}")
            self.console.print_info(
                "\nIf the problem persists, please report this issue."
            )
            sys.exit(1)

    def _check_claude_sdk_available(self) -> bool:
        """Check if Claude SDK is available."""
        try:
            return importlib.util.find_spec("claude_code_sdk") is not None
        except (ImportError, ValueError):
            return False

    def _confirm_overwrite(self) -> bool:
        """Confirm overwriting existing file."""
        self.console.print_warning(f"\n⚠️  File '{self.filename}' already exists.")
        response = self.console.get_input("Overwrite? [y/N]: ").lower()
        return response == "y"

    def _show_sdk_required_error(self) -> None:
        """Show error when Claude SDK is not available."""
        self.console.print_error(
            "\n❌ Error: Claude Code SDK is required for configuration generation"
        )
        self.console.print_info(
            "\nThe --init command requires Claude Code SDK to analyze your project"
        )
        self.console.print_info("and generate intelligent configurations.")
        self.console.print_info("\nTo fix this:")
        self.console.print_info(
            "1. Ensure Claude Code is installed: https://claude.ai/code"
        )
        self.console.print_info("2. Verify it's accessible: claude-code --version")
        self.console.print_info("3. Try again: prompter --init")
        self.console.print_info("\nFor manual configuration examples, see:")
        self.console.print_info(
            "https://github.com/YourOrg/prompter/tree/main/examples"
        )

    def _perform_ai_analysis(self) -> AnalysisResult:
        """Perform AI analysis of the project."""
        self.console.print_status("🔍 Analyzing your project with AI...")
        analyzer = ProjectAnalyzer(self.project_path)

        # Run async analysis with timeout
        timeout = int(
            os.environ.get("PROMPTER_INIT_TIMEOUT", str(DEFAULT_INIT_TIMEOUT))
        )

        try:
            # Use asyncio.run() which properly sets up the event loop
            analysis = asyncio.run(analyzer.analyze_with_timeout(timeout=timeout))
        except TimeoutError as e:
            msg = f"Analysis timed out after {timeout} seconds. Please try again.\nYou can increase the timeout by setting PROMPTER_INIT_TIMEOUT environment variable."
            raise TimeoutError(msg) from e

        # Display results
        self._display_analysis_results(analysis)
        return analysis

    def _handle_ai_flow(self, analysis: AnalysisResult) -> None:
        """Handle configuration when AI analysis succeeds."""
        # Offer quick setup
        self.console.print_section("💡 Quick Setup Available!")
        self.console.print_info("   Press ENTER to accept all recommendations")
        self.console.print_info("   Press 'c' to customize each task")
        self.console.print_info("   Press 'q' to quit")

        choice = self.console.get_input("\nYour choice [ENTER/c/q]: ").lower()

        if choice == "q":
            self.console.print_info("Configuration generation cancelled.")
            return

        # Generate base configuration from analysis
        config = self._generate_config_from_analysis(analysis)

        if choice == "c":
            # Interactive customization
            self.console.print_header("📋 Customizing Configuration")
            configurator = InteractiveConfigurator(self.console)
            config = configurator.customize(config, analysis)

        # Save configuration
        self._save_configuration(config)
        self._show_success_message()

    def _display_analysis_results(self, analysis: AnalysisResult) -> None:
        """Display AI analysis results."""
        if analysis.language:
            self.console.print_success(f"   ✓ Detected {analysis.language} project")
        if analysis.build_system:
            self.console.print_success(
                f"   ✓ Found build system: {analysis.build_system}"
            )
        if analysis.test_framework:
            self.console.print_success(
                f"   ✓ Found test framework: {analysis.test_framework}"
            )
        if analysis.linter:
            self.console.print_success(f"   ✓ Found linter: {analysis.linter}")
        if analysis.issues:
            self.console.print_success(
                f"   ✓ Found {len(analysis.issues)} areas for improvement"
            )

    def _generate_config_from_analysis(
        self, analysis: AnalysisResult
    ) -> dict[str, Any]:
        """Generate configuration from AI analysis results."""
        config: dict[str, Any] = {
            "settings": {
                "working_directory": ".",
                "check_interval": 30,
            },
            "tasks": [],
        }

        # Add tool commands if found
        tools = {}
        if analysis.build_command:
            tools["build_command"] = analysis.build_command
        if analysis.test_command:
            tools["test_command"] = analysis.test_command
        if analysis.lint_command:
            tools["lint_command"] = analysis.lint_command
        if analysis.format_command:
            tools["format_command"] = analysis.format_command
        if analysis.doc_command:
            tools["doc_command"] = analysis.doc_command

        if tools:
            config["tools"] = tools

        # Add suggested tasks
        for suggestion in analysis.suggestions:
            task = {
                "name": suggestion["name"],
                "prompt": suggestion["prompt"],
                "verify_command": suggestion["verify_command"],
                "timeout": DEFAULT_TASK_TIMEOUT,
                "on_success": "next",
                "on_failure": "retry",
                "max_attempts": 3,
            }
            config["tasks"].append(task)

        # Add standard maintenance tasks based on detected tools
        if analysis.test_framework and analysis.test_command:
            config["tasks"].append(
                {
                    "name": "fix_test_failures",
                    "prompt": f"Run the tests using '{analysis.test_command}' and fix any failures you find. Focus on fixing actual test failures, not warnings.",
                    "verify_command": analysis.test_command,
                    "timeout": DEFAULT_TASK_TIMEOUT,
                    "on_success": "next",
                    "on_failure": "retry",
                    "max_attempts": 3,
                }
            )

        if analysis.linter and analysis.lint_command:
            config["tasks"].append(
                {
                    "name": "fix_linting_errors",
                    "prompt": f"Run the linter using '{analysis.lint_command}' and fix any errors. Focus on errors, not warnings unless they're critical.",
                    "verify_command": analysis.lint_command,
                    "timeout": DEFAULT_TASK_TIMEOUT,
                    "on_success": "next",
                    "on_failure": "retry",
                    "max_attempts": 3,
                }
            )

        if analysis.formatter and analysis.format_command:
            config["tasks"].append(
                {
                    "name": "format_code",
                    "prompt": f"Format the codebase using '{analysis.format_command}'. Ensure all code follows the project's style guidelines.",
                    "verify_command": f"{analysis.format_command} --check || {analysis.format_command} --verify || echo 'Formatting complete'",
                    "timeout": DEFAULT_TASK_TIMEOUT,
                    "on_success": "next",
                    "on_failure": "retry",
                    "max_attempts": 2,
                }
            )

        return config

    def _save_configuration(self, config: dict[str, Any]) -> None:
        """Save configuration to TOML file."""
        # Convert task objects to dictionaries if needed
        if "tasks" in config:
            tasks = []
            for task in config["tasks"]:
                if hasattr(task, "to_dict"):
                    tasks.append(task.to_dict())
                else:
                    tasks.append(task)
            config["tasks"] = tasks

        # Write TOML file
        with open(self.filename, "wb") as f:
            tomli_w.dump(config, f)

    def _show_success_message(self) -> None:
        """Show success message after configuration is saved."""
        self.console.print_success(f"\n✅ Configuration saved to: {self.filename}")
        self.console.print_info("\n🎉 Your personalized configuration is ready!")
        self.console.print_info("\n📚 Next steps:")
        self.console.print_info(f"   1. Review: cat {self.filename}")
        self.console.print_info(f"   2. Test: prompter {self.filename} --dry-run")
        self.console.print_info(f"   3. Run: prompter {self.filename}")
