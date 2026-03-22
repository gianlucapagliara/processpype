"""Logging initialisation for ProcessPype observability."""

from __future__ import annotations

import logging
import logging.config
import os
from pathlib import Path
from typing import Any

from processpype.config.models import LoggingConfig as LoggingModelConfig
from processpype.observability.logging.config import (
    load_logging_config,
)
from processpype.observability.logging.context import set_log_context
from processpype.observability.logging.levels import register_runtime_levels


def _ensure_handler_directories(config_dict: dict[str, Any]) -> None:
    handlers = config_dict.get("handlers", {})
    for handler_config in handlers.values():
        if not isinstance(handler_config, dict):
            continue
        filename = handler_config.get("filename")
        if not isinstance(filename, str) or filename.strip() == "":
            continue
        Path(filename).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def init_logging_from_file(
    conf_filename: str,
    strategy_file_path: str = "application",
    file_dir: str | None = None,
    replace_mapping: dict[str, str] | None = None,
) -> None:
    """Initialize logging from a dictConfig YAML file."""
    register_runtime_levels()

    config_dict, runtime_context = load_logging_config(
        conf_filename=conf_filename,
        strategy_file_path=strategy_file_path,
        file_dir=file_dir,
        replace_mapping=replace_mapping,
    )

    _ensure_handler_directories(config_dict)
    logging.raiseExceptions = False
    logging.config.dictConfig(config_dict)
    set_log_context(
        strategy_code=runtime_context.strategy_code,
        run_id=runtime_context.run_id,
        instance_id=runtime_context.instance_id,
        environment=runtime_context.environment,
    )


def resolve_logs_config_path(
    config: LoggingModelConfig,
    *,
    conf_dir: Path | None = None,
) -> Path | None:
    """Return the effective logging dictConfig YAML path, or None."""
    # Check for explicit handler config files in the config model
    if hasattr(config, "config_file") and config.config_file is not None:
        candidate = Path(config.config_file)
        if not candidate.is_absolute() and conf_dir is not None:
            candidate = conf_dir / candidate
        return candidate if candidate.exists() else None

    logs_path_str = os.getenv("LOGS_YAML")
    if logs_path_str:
        candidate = Path(logs_path_str)
        if not candidate.is_absolute() and conf_dir is not None:
            candidate = conf_dir.parent / candidate
        return candidate if candidate.exists() else None

    if conf_dir is not None:
        candidate = conf_dir / "logs_local.yml"
        return candidate if candidate.exists() else None

    return None


def init_logging(
    config: LoggingModelConfig,
    *,
    conf_dir: Path | None = None,
) -> None:
    """Configure Python logging from the ObservabilityConfig.logging section."""
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
