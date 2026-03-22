"""Tracing subsystem for ProcessPype observability."""

from processpype.observability.tracing.decorators import (
    _should_trace,
    add_span_event,
    trace_action,
    trace_span,
)
from processpype.observability.tracing.noop import NoOpSpan, NoOpTracer
from processpype.observability.tracing.setup import (
    get_tracer,
    get_tracing_config,
    is_tracing_enabled,
    register_trace_filter,
    setup_tracing,
)

__all__ = [
    "NoOpSpan",
    "NoOpTracer",
    "_should_trace",
    "add_span_event",
    "get_tracer",
    "get_tracing_config",
    "is_tracing_enabled",
    "register_trace_filter",
    "setup_tracing",
    "trace_action",
    "trace_span",
]
