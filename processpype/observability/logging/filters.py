"""Logging filters: context injection and secret redaction."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from processpype.observability.logging.context import get_log_context

DEFAULT_SECRET_PATTERNS = (
    r"(?i)(password|passwd|pwd)\s*[:=]\s*([^\s,;]+)",
    r"(?i)(api[_-]?key)\s*[:=]\s*([^\s,;]+)",
    r"(?i)(secret)\s*[:=]\s*([^\s,;]+)",
    r"(?i)(token)\s*[:=]\s*([^\s,;]+)",
    r"(?i)(authorization)\s*[:=]\s*([^\s,;]+)",
)


class ContextFilter(logging.Filter):
    """Injects async-safe context from ContextVar into log records."""

    def __init__(self, name: str = "", static_context: Mapping[str, Any] | None = None):
        super().__init__(name=name)
        self._static_context = dict(static_context or {})

    def filter(self, record: logging.LogRecord) -> bool:
        context = {**self._static_context, **get_log_context()}
        for key, value in context.items():
            if value is not None and not hasattr(record, key):
                setattr(record, key, value)
        return True


class RedactionFilter(logging.Filter):
    """Pattern-based secret masking for log records."""

    def __init__(
        self,
        name: str = "",
        patterns: list[str] | None = None,
        replacement: str = "***",
    ):
        super().__init__(name=name)
        active_patterns = patterns or list(DEFAULT_SECRET_PATTERNS)
        self._patterns = [re.compile(pattern) for pattern in active_patterns]
        self._replacement = replacement

    def _redact_text(self, value: str) -> str:
        redacted = value
        for pattern in self._patterns:
            redacted = pattern.sub(r"\1=" + self._replacement, redacted)
        return redacted

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact_text(value)
        if isinstance(value, Mapping):
            return {k: self._redact_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact_value(item) for item in value)
        if isinstance(value, set):
            return {self._redact_value(item) for item in value}
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact_text(record.msg)

        if record.args:
            record.args = self._redact_value(record.args)

        for attr in ("extra", "metadata", "dict_msg"):
            if hasattr(record, attr):
                setattr(record, attr, self._redact_value(getattr(record, attr)))

        return True
