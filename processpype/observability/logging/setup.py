"""Logging initialisation for ProcessPype observability."""

from __future__ import annotations

import logging
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

    log_level = getattr(logging, config.level.upper(), logging.INFO)

    # Register custom levels from config
    for level_name, level_num in config.custom_levels.items():
        logging.addLevelName(level_num, level_name.upper())

    # If no external config file, set up basic logging with the chosen format
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        from processpype.observability.logging.formatters import (
            ColorFormatter,
            JsonFormatter,
            TextFormatter,
        )

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

    # Apply per-logger level overrides
    for logger_name, logger_level in config.loggers.items():
        logging.getLogger(logger_name).setLevel(
            getattr(logging, logger_level.upper(), logging.INFO)
        )
