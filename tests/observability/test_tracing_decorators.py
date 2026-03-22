"""Tests for tracing decorators and context managers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from processpype.observability.tracing.decorators import (
    _record_error,
    add_span_event,
    should_trace,
    trace_action,
    trace_span,
)
from processpype.observability.tracing.noop import NoOpSpan


class TestShouldTrace:
    def test_returns_false_when_tracing_disabled(self):
        with patch(
            "processpype.observability.tracing.decorators.is_tracing_enabled",
            return_value=False,
        ):
            assert should_trace("test.span") is False

    def test_returns_true_when_enabled_and_no_filter(self):
        with (
            patch(
                "processpype.observability.tracing.decorators.is_tracing_enabled",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.setup._trace_filter",
                None,
            ),
        ):
            assert should_trace("test.span") is True

    def test_returns_filter_result_when_filter_set(self):
        mock_filter = MagicMock(return_value=False)
        with (
            patch(
                "processpype.observability.tracing.decorators.is_tracing_enabled",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.setup._trace_filter",
                mock_filter,
            ),
        ):
            assert should_trace("test.span") is False
            mock_filter.assert_called_once_with("test.span")

    def test_returns_true_when_filter_raises(self):
        mock_filter = MagicMock(side_effect=RuntimeError("boom"))
        with (
            patch(
                "processpype.observability.tracing.decorators.is_tracing_enabled",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.setup._trace_filter",
                mock_filter,
            ),
        ):
            assert should_trace("test.span") is True


class TestTraceAction:
    def test_sync_function_no_tracing(self):
        with patch(
            "processpype.observability.tracing.decorators.should_trace",
            return_value=False,
        ):

            @trace_action("test.action")
            def my_func(x: int) -> int:
                return x + 1

            assert my_func(5) == 6

    def test_sync_function_with_tracing(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
        ):

            @trace_action("test.action")
            def my_func(x: int) -> int:
                return x + 1

            assert my_func(5) == 6
            mock_tracer.start_as_current_span.assert_called_once()

    def test_sync_function_exception_records_error(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
            patch(
                "processpype.observability.tracing.decorators._record_error"
            ) as mock_record,
        ):

            @trace_action("test.action")
            def failing():
                raise ValueError("oops")

            with pytest.raises(ValueError, match="oops"):
                failing()

            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_function_no_tracing(self):
        with patch(
            "processpype.observability.tracing.decorators.should_trace",
            return_value=False,
        ):

            @trace_action("test.action")
            async def my_func(x: int) -> int:
                return x + 1

            assert await my_func(5) == 6

    @pytest.mark.asyncio
    async def test_async_function_with_tracing(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
        ):

            @trace_action("test.action")
            async def my_func(x: int) -> int:
                return x + 1

            assert await my_func(5) == 6
            mock_tracer.start_as_current_span.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_function_exception_records_error(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
            patch(
                "processpype.observability.tracing.decorators._record_error"
            ) as mock_record,
        ):

            @trace_action("test.action")
            async def failing():
                raise ValueError("oops")

            with pytest.raises(ValueError, match="oops"):
                await failing()

            mock_record.assert_called_once()

    def test_extract_attrs(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
        ):

            @trace_action("test.action", extract_attrs={"user.id": "user_id"})
            def my_func(user_id: str) -> str:
                return user_id

            my_func("abc123")
            call_kwargs = mock_tracer.start_as_current_span.call_args
            assert call_kwargs[1]["attributes"] == {"user.id": "abc123"}


class TestTraceSpan:
    def test_trace_span_disabled(self):
        with patch(
            "processpype.observability.tracing.decorators.should_trace",
            return_value=False,
        ):
            with trace_span("test.span") as span:
                assert isinstance(span, NoOpSpan)

    def test_trace_span_enabled(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
        ):
            with trace_span("test.span", attributes={"k": "v"}) as span:
                assert span is mock_span

    def test_trace_span_exception_records_error(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch(
                "processpype.observability.tracing.decorators.get_tracer",
                return_value=mock_tracer,
            ),
            patch(
                "processpype.observability.tracing.decorators._record_error"
            ) as mock_record,
        ):
            with pytest.raises(ValueError, match="boom"):
                with trace_span("test.span"):
                    raise ValueError("boom")
            mock_record.assert_called_once()


class TestAddSpanEvent:
    def test_no_trace(self):
        with patch(
            "processpype.observability.tracing.decorators.should_trace",
            return_value=False,
        ):
            add_span_event("event")  # should not raise

    def test_with_tracing_and_recording_span(self):
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_trace_mod = MagicMock()
        mock_trace_mod.get_current_span.return_value = mock_span

        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch.dict(
                "sys.modules",
                {"opentelemetry": MagicMock(trace=mock_trace_mod)},
            ),
        ):
            add_span_event("my_event", attributes={"a": "b"})
            mock_span.add_event.assert_called_once_with(
                "my_event", attributes={"a": "b"}
            )

    def test_silently_handles_import_error(self):
        with (
            patch(
                "processpype.observability.tracing.decorators.should_trace",
                return_value=True,
            ),
            patch.dict(
                "sys.modules",
                {"opentelemetry": None},
            ),
        ):
            # Should not raise
            add_span_event("event")


class TestRecordError:
    def test_record_error_with_otel_status_code(self):
        mock_span = MagicMock()
        exc = RuntimeError("test error")
        mock_status = MagicMock()
        mock_status.ERROR = "ERROR_STATUS"
        mock_otel_trace = MagicMock(StatusCode=mock_status)

        with patch.dict("sys.modules", {"opentelemetry.trace": mock_otel_trace}):
            _record_error(mock_span, exc)
            mock_span.set_status.assert_called_once_with("ERROR_STATUS", "test error")
            mock_span.record_exception.assert_called_once_with(exc)

    def test_record_error_fallback_when_import_fails(self):
        mock_span = MagicMock()
        exc = RuntimeError("test error")
        # When opentelemetry.trace import fails, falls back to ERROR_STATUS_CODE=2
        with patch.dict("sys.modules", {"opentelemetry.trace": None}):
            _record_error(mock_span, exc)
            mock_span.set_status.assert_called_once_with(2, "test error")
            mock_span.record_exception.assert_called_once_with(exc)
