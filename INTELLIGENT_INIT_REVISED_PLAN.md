# Intelligent --init Feature: Revised Implementation Plan

## Executive Summary

This document presents a streamlined implementation plan for enhancing the `prompter` tool's `--init` option. The new design makes `--init` always intelligent and interactive by default, providing users with AI-powered, project-specific configurations from the start. The static template generation becomes a fallback mechanism when AI analysis is unavailable.

## Design Philosophy

**Core Principle**: "Smart by default, simple to use"

- Single command: `prompter --init`
- Always attempts intelligent analysis
- Always offers interactive customization
- Gracefully degrades when AI unavailable
- No confusing mode flags

## User Experience Flow

### Primary Flow: Full AI Analysis Available

```
$ prompter --init

🚀 Prompter Configuration Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Analyzing your project with AI...
   ✓ Detected Python 3.11 project
   ✓ Found build system: Makefile
   ✓ Found test framework: pytest
   ✓ Found linter: ruff
   ✓ Found 3 areas for improvement

💡 Quick Setup Available!
   Press ENTER to accept all recommendations
   Press 'c' to customize each task
   Press 'q' to quit

Your choice [ENTER/c/q]: c

📋 Customizing Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detected Tools:
1. Build: make (via Makefile)
   ✓ Accept this? [Y/n]: 

2. Tests: pytest (via pytest.ini) 
   ✓ Accept this? [Y/n]: n
   Enter test command: pytest -xvs

[... continues with interactive customization ...]

✅ Configuration saved to: prompter.toml
   
   Next steps:
   1. Review the configuration: cat prompter.toml
   2. Test with dry run: prompter prompter.toml --dry-run
   3. Execute tasks: prompter prompter.toml
```

### Error Flow: No AI Available

```
$ prompter --init

🚀 Prompter Configuration Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Error: Claude Code SDK is required for configuration generation

The --init command requires Claude Code SDK to analyze your project
and generate intelligent configurations.

To fix this:
1. Ensure Claude Code is installed: https://claude.ai/code
2. Verify it's accessible: claude-code --version
3. Try again: prompter --init

For manual configuration examples, see:
https://github.com/YourOrg/prompter/tree/main/examples
```

## Technical Architecture

### 1. Module Structure

```
src/prompter/
├── cli/
│   ├── arguments.py              # Simplified - remove --smart/--interactive
│   ├── main.py                   # Updated init handling
│   ├── sample_config.py          # DELETE - no longer needed
│   └── init/                     # NEW package for init functionality
│       ├── __init__.py
│       ├── generator.py          # Main orchestration
│       ├── analyzer.py           # AI project analysis
│       └── interactive.py        # User interaction logic
├── resources/                    # Bundled resources
│   ├── PROMPTER_SYSTEM_PROMPT.md
│   └── examples/
│       └── [existing examples]
└── utils/
    ├── resource_loader.py       # Resource access
    └── console.py               # NEW: Rich console output
```

### 2. Core Implementation

#### A. Main Generator (`src/prompter/cli/init/generator.py`)

```python
"""Main configuration generator orchestration."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from ...utils.console import Console
from ...utils.resource_loader import get_system_prompt
from .analyzer import ProjectAnalyzer, AnalysisResult
from .interactive import InteractiveConfigurator


class ConfigGenerator:
    """Orchestrates the entire configuration generation process."""
    
    def __init__(self, filename: str = "prompter.toml"):
        self.filename = filename
        self.console = Console()
        self.project_path = Path.cwd()
        
    def generate(self) -> None:
        """Main entry point for configuration generation."""
        self.console.print_header("🚀 Prompter Configuration Generator")
        
        # Check if file exists
        if Path(self.filename).exists():
            if not self._confirm_overwrite():
                self.console.print_info("Configuration generation cancelled.")
                return
                
        # Check for Claude SDK availability
        try:
            import claude_code_sdk
        except ImportError:
            self._show_sdk_required_error()
            sys.exit(1)
            
        # Perform AI analysis
        try:
            analysis = self._perform_ai_analysis()
            self._handle_ai_flow(analysis)
        except Exception as e:
            self.console.print_error(f"\n❌ Error during analysis: {e}")
            self.console.print_info("\nPlease check your Claude Code SDK installation and try again.")
            sys.exit(1)
            
    def _show_sdk_required_error(self) -> None:
        """Show error when Claude SDK is not available."""
        self.console.print_error("\n❌ Error: Claude Code SDK is required for configuration generation")
        self.console.print_info("\nThe --init command requires Claude Code SDK to analyze your project")
        self.console.print_info("and generate intelligent configurations.")
        self.console.print_info("\nTo fix this:")
        self.console.print_info("1. Ensure Claude Code is installed: https://claude.ai/code")
        self.console.print_info("2. Verify it's accessible: claude-code --version")
        self.console.print_info("3. Try again: prompter --init")
        self.console.print_info("\nFor manual configuration examples, see:")
        self.console.print_info("https://github.com/YourOrg/prompter/tree/main/examples")
        
    def _perform_ai_analysis(self) -> AnalysisResult:
        """Perform AI analysis of the project."""
        self.console.print_status("🔍 Analyzing your project with AI...")
        analyzer = ProjectAnalyzer(self.project_path)
        
        # Run async analysis with timeout
        try:
            analysis = asyncio.run(analyzer.analyze_with_timeout(timeout=30))
        except TimeoutError:
            raise Exception("Analysis timed out after 30 seconds. Please try again.")
            
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
        
        choice = self.console.get_input("Your choice [ENTER/c/q]: ").lower()
        
        if choice == 'q':
            self.console.print_info("Configuration generation cancelled.")
            return
            
        # Generate base configuration from analysis
        config = self._generate_config_from_analysis(analysis)
        
        if choice == 'c':
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
            self.console.print_success(f"   ✓ Found build system: {analysis.build_system}")
        if analysis.test_framework:
            self.console.print_success(f"   ✓ Found test framework: {analysis.test_framework}")
        if analysis.linter:
            self.console.print_success(f"   ✓ Found linter: {analysis.linter}")
        if analysis.issues:
            self.console.print_success(f"   ✓ Found {len(analysis.issues)} areas for improvement")
            
    def _show_success_message(self) -> None:
        """Show success message after configuration is saved."""
        self.console.print_success(f"\n✅ Configuration saved to: {self.filename}")
        self.console.print_info("\n🎉 Your personalized configuration is ready!")
        self.console.print_info("\n📚 Next steps:")
        self.console.print_info(f"   1. Review: cat {self.filename}")
        self.console.print_info(f"   2. Test: prompter {self.filename} --dry-run")
        self.console.print_info(f"   3. Run: prompter {self.filename}")
```

#### B. AI Analyzer (`src/prompter/cli/init/analyzer.py`)

```python
"""AI-powered project analysis using Claude Code SDK."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from claude_code_sdk import ClaudeCodeOptions, query

from ...utils.resource_loader import get_system_prompt


@dataclass
class AnalysisResult:
    """Results from AI project analysis."""
    language: Optional[str] = None
    build_system: Optional[str] = None
    build_command: Optional[str] = None
    test_framework: Optional[str] = None
    test_command: Optional[str] = None
    linter: Optional[str] = None
    lint_command: Optional[str] = None
    formatter: Optional[str] = None
    format_command: Optional[str] = None
    documentation_tool: Optional[str] = None
    doc_command: Optional[str] = None
    issues: List[str] = None
    suggestions: List[Dict[str, str]] = None
    custom_commands: Dict[str, str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.suggestions is None:
            self.suggestions = []
        if self.custom_commands is None:
            self.custom_commands = {}


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
            
    async def analyze(self) -> AnalysisResult:
        """Perform comprehensive project analysis."""
        analysis_prompt = self._build_analysis_prompt()
        
        options = ClaudeCodeOptions(
            cwd=str(self.project_path),
            permission_mode="bypassPermissions"
        )
        
        # Collect analysis results
        response_text = ""
        async for message in query(prompt=analysis_prompt, options=options):
            if hasattr(message, "content"):
                for content in message.content:
                    if hasattr(content, "text"):
                        response_text += content.text
                        
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
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return AnalysisResult(**data)
        except Exception as e:
            # Fallback parsing if JSON fails
            return self._parse_text_response(response)
            
        return AnalysisResult()
```

#### C. Interactive Configuration (`src/prompter/cli/init/interactive.py`)

```python
"""Interactive configuration customization."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .analyzer import AnalysisResult
from ...utils.console import Console


@dataclass
class TaskConfig:
    """Configuration for a single task."""
    name: str
    prompt: str
    verify_command: str
    timeout: int = 300
    on_success: str = "next"
    on_failure: str = "retry"
    max_attempts: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        return {
            "name": self.name,
            "prompt": self.prompt,
            "verify_command": self.verify_command,
            "timeout": self.timeout,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "max_attempts": self.max_attempts
        }


class InteractiveConfigurator:
    """Handles interactive configuration customization."""
    
    def __init__(self, console: Console):
        self.console = console
        
    def customize(self, config: Dict[str, Any], analysis: AnalysisResult) -> Dict[str, Any]:
        """Customize configuration based on AI analysis."""
        # Confirm detected tools
        self.console.print_section("Detected Tools:")
        config = self._confirm_tools(config, analysis)
        
        # Customize tasks
        self.console.print_section("\nProposed Tasks:")
        config["tasks"] = self._customize_tasks(config.get("tasks", []))
        
        # Add custom tasks
        config["tasks"].extend(self._add_custom_tasks())
        
        # Global settings
        config["settings"] = self._customize_settings(config.get("settings", {}))
        
        return config
        
    def customize_template(self, config: Dict[str, Any], patterns: List[str]) -> Dict[str, Any]:
        """Customize template-based configuration."""
        self.console.print_section("Template Customization")
        
        # Show what was detected
        self.console.print_info("\nDetected patterns:")
        for pattern in patterns:
            self.console.print_info(f"  • {pattern}")
            
        # Customize each task in template
        self.console.print_section("\nCustomizing template tasks:")
        config["tasks"] = self._customize_tasks(config.get("tasks", []))
        
        # Offer to add more tasks
        config["tasks"].extend(self._add_custom_tasks())
        
        return config
        
    def _confirm_tools(self, config: Dict[str, Any], analysis: AnalysisResult) -> Dict[str, Any]:
        """Confirm or modify detected tools."""
        tool_mappings = [
            ("Build", analysis.build_system, analysis.build_command, "build_command"),
            ("Tests", analysis.test_framework, analysis.test_command, "test_command"),
            ("Linter", analysis.linter, analysis.lint_command, "lint_command"),
            ("Formatter", analysis.formatter, analysis.format_command, "format_command"),
            ("Docs", analysis.documentation_tool, analysis.doc_command, "doc_command")
        ]
        
        confirmed_tools = {}
        
        for tool_type, tool_name, command, key in tool_mappings:
            if tool_name:
                self.console.print_info(f"\n{tool_type}: {tool_name}")
                if command:
                    self.console.print_info(f"  Command: {command}")
                    
                confirm = self.console.get_input("  ✓ Accept this? [Y/n]: ").lower()
                
                if confirm == 'n':
                    custom_cmd = self.console.get_input(f"  Enter {tool_type.lower()} command: ")
                    confirmed_tools[key] = custom_cmd
                else:
                    confirmed_tools[key] = command
                    
        # Update config with confirmed tools
        if "tools" not in config:
            config["tools"] = {}
        config["tools"].update(confirmed_tools)
        
        return config
        
    def _customize_tasks(self, tasks: List[Dict[str, Any]]) -> List[TaskConfig]:
        """Customize individual tasks."""
        customized_tasks = []
        
        for i, task in enumerate(tasks, 1):
            self.console.print_subsection(f"\n{i}. {task['name']}")
            self.console.print_info(f"   Prompt: {task['prompt'][:80]}...")
            self.console.print_info(f"   Verify: {task['verify_command']}")
            self.console.print_info(f"   Timeout: {task.get('timeout', 300)}s")
            
            action = self.console.get_input("   Action [keep/edit/delete/skip]: ").lower()
            
            if action == 'keep' or action == '':
                customized_tasks.append(TaskConfig(**task))
            elif action == 'edit':
                customized_tasks.append(self._edit_task(task))
            elif action == 'skip':
                continue
            # 'delete' results in task not being added
            
        return customized_tasks
        
    def _edit_task(self, task: Dict[str, Any]) -> TaskConfig:
        """Edit a single task."""
        self.console.print_info("\n   Editing task (press ENTER to keep current value):")
        
        name = self.console.get_input(f"   Name [{task['name']}]: ") or task['name']
        
        self.console.print_info(f"   Current prompt: {task['prompt']}")
        new_prompt = self.console.get_input("   New prompt (or ENTER to keep): ")
        prompt = new_prompt if new_prompt else task['prompt']
        
        verify = self.console.get_input(
            f"   Verify command [{task['verify_command']}]: "
        ) or task['verify_command']
        
        timeout_str = self.console.get_input(
            f"   Timeout in seconds [{task.get('timeout', 300)}]: "
        )
        timeout = int(timeout_str) if timeout_str else task.get('timeout', 300)
        
        on_success = self.console.get_input(
            f"   On success [next/stop/repeat] [{task.get('on_success', 'next')}]: "
        ) or task.get('on_success', 'next')
        
        on_failure = self.console.get_input(
            f"   On failure [retry/next/stop] [{task.get('on_failure', 'retry')}]: "
        ) or task.get('on_failure', 'retry')
        
        max_attempts_str = self.console.get_input(
            f"   Max attempts [{task.get('max_attempts', 3)}]: "
        )
        max_attempts = int(max_attempts_str) if max_attempts_str else task.get('max_attempts', 3)
        
        return TaskConfig(
            name=name,
            prompt=prompt,
            verify_command=verify,
            timeout=timeout,
            on_success=on_success,
            on_failure=on_failure,
            max_attempts=max_attempts
        )
        
    def _add_custom_tasks(self) -> List[TaskConfig]:
        """Add custom tasks interactively."""
        custom_tasks = []
        
        while True:
            add_more = self.console.get_input("\nAdd a custom task? [y/N]: ").lower()
            if add_more != 'y':
                break
                
            self.console.print_subsection("Creating custom task:")
            
            name = self.console.get_input("  Task name: ")
            if not name:
                self.console.print_warning("  Task name is required!")
                continue
                
            prompt = self.console.get_input("  Task prompt: ")
            if not prompt:
                self.console.print_warning("  Task prompt is required!")
                continue
                
            verify = self.console.get_input("  Verify command: ")
            if not verify:
                self.console.print_warning("  Verify command is required!")
                continue
                
            # Optional fields with defaults
            timeout_str = self.console.get_input("  Timeout in seconds [300]: ")
            timeout = int(timeout_str) if timeout_str else 300
            
            on_success = self.console.get_input("  On success [next/stop/repeat] [next]: ") or "next"
            on_failure = self.console.get_input("  On failure [retry/next/stop] [retry]: ") or "retry"
            
            max_attempts_str = self.console.get_input("  Max attempts [3]: ")
            max_attempts = int(max_attempts_str) if max_attempts_str else 3
            
            custom_tasks.append(TaskConfig(
                name=name,
                prompt=prompt,
                verify_command=verify,
                timeout=timeout,
                on_success=on_success,
                on_failure=on_failure,
                max_attempts=max_attempts
            ))
            
            self.console.print_success("  ✓ Task added!")
            
        return custom_tasks
        
    def _customize_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Customize global settings."""
        self.console.print_section("\nGlobal Settings:")
        
        # Working directory
        current_wd = settings.get("working_directory", ".")
        wd = self.console.get_input(f"Working directory [{current_wd}]: ") or current_wd
        settings["working_directory"] = wd
        
        # Check interval
        current_interval = settings.get("check_interval", 30)
        interval_str = self.console.get_input(f"Check interval in seconds [{current_interval}]: ")
        settings["check_interval"] = int(interval_str) if interval_str else current_interval
        
        # Allow infinite loops
        allow_loops = self.console.get_input("Allow infinite loops? [y/N]: ").lower() == 'y'
        if allow_loops:
            settings["allow_infinite_loops"] = True
            
        return settings
```

#### D. Console Utilities (`src/prompter/utils/console.py`)

```python
"""Rich console output utilities."""

import sys
from typing import Optional


class Console:
    """Enhanced console output with formatting."""
    
    # ANSI color codes
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    
    def print_header(self, text: str) -> None:
        """Print a main header."""
        print(f"\n{self.BOLD}{self.CYAN}{text}{self.RESET}")
        print("━" * 50)
        
    def print_section(self, text: str) -> None:
        """Print a section header."""
        print(f"\n{self.BOLD}{text}{self.RESET}")
        
    def print_subsection(self, text: str) -> None:
        """Print a subsection header."""
        print(f"{self.CYAN}{text}{self.RESET}")
        
    def print_info(self, text: str) -> None:
        """Print information text."""
        print(text)
        
    def print_success(self, text: str) -> None:
        """Print success message."""
        print(f"{self.GREEN}{text}{self.RESET}")
        
    def print_warning(self, text: str) -> None:
        """Print warning message."""
        print(f"{self.YELLOW}{text}{self.RESET}")
        
    def print_error(self, text: str) -> None:
        """Print error message."""
        print(f"{self.RED}{text}{self.RESET}", file=sys.stderr)
        
    def print_status(self, text: str) -> None:
        """Print status message."""
        print(f"{self.BLUE}{text}{self.RESET}")
        
    def get_input(self, prompt: str) -> str:
        """Get user input with prompt."""
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nOperation cancelled.")
            sys.exit(0)
            
    def print_separator(self) -> None:
        """Print a separator line."""
        print("─" * 50)
```

### 3. CLI Integration

#### Update `src/prompter/cli/arguments.py`:
```python
# Remove --smart and --interactive arguments
# Keep only:
parser.add_argument(
    "--init",
    help="Generate a configuration file with AI assistance (specify filename, defaults to 'prompter.toml')",
    nargs="?",
    const="prompter.toml",
)
```

#### Update `src/prompter/cli/main.py`:
```python
# Replace init handling:
if args.init:
    from .init.generator import ConfigGenerator
    generator = ConfigGenerator(args.init)
    generator.generate()
    return 0
```

### 4. Error Handling Strategy

The error handling is simplified to fail fast with clear guidance:

1. **Missing Claude SDK**: Show installation instructions and exit
2. **Analysis Timeout**: Clear error message with retry suggestion
3. **Other Failures**: Descriptive error with troubleshooting steps

No fallbacks to pattern detection or static templates - the feature requires AI to work properly.

### 5. Testing Strategy

#### Unit Tests Structure:
```python
# tests/test_init/
├── test_generator.py      # Main orchestration tests
├── test_analyzer.py       # AI analysis tests (mocked)
├── test_interactive.py    # Interactive flow tests
└── test_integration.py    # End-to-end tests

# Example tests:
def test_missing_claude_sdk(capsys):
    """Test error when Claude SDK not available."""
    with patch.dict('sys.modules', {'claude_code_sdk': None}):
        generator = ConfigGenerator("test.toml")
        with pytest.raises(SystemExit) as exc:
            generator.generate()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Claude Code SDK is required" in captured.out

def test_full_flow_with_ai(mock_claude_sdk, tmp_path):
    """Test complete flow with AI analysis."""
    # Setup mock responses
    mock_claude_sdk.query.return_value = mock_analysis_response()
    
    # Run generator
    with patch('builtins.input', side_effect=['c', 'y', 'n', 'pytest -xvs']):
        generator = ConfigGenerator("test.toml")
        generator.generate()
        
    # Verify output
    assert (tmp_path / "test.toml").exists()
    config = tomllib.loads((tmp_path / "test.toml").read_text())
    assert "fix_test_failures" in [t["name"] for t in config["tasks"]]
```

### 6. Performance Optimizations

1. **Streaming Results**: Show progress as AI analysis proceeds
2. **Timeout Management**: 30s timeout with clear error handling
3. **Minimal File Reading**: AI does targeted analysis, not full scan
4. **Response Caching**: Cache analysis for immediate re-runs (5 min TTL)

### 7. User Experience Enhancements

#### Progress Indicators:
```python
def show_analysis_progress(self):
    """Show animated progress during analysis."""
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    # Animate while analysis runs
```

#### Helpful Error Messages:
```
❌ Build command failed: make
   
   This might be because:
   • The Makefile has different targets
   • Dependencies aren't installed
   • You need a different build command
   
   Try running 'make help' to see available targets
```

#### Success Celebration:
```
✅ Configuration saved to: prompter.toml

🎉 Your personalized configuration is ready!

📚 Resources to help you get started:
   • Documentation: https://github.com/YourOrg/prompter
   • Example workflows: cat prompter.toml
   • Community configs: prompter --examples

🚀 Next steps:
   1. Review: cat prompter.toml
   2. Test: prompter prompter.toml --dry-run  
   3. Run: prompter prompter.toml
```

## Migration Path

### Phase 1: Implementation (v0.7.0)
1. Implement core generator with AI analysis
2. Add pattern-based fallback
3. Create interactive customization
4. Bundle resources properly
5. Update CLI integration

### Phase 2: Polish (v0.8.0)
1. Enhance progress indicators
2. Add more language templates
3. Improve error messages
4. Add configuration validation

### Phase 3: Advanced Features (v0.9.0)
1. Configuration sharing platform
2. Team templates
3. Plugin system for analyzers
4. Web-based configurator

## Breaking Changes

This is a breaking change from the previous `--init` behavior:

- **Old behavior**: Generated static template file
- **New behavior**: Requires Claude SDK and performs AI analysis

Users who need the old static templates should:
1. Use example files from the repository
2. Copy templates from documentation
3. Use an older version of prompter

No backwards compatibility flags are provided to keep the implementation clean.

## Security Considerations

1. **Sandboxed Analysis**: AI runs with read-only permissions
2. **Command Validation**: Verify commands before adding to config
3. **No Secrets**: Never include credentials or tokens
4. **User Confirmation**: Always require explicit approval

## Conclusion

This revised plan creates a focused, AI-powered `--init` experience that delivers immediate value. By requiring Claude SDK and removing fallbacks, we ensure users get the full intelligent configuration experience. The simplified design is easier to implement, test, and maintain while providing a delightful user experience for those who have properly set up their Claude Code environment.