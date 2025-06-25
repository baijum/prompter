"""Logging configuration for the prompter tool."""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """Set up logging configuration."""

    # Determine log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    if verbose:
        numeric_level = logging.DEBUG

    # Create logger
    logger = logging.getLogger("prompter")
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"prompter.{name}")
