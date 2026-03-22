"""Tests for logging setup / init_logging."""

from __future__ import annotations

import logging

import pytest
import yaml

from processpype.config.models import LoggingConfig
from processpype.observability.logging.setup import (
    _ensure_handler_directories,
    init_logging,
    init_logging_from_file,
)


@pytest.fixture(autouse=True)
def clean_root_logger():
    """Remove handlers added during tests."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.level = original_level


class TestInitLogging:
    def test_disabled_config_does_nothing(self):
        cfg = LoggingConfig(enabled=False)
        root = logging.getLogger()
        handler_count_before = len(root.handlers)
        init_logging(cfg)
        assert len(root.handlers) == handler_count_before

    def test_sets_root_log_level(self):
        # Clear handlers so init_logging installs new ones
        root = logging.getLogger()
        root.handlers.clear()
        cfg = LoggingConfig(enabled=True, level="WARNING")
        init_logging(cfg)
        assert root.level == logging.WARNING

    def test_color_format(self):
        root = logging.getLogger()
        root.handlers.clear()
        cfg = LoggingConfig(enabled=True, format="color")
        init_logging(cfg)
        from processpype.observability.logging.formatters import ColorFormatter

        assert any(isinstance(h.formatter, ColorFormatter) for h in root.handlers)

    def test_json_format(self):
        root = logging.getLogger()
        root.handlers.clear()
        cfg = LoggingConfig(enabled=True, format="json")
        init_logging(cfg)
        from processpype.observability.logging.formatters import JsonFormatter

        assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)

    def test_text_format(self):
        root = logging.getLogger()
        root.handlers.clear()
        cfg = LoggingConfig(enabled=True, format="text")
        init_logging(cfg)
        from processpype.observability.logging.formatters import TextFormatter

        assert any(isinstance(h.formatter, TextFormatter) for h in root.handlers)

    def test_per_logger_overrides(self):
        root = logging.getLogger()
        root.handlers.clear()
        cfg = LoggingConfig(
            enabled=True,
            loggers={"noisy.lib": "ERROR"},
        )
        init_logging(cfg)
        assert logging.getLogger("noisy.lib").level == logging.ERROR

    def test_custom_levels(self):
        root = logging.getLogger()
        root.handlers.clear()
        cfg = LoggingConfig(
            enabled=True,
            custom_levels={"CUSTOM_TEST_LEVEL": 35},
        )
        init_logging(cfg)
        assert logging.getLevelName(35) == "CUSTOM_TEST_LEVEL"

    def test_redaction_filter_added(self):
        root = logging.getLogger()
        root.handlers.clear()
        from processpype.config.models import RedactionConfig

        cfg = LoggingConfig(
            enabled=True,
            redaction=RedactionConfig(enabled=True),
        )
        init_logging(cfg)
        from processpype.observability.logging.filters import RedactionFilter

        filters_on_handlers = [
            f
            for h in root.handlers
            for f in h.filters
            if isinstance(f, RedactionFilter)
        ]
        assert len(filters_on_handlers) >= 1

    def test_context_filter_added(self):
        root = logging.getLogger()
        root.handlers.clear()
        from processpype.config.models import ContextConfig

        cfg = LoggingConfig(
            enabled=True,
            context=ContextConfig(enabled=True),
        )
        init_logging(cfg)
        from processpype.observability.logging.filters import ContextFilter

        filters_on_handlers = [
            f for h in root.handlers for f in h.filters if isinstance(f, ContextFilter)
        ]
        assert len(filters_on_handlers) >= 1

    def test_no_duplicate_handlers_when_handlers_exist(self):
        root = logging.getLogger()
        # Ensure there's already a handler
        root.addHandler(logging.StreamHandler())
        handler_count = len(root.handlers)
        cfg = LoggingConfig(enabled=True)
        init_logging(cfg)
        # Should not add more handlers since root already has some
        assert len(root.handlers) == handler_count


class TestEnsureHandlerDirectories:
    def test_creates_parent_directory(self, tmp_path):
        log_dir = tmp_path / "logs" / "subdir"
        config_dict = {
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_dir / "app.log"),
                }
            }
        }
        _ensure_handler_directories(config_dict)
        assert log_dir.exists()

    def test_ignores_non_dict_handlers(self):
        config_dict = {"handlers": {"bad": "not_a_dict"}}
        _ensure_handler_directories(config_dict)  # should not raise

    def test_ignores_handlers_without_filename(self):
        config_dict = {"handlers": {"console": {"class": "logging.StreamHandler"}}}
        _ensure_handler_directories(config_dict)  # should not raise

    def test_ignores_empty_filename(self):
        config_dict = {
            "handlers": {"file": {"class": "logging.FileHandler", "filename": "  "}}
        }
        _ensure_handler_directories(config_dict)  # should not raise

    def test_no_handlers_key(self):
        _ensure_handler_directories({})  # should not raise


class TestInitLoggingFromFile:
    def test_loads_and_configures(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()

        config_data = {
            "version": 1,
            "root": {"level": "DEBUG", "handlers": ["console"]},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                }
            },
        }
        config_file = conf_dir / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        init_logging_from_file("logging.yaml")

        from processpype.observability.logging.context import get_log_context

        ctx = get_log_context()
        assert "strategy_code" in ctx
        assert "run_id" in ctx

    def test_with_file_handler(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()
        log_file = tmp_path / "logs" / "app.log"

        config_data = {
            "version": 1,
            "root": {"level": "INFO", "handlers": ["file"]},
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_file),
                    "level": "INFO",
                }
            },
        }
        config_file = conf_dir / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        init_logging_from_file("logging.yaml")
        assert log_file.parent.exists()
