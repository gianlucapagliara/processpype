"""Tests for NoOpSpan and NoOpTracer."""

from processpype.observability.tracing.noop import NoOpSpan, NoOpTracer


class TestNoOpSpan:
    def test_set_attribute(self):
        span = NoOpSpan()
        span.set_attribute("key", "value")  # should not raise

    def test_set_status(self):
        span = NoOpSpan()
        span.set_status(0, "ok")

    def test_record_exception(self):
        span = NoOpSpan()
        span.record_exception(RuntimeError("boom"))

    def test_add_event(self):
        span = NoOpSpan()
        span.add_event("event_name")
        span.add_event("event_name", attributes={"k": "v"})

    def test_is_recording(self):
        span = NoOpSpan()
        assert span.is_recording() is False

    def test_context_manager(self):
        span = NoOpSpan()
        with span as s:
            assert s is span


class TestNoOpTracer:
    def test_start_as_current_span(self):
        tracer = NoOpTracer()
        span = tracer.start_as_current_span("test")
        assert isinstance(span, NoOpSpan)

    def test_start_as_current_span_with_attributes(self):
        tracer = NoOpTracer()
        span = tracer.start_as_current_span("test", attributes={"k": "v"})
        assert isinstance(span, NoOpSpan)

    def test_start_span(self):
        tracer = NoOpTracer()
        span = tracer.start_span("test")
        assert isinstance(span, NoOpSpan)

    def test_start_span_with_attributes(self):
        tracer = NoOpTracer()
        span = tracer.start_span("test", attributes={"k": "v"})
        assert isinstance(span, NoOpSpan)

    def test_start_as_current_span_usable_as_context_manager(self):
        tracer = NoOpTracer()
        with tracer.start_as_current_span("test") as span:
            assert isinstance(span, NoOpSpan)
