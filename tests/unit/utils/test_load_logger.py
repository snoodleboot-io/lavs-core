"""Tests for the application logger loader."""

import logging

from app.utils.load_logger import load_logger


class TestLoadLogger:
    """``load_logger`` hands back the shared application logger."""

    def test_returns_the_lavs_api_logger(self) -> None:
        """The loader returns the logger registered under ``lavs-api``."""
        # Act
        logger = load_logger()

        # Assert
        assert isinstance(logger, logging.Logger)
        assert logger.name == "lavs-api"

    def test_repeated_calls_return_the_same_logger_instance(self) -> None:
        """Every call resolves to the same shared logger, not a fresh one."""
        # Act
        first = load_logger()
        second = load_logger()

        # Assert
        assert first is second
