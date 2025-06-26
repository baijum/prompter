"""Command-line interface for the prompter tool.

This module serves as a thin wrapper around the CLI package for backward compatibility.
The actual implementation has been split into multiple modules in the cli package.
"""

# Re-export main components for backward compatibility
from .cli.arguments import create_parser
from .cli.main import main
from .cli.status import print_status

# Keep all imports available for existing code
__all__ = ["create_parser", "main", "print_status"]


if __name__ == "__main__":
    import sys

    sys.exit(main())
