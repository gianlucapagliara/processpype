"""Unified observability for ProcessPype: logging + tracing."""

import logging as _logging

from processpype.observability.logging import (
    init_logging,
)
from processpype.observability.setup import init_observability
from processpype.observability.tracing import (
    add_span_event,
    get_tracer,
    get_tracing_config,
    is_tracing_enabled,
    register_trace_filter,
    setup_tracing,
    trace_action,
    trace_span,
)


def get_logger(name: str, prefix: str = "processpype") -> _logging.Logger:
    """Get a named logger under the processpype hierarchy."""
    full_name = f"{prefix}.{name}" if prefix else name
    return _logging.getLogger(full_name)


__all__ = [
    "add_span_event",
    "get_logger",
    "get_tracer",
    "get_tracing_config",
    "init_logging",
    "init_observability",
    "is_tracing_enabled",
    "register_trace_filter",
    "setup_tracing",
    "trace_action",
    "trace_span",
]
