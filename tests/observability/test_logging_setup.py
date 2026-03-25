"""Tests for logging setup / init_logging."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from processpype.config.models import ContextConfig, LoggingConfig, RedactionConfig
from processpype.observability.logging.filters import ContextFilter, RedactionFilter
from processpype.observability.logging.setup import init_logging


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


def _write_dictconfig_yaml(path: Path, config_dict: dict) -> None:
    """Helper to write a dictConfig YAML file."""
    path.write_text(yaml.dump(config_dict, default_flow_style=False))


def _minimal_dictconfig(extra: dict | None = None) -> dict:
    """Return a minimal valid dictConfig dict, merged with extras."""
    base = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {"level": "DEBUG", "handlers": ["console"]},
    }
    if extra:
        for key, value in extra.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                base[key].update(value)
            else:
                base[key] = value
    return base


class TestInitLoggingConfigFile:
    """Tests for config_file mode of init_logging."""

    def test_config_file_loads_and_applies(self, tmp_path):
        """Provide a dictConfig YAML with a file handler, verify it's created."""
        log_file = tmp_path / "app.log"
        config_dict = _minimal_dictconfig(
            {
                "handlers": {
                    "file": {
                        "class": "logging.FileHandler",
                        "filename": str(log_file),
                        "level": "DEBUG",
                    }
                },
                "root": {"level": "DEBUG", "handlers": ["file"]},
            }
        )
        config_path = tmp_path / "logging.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="logging.yml",
            level="DEBUG",
            redaction=RedactionConfig(enabled=False),
            context=ContextConfig(enabled=False),
        )
        init_logging(cfg, conf_dir=tmp_path)

        # Verify a FileHandler was created
        assert any(isinstance(h, logging.FileHandler) for h in root.handlers)

        # Verify log output reaches the file
        logging.getLogger("test.config_file").info("hello from config_file test")
        for h in root.handlers:
            h.flush()
        assert "hello from config_file test" in log_file.read_text()

    def test_config_file_level_override(self, tmp_path):
        """dictConfig sets root to DEBUG, but LoggingConfig.level=WARNING overrides."""
        config_dict = _minimal_dictconfig()
        config_path = tmp_path / "logging.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="logging.yml",
            level="WARNING",
            redaction=RedactionConfig(enabled=False),
            context=ContextConfig(enabled=False),
        )
        init_logging(cfg, conf_dir=tmp_path)

        assert root.level == logging.WARNING

    def test_config_file_loggers_override(self, tmp_path):
        """Per-logger overrides from LoggingConfig.loggers win over dictConfig."""
        config_dict = _minimal_dictconfig(
            {
                "loggers": {
                    "my.lib": {"level": "DEBUG", "handlers": ["console"]},
                },
            }
        )
        config_path = tmp_path / "logging.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="logging.yml",
            loggers={"my.lib": "WARNING"},
            redaction=RedactionConfig(enabled=False),
            context=ContextConfig(enabled=False),
        )
        init_logging(cfg, conf_dir=tmp_path)

        assert logging.getLogger("my.lib").level == logging.WARNING

    def test_config_file_redaction_and_context_filters(self, tmp_path):
        """Verify redaction and context filters are added to dictConfig handlers."""
        config_dict = _minimal_dictconfig()
        config_path = tmp_path / "logging.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="logging.yml",
            redaction=RedactionConfig(enabled=True),
            context=ContextConfig(enabled=True),
        )
        init_logging(cfg, conf_dir=tmp_path)

        for handler in root.handlers:
            filter_types = {type(f) for f in handler.filters}
            assert RedactionFilter in filter_types
            assert ContextFilter in filter_types

    def test_config_file_no_duplicate_filters(self, tmp_path):
        """Filters already in dictConfig should not be duplicated."""
        config_dict = _minimal_dictconfig(
            {
                "filters": {
                    "redact": {
                        "()": "processpype.observability.logging.filters.RedactionFilter",
                    },
                    "ctx": {
                        "()": "processpype.observability.logging.filters.ContextFilter",
                    },
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "DEBUG",
                        "stream": "ext://sys.stdout",
                        "filters": ["redact", "ctx"],
                    },
                },
            }
        )
        config_path = tmp_path / "logging.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="logging.yml",
            redaction=RedactionConfig(enabled=True),
            context=ContextConfig(enabled=True),
        )
        init_logging(cfg, conf_dir=tmp_path)

        for handler in root.handlers:
            redaction_count = sum(
                1 for f in handler.filters if isinstance(f, RedactionFilter)
            )
            context_count = sum(
                1 for f in handler.filters if isinstance(f, ContextFilter)
            )
            assert redaction_count == 1
            assert context_count == 1

    def test_config_file_not_found(self, tmp_path):
        """Missing config_file should raise FileNotFoundError."""
        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="nonexistent.yml",
        )
        with pytest.raises(FileNotFoundError):
            init_logging(cfg, conf_dir=tmp_path)

    def test_config_file_token_replacement(self, tmp_path, monkeypatch):
        """Verify $PROJECT_DIR token is replaced in handler filenames."""
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        config_dict = _minimal_dictconfig(
            {
                "handlers": {
                    "file": {
                        "class": "logging.FileHandler",
                        "filename": "$PROJECT_DIR/tokens.log",
                        "level": "DEBUG",
                    }
                },
                "root": {"level": "DEBUG", "handlers": ["file"]},
            }
        )
        config_path = tmp_path / "logging.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="logging.yml",
            redaction=RedactionConfig(enabled=False),
            context=ContextConfig(enabled=False),
        )
        init_logging(cfg, conf_dir=tmp_path)

        # Verify the file handler points to the resolved path
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert str(tmp_path) in file_handlers[0].baseFilename

    def test_config_file_relative_path(self, tmp_path):
        """Relative config_file is resolved against conf_dir."""
        sub_dir = tmp_path / "conf"
        sub_dir.mkdir()
        config_dict = _minimal_dictconfig()
        _write_dictconfig_yaml(sub_dir / "log.yml", config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file="log.yml",
            redaction=RedactionConfig(enabled=False),
            context=ContextConfig(enabled=False),
        )
        init_logging(cfg, conf_dir=sub_dir)
        assert len(root.handlers) >= 1

    def test_config_file_absolute_path(self, tmp_path):
        """Absolute config_file path is used directly, ignoring conf_dir."""
        config_dict = _minimal_dictconfig()
        config_path = tmp_path / "absolute_log.yml"
        _write_dictconfig_yaml(config_path, config_dict)

        root = logging.getLogger()
        root.handlers.clear()

        cfg = LoggingConfig(
            enabled=True,
            config_file=str(config_path),
            redaction=RedactionConfig(enabled=False),
            context=ContextConfig(enabled=False),
        )
        # Pass a different conf_dir to prove it's ignored
        init_logging(cfg, conf_dir=tmp_path / "other")
        assert len(root.handlers) >= 1
