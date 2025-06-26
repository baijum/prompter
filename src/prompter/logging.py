"""Logging configuration for the prompter tool."""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    verbose: bool = False,
    debug: bool = False,
) -> logging.Logger:
    """Set up logging configuration."""

    # Determine log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    if debug:
        numeric_level = logging.DEBUG
        # Enable debug logging for all prompter modules
        logging.getLogger("prompter").setLevel(logging.DEBUG)
    elif verbose:
        numeric_level = logging.DEBUG

    # Create logger
    logger = logging.getLogger("prompter")
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Create formatter
    if debug:
        # Extended format for debug mode with file location and function name
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d - [%(process)d:%(thread)d] - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d in %(funcName)s()] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Standard formatter for normal mode
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

    # Enable debug logging for third-party libraries when in debug mode
    if debug:
        # Log Claude SDK operations
        logging.getLogger("claude_code_sdk").setLevel(logging.DEBUG)
        # Log asyncio operations
        logging.getLogger("asyncio").setLevel(
            logging.WARNING
        )  # Keep at WARNING to avoid noise

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"prompter.{name}")
