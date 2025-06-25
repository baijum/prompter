"""Tests for the logging module."""

import logging
from unittest.mock import mock_open, patch

from prompter.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        logger = setup_logging()

        assert logger.name == "prompter"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_debug_level(self):
        """Test setup_logging with DEBUG level."""
        logger = setup_logging(level="DEBUG")

        assert logger.level == logging.DEBUG

    def test_setup_logging_verbose_flag(self):
        """Test setup_logging with verbose flag."""
        logger = setup_logging(verbose=True)

        assert logger.level == logging.DEBUG

    def test_setup_logging_with_file(self, temp_dir):
        """Test setup_logging with log file."""
        log_file = temp_dir / "test.log"
        logger = setup_logging(log_file=log_file)

        assert len(logger.handlers) == 2  # Console + file handler

        # Check that one handler is FileHandler
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid level defaults to INFO."""
        logger = setup_logging(level="INVALID")

        # Should default to INFO level
        assert logger.level == logging.INFO

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        # First setup
        logger1 = setup_logging()
        initial_handler_count = len(logger1.handlers)

        # Second setup should clear and recreate handlers
        logger2 = setup_logging()

        assert logger1 is logger2  # Same logger instance
        assert len(logger2.handlers) == initial_handler_count

    def test_logging_output_format(self, capsys):
        """Test that logging output uses correct format."""
        logger = setup_logging(level="DEBUG")

        logger.info("Test message")

        captured = capsys.readouterr()
        # Should contain timestamp, logger name, level, and message
        assert "prompter" in captured.out
        assert "INFO" in captured.out
        assert "Test message" in captured.out

    @patch("builtins.open", mock_open())
    def test_setup_logging_file_permissions(self, temp_dir):
        """Test setup_logging handles file creation properly."""
        log_file = temp_dir / "test.log"

        # Should not raise exception
        logger = setup_logging(log_file=log_file)

        # Should have file handler
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_basic(self):
        """Test basic get_logger functionality."""
        logger = get_logger("test_module")

        assert logger.name == "prompter.test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_different_modules(self):
        """Test get_logger with different module names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "prompter.module1"
        assert logger2.name == "prompter.module2"
        assert logger1 is not logger2

    def test_get_logger_same_module(self):
        """Test get_logger returns same instance for same module."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        assert logger1 is logger2

    def test_get_logger_inherits_from_parent(self):
        """Test that module loggers inherit from parent prompter logger."""
        # Setup parent logger
        parent_logger = setup_logging(level="DEBUG")

        # Get module logger
        module_logger = get_logger("test_module")

        # Module logger should inherit parent's configuration
        assert module_logger.getEffectiveLevel() == logging.DEBUG

    def test_logger_hierarchy(self):
        """Test logger hierarchy works correctly."""
        # Setup parent with specific handler
        parent_logger = setup_logging(level="WARNING")

        # Get child logger
        child_logger = get_logger("child")

        # Child should propagate to parent
        assert child_logger.parent == parent_logger

        # Test that messages propagate
        with patch.object(parent_logger, "handle") as mock_handle:
            child_logger.warning("Test warning")
            # Should eventually reach parent logger for handling


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_logging_in_real_scenario(self, temp_dir, capsys):
        """Test logging in a realistic scenario."""
        log_file = temp_dir / "integration.log"

        # Setup logging
        main_logger = setup_logging(level="INFO", log_file=log_file, verbose=False)

        # Get module loggers
        config_logger = get_logger("config")
        runner_logger = get_logger("runner")

        # Log some messages
        main_logger.info("Starting application")
        config_logger.info("Loading configuration")
        runner_logger.warning("Task failed, retrying")
        main_logger.info("Application finished")

        # Check console output
        captured = capsys.readouterr()
        assert "Starting application" in captured.out
        assert "Loading configuration" in captured.out
        assert "Task failed, retrying" in captured.out
        assert "Application finished" in captured.out

    def test_verbose_vs_normal_logging(self, capsys):
        """Test difference between verbose and normal logging."""
        # Normal logging (INFO level)
        normal_logger = setup_logging(level="INFO", verbose=False)
        normal_logger.debug("Debug message - should not appear")
        normal_logger.info("Info message - should appear")

        captured_normal = capsys.readouterr()
        assert "Debug message" not in captured_normal.out
        assert "Info message" in captured_normal.out

        # Verbose logging (DEBUG level)
        verbose_logger = setup_logging(level="INFO", verbose=True)
        verbose_logger.debug("Debug message - should appear")
        verbose_logger.info("Info message - should appear")

        captured_verbose = capsys.readouterr()
        assert "Debug message" in captured_verbose.out
        assert "Info message" in captured_verbose.out

    def test_multiple_loggers_same_file(self, temp_dir):
        """Test multiple loggers writing to same file."""
        log_file = temp_dir / "shared.log"

        # Create multiple loggers with same file
        logger1 = setup_logging(log_file=log_file)
        logger2 = get_logger("module1")
        logger3 = get_logger("module2")

        # All should be able to log
        logger1.info("Main logger message")
        logger2.info("Module1 message")
        logger3.info("Module2 message")

        # No exceptions should be raised
