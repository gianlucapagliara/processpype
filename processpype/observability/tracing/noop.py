"""No-op tracer and span stubs for when tracing is disabled."""

from __future__ import annotations

from typing import Any


class NoOpSpan:
    """Minimal stub returned when tracing is disabled."""

    def set_attribute(self, key: str, value: object) -> None:
        pass

    def set_status(self, *args: object, **kwargs: object) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass

    def is_recording(self) -> bool:
        return False

    def __enter__(self) -> NoOpSpan:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class NoOpTracer:
    """Tracer stub used when tracing is disabled."""

    def start_as_current_span(
        self, name: str, *, attributes: dict[str, Any] | None = None, **kwargs: object
    ) -> NoOpSpan:
        return NoOpSpan()

    def start_span(
        self, name: str, *, attributes: dict[str, Any] | None = None, **kwargs: object
    ) -> NoOpSpan:
        return NoOpSpan()
