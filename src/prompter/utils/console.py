"""Rich console output utilities."""

import sys


class Console:
    """Enhanced console output with formatting."""

    # ANSI color codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

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
