"""Async-safe log context using ContextVar."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_LOG_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "_LOG_CONTEXT", default=None
)


def get_log_context() -> dict[str, Any]:
    return dict(_LOG_CONTEXT.get() or {})


def set_log_context(**fields: Any) -> None:
    context = get_log_context()
    context.update({key: value for key, value in fields.items() if value is not None})
    _LOG_CONTEXT.set(context)


def clear_log_context(*keys: str) -> None:
    if keys:
        context = get_log_context()
        for key in keys:
            context.pop(key, None)
        _LOG_CONTEXT.set(context)
        return
    _LOG_CONTEXT.set({})
