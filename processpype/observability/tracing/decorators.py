"""Tracing decorators and context managers."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from processpype.observability.tracing.noop import NoOpSpan
from processpype.observability.tracing.setup import get_tracer, is_tracing_enabled

ERROR_STATUS_CODE = 2


def should_trace(name: str) -> bool:
    """Check if tracing is enabled for the given span/event name."""
    if not is_tracing_enabled():
        return False

    from processpype.observability.tracing.setup import _trace_filter

    if _trace_filter is None:
        return True

    try:
        return bool(_trace_filter(name))
    except Exception:
        return True


def _extract_attributes(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    extract_attrs: dict[str, str] | None,
) -> dict[str, Any]:
    if not extract_attrs:
        return {}

    sig = inspect.signature(func)
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()

    attrs: dict[str, Any] = {}
    for attr_name, param_name in extract_attrs.items():
        value = bound.arguments.get(param_name)
        if value is not None:
            attrs[attr_name] = str(value)
    return attrs


def trace_action(
    name: str,
    *,
    extract_attrs: dict[str, str] | None = None,
) -> Callable[..., Any]:
    """Decorator that wraps a function in an OTEL span."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not should_trace(name):
                    return await func(*args, **kwargs)
                tracer = get_tracer()
                attrs = _extract_attributes(func, args, kwargs, extract_attrs)
                with tracer.start_as_current_span(name, attributes=attrs) as span:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        _record_error(span, exc)
                        raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not should_trace(name):
                return func(*args, **kwargs)
            tracer = get_tracer()
            attrs = _extract_attributes(func, args, kwargs, extract_attrs)
            with tracer.start_as_current_span(name, attributes=attrs) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    _record_error(span, exc)
                    raise

        return sync_wrapper

    return decorator


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Context manager that creates a child span."""
    if not should_trace(name):
        yield NoOpSpan()
        return

    tracer = get_tracer()
    with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        try:
            yield span
        except Exception as exc:
            _record_error(span, exc)
            raise


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """Record an event on the currently active span (if any)."""
    if not should_trace(name):
        return

    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span is not None and span.is_recording():
            span.add_event(name, attributes=attributes or {})
    except Exception:
        pass


def _record_error(span: Any, exc: Exception) -> None:
    try:
        from opentelemetry.trace import StatusCode

        span.set_status(StatusCode.ERROR, str(exc))
        span.record_exception(exc)
    except Exception:
        span.set_status(ERROR_STATUS_CODE, str(exc))
        span.record_exception(exc)
