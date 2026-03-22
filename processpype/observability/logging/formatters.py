"""Log formatters: text, colored, and structured JSON."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_RESERVED_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class TextFormatter(logging.Formatter):
    DEFAULT_FORMAT = (
        "%(asctime)s - %(levelname)s - %(name)s - %(module)s:%(lineno)d | %(message)s"
    )

    def __init__(self, fmt: str | None = None, datefmt: str | None = None):
        super().__init__(fmt=fmt or self.DEFAULT_FORMAT, datefmt=datefmt)


class ColorFormatter(TextFormatter):
    _RESET = "\x1b[0m"
    _COLORS = {
        5: "\x1b[34;20m",  # TRACE
        logging.DEBUG: "\x1b[37;20m",
        logging.INFO: "\x1b[32;20m",
        15: "\x1b[36;20m",  # TRACK
        16: "\x1b[35;20m",  # NETWORK
        17: "\x1b[36;1m",  # EVENT_LOG
        logging.WARNING: "\x1b[33;20m",
        logging.ERROR: "\x1b[31;20m",
        logging.CRITICAL: "\x1b[31;1m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelno, "")
        rendered = super().format(record)
        if not color:
            return rendered
        return f"{color}{rendered}{self._RESET}"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        for context_field in ("strategy_code", "run_id", "instance_id", "environment"):
            value = getattr(record, context_field, None)
            if value is not None:
                payload[context_field] = value

        extra_payload = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED_RECORD_ATTRS and not key.startswith("_")
        }
        payload.update(extra_payload)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(payload, default=str, ensure_ascii=True)
