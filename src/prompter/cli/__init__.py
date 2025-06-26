"""CLI package for the prompter tool."""

from .arguments import create_parser
from .main import main
from .status import print_status

__all__ = ["create_parser", "main", "print_status"]
