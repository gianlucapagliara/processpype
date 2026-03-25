"""Custom log levels for ProcessPype observability."""

from __future__ import annotations

import logging
from typing import Any

TRACE = logging.DEBUG - 5
TRACK = logging.DEBUG + 5
NETWORK = logging.DEBUG + 6
EVENT_LOG = logging.DEBUG + 7
METRIC_LOG = 14


def _add_level(level_name: str, level_num: int, method_name: str | None = None) -> None:
    if not method_name:
        method_name = level_name.lower()

    if not hasattr(logging, level_name):
        logging.addLevelName(level_num, level_name)
        setattr(logging, level_name, level_num)

    if not hasattr(logging.getLoggerClass(), method_name):

        def log_for_level(
            self: logging.Logger, message: str, *args: object, **kwargs: Any
        ) -> None:
            if self.isEnabledFor(level_num):
                self._log(level_num, message, args, **kwargs)

        setattr(logging.getLoggerClass(), method_name, log_for_level)

    if not hasattr(logging, method_name):

        def log_to_root(message: str, *args: object, **kwargs: Any) -> None:
            logging.log(level_num, message, *args, **kwargs)

        setattr(logging, method_name, log_to_root)


def register_runtime_levels() -> None:
    """Register all custom log levels with the logging module."""
    _add_level("TRACE", TRACE)
    _add_level("TRACK", TRACK)
    _add_level("NETWORK", NETWORK)
    _add_level("EVENT_LOG", EVENT_LOG, method_name="event_log")
    _add_level("METRIC_LOG", METRIC_LOG, method_name="metric_log")
