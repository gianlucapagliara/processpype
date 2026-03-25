"""Logging initialisation for ProcessPype observability."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

from processpype.config.models import LoggingConfig as LoggingModelConfig
from processpype.observability.logging.levels import register_runtime_levels


def init_logging(
    config: LoggingModelConfig,
    *,
    conf_dir: Path | None = None,
) -> None:
    """Configure Python logging from the ObservabilityConfig.logging section."""
    if not config.enabled:
        return

    register_runtime_levels()

    # Register custom levels from config
    for level_name, level_num in config.custom_levels.items():
        logging.addLevelName(level_num, level_name.upper())

    if config.config_file:
        _init_from_dictconfig_file(config, conf_dir=conf_dir)
    else:
        _init_inline(config)

    # Always apply per-logger level overrides (works in both modes)
    for logger_name, logger_level in config.loggers.items():
        logging.getLogger(logger_name).setLevel(
            getattr(logging, logger_level.upper(), logging.INFO)
        )


def _init_from_dictconfig_file(
    config: LoggingModelConfig,
    *,
    conf_dir: Path | None = None,
) -> None:
    """Load a dictConfig YAML file and apply it."""
    from processpype.observability.logging.config import load_logging_config_from_path

    assert config.config_file is not None
    config_path = Path(config.config_file)
    if not config_path.is_absolute():
        base = conf_dir or Path.cwd()
        config_path = base / config_path

    config_dict, _ = load_logging_config_from_path(config_path)
    logging.config.dictConfig(config_dict)

    # Apply root level override (allows CLI --log-level to work)
    log_level = getattr(logging, config.level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)

    # Apply redaction/context filters to all handlers (if not already present)
    _ensure_filters_on_all_handlers(config)


def _init_inline(config: LoggingModelConfig) -> None:
    """Current behavior — StreamHandler with format choice."""
    from processpype.observability.logging.formatters import (
        ColorFormatter,
        JsonFormatter,
        TextFormatter,
    )

    log_level = getattr(logging, config.level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        if config.format == "json":
            handler.setFormatter(JsonFormatter())
        elif config.format == "color":
            handler.setFormatter(ColorFormatter())
        else:
            handler.setFormatter(TextFormatter())

        handler.setLevel(log_level)

        # Add redaction filter if enabled
        if config.redaction.enabled:
            from processpype.observability.logging.filters import RedactionFilter

            handler.addFilter(RedactionFilter(patterns=config.redaction.patterns))

        # Add context filter if enabled
        if config.context.enabled:
            from processpype.observability.logging.filters import ContextFilter

            handler.addFilter(ContextFilter())

        logging.basicConfig(level=log_level, handlers=[handler])

    root_logger.setLevel(log_level)


def _ensure_filters_on_all_handlers(config: LoggingModelConfig) -> None:
    """Add redaction and context filters to all root logger handlers if missing."""
    from processpype.observability.logging.filters import ContextFilter, RedactionFilter

    root = logging.getLogger()
    for handler in root.handlers:
        existing_types = {type(f) for f in handler.filters}
        if config.redaction.enabled and RedactionFilter not in existing_types:
            handler.addFilter(RedactionFilter(patterns=config.redaction.patterns))
        if config.context.enabled and ContextFilter not in existing_types:
            handler.addFilter(ContextFilter())
