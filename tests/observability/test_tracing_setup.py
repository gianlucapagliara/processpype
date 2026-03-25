"""Tests for tracing setup module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from processpype.config.models import LogfireConfig, TracingConfig
from processpype.observability.tracing import setup as tracing_setup_module
from processpype.observability.tracing.noop import NoOpTracer


@pytest.fixture(autouse=True)
def reset_tracing_globals():
    """Reset module-level globals before each test."""
    tracing_setup_module._tracing_enabled = False
    tracing_setup_module._tracer = None
    tracing_setup_module._config = None
    tracing_setup_module._trace_filter = None
    yield
    tracing_setup_module._tracing_enabled = False
    tracing_setup_module._tracer = None
    tracing_setup_module._config = None
    tracing_setup_module._trace_filter = None


class TestGetTracer:
    def test_returns_noop_when_no_tracer_set(self):
        tracer = tracing_setup_module.get_tracer()
        assert isinstance(tracer, NoOpTracer)

    def test_returns_same_tracer_on_subsequent_calls(self):
        t1 = tracing_setup_module.get_tracer()
        t2 = tracing_setup_module.get_tracer()
        assert t1 is t2


class TestIsTracingEnabled:
    def test_false_by_default(self):
        assert tracing_setup_module.is_tracing_enabled() is False

    def test_true_after_successful_setup(self):
        tracing_setup_module._tracing_enabled = True
        assert tracing_setup_module.is_tracing_enabled() is True


class TestRegisterTraceFilter:
    def test_register_filter(self):
        def fn(name: str) -> bool:
            return name.startswith("x")

        tracing_setup_module.register_trace_filter(fn)
        assert tracing_setup_module._trace_filter is fn

    def test_register_none_clears_filter(self):
        tracing_setup_module._trace_filter = lambda n: True
        tracing_setup_module.register_trace_filter(None)
        assert tracing_setup_module._trace_filter is None


class TestGetTracingConfig:
    def test_none_by_default(self):
        assert tracing_setup_module.get_tracing_config() is None

    def test_returns_config_after_setup(self):
        cfg = TracingConfig(enabled=False)
        tracing_setup_module._config = cfg
        assert tracing_setup_module.get_tracing_config() is cfg


class TestSetupTracing:
    def test_disabled_config_sets_noop_tracer(self):
        cfg = TracingConfig(enabled=False)
        tracing_setup_module.setup_tracing(cfg)
        assert isinstance(tracing_setup_module._tracer, NoOpTracer)
        assert tracing_setup_module._tracing_enabled is False

    def test_already_initialised_skips(self):
        tracing_setup_module._tracing_enabled = True
        cfg = TracingConfig(enabled=True)
        tracing_setup_module.setup_tracing(cfg)
        # Should not raise, just skip

    def test_otel_failure_falls_back_to_noop(self):
        cfg = TracingConfig(enabled=True, backend="console", service_name="test")
        with patch.object(
            tracing_setup_module,
            "_setup_otel",
            side_effect=ImportError("no otel"),
        ):
            tracing_setup_module.setup_tracing(cfg)
        assert isinstance(tracing_setup_module._tracer, NoOpTracer)
        assert tracing_setup_module._tracing_enabled is False

    def test_successful_setup_enables_tracing(self):
        cfg = TracingConfig(enabled=True, backend="console", service_name="test")
        with patch.object(tracing_setup_module, "_setup_otel"):
            tracing_setup_module.setup_tracing(cfg)
        assert tracing_setup_module._tracing_enabled is True


class TestSetupOtel:
    def test_logfire_backend(self):
        cfg = TracingConfig(
            enabled=True,
            backend="logfire",
            service_name="test-svc",
            logfire=LogfireConfig(token="test-token"),
            sampling_rate=0.5,
        )
        mock_logfire = MagicMock()
        mock_trace = MagicMock()
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer

        with patch.dict(
            sys.modules,
            {
                "logfire": mock_logfire,
                "opentelemetry": MagicMock(trace=mock_trace),
                "opentelemetry.trace": mock_trace,
            },
        ):
            tracing_setup_module._setup_otel(cfg)

        mock_logfire.configure.assert_called_once()
        mock_trace.get_tracer.assert_called_once()
        assert tracing_setup_module._tracer is mock_tracer

    def test_otel_sdk_console_backend(self):
        cfg = TracingConfig(
            enabled=True,
            backend="console",
            service_name="test-svc",
            sampling_rate=1.0,
        )
        mock_trace = MagicMock()
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        mock_resource = MagicMock()
        mock_resource_cls = MagicMock()
        mock_resource_cls.create.return_value = mock_resource
        mock_provider = MagicMock()
        mock_provider_cls = MagicMock(return_value=mock_provider)
        mock_sampler = MagicMock()
        mock_sampler_cls = MagicMock(return_value=mock_sampler)
        mock_console_exporter = MagicMock()
        mock_batch_processor = MagicMock()

        with patch.dict(
            sys.modules,
            {
                "opentelemetry": MagicMock(trace=mock_trace),
                "opentelemetry.trace": mock_trace,
                "opentelemetry.sdk": MagicMock(),
                "opentelemetry.sdk.resources": MagicMock(Resource=mock_resource_cls),
                "opentelemetry.sdk.trace": MagicMock(TracerProvider=mock_provider_cls),
                "opentelemetry.sdk.trace.sampling": MagicMock(
                    TraceIdRatioBased=mock_sampler_cls
                ),
                "opentelemetry.sdk.trace.export": MagicMock(
                    ConsoleSpanExporter=MagicMock(return_value=mock_console_exporter),
                    BatchSpanProcessor=MagicMock(return_value=mock_batch_processor),
                ),
            },
        ):
            tracing_setup_module._setup_otel(cfg)

        mock_trace.set_tracer_provider.assert_called_once()
        assert tracing_setup_module._tracer is mock_tracer


class TestBuildExporter:
    def test_otlp_grpc(self):
        cfg = TracingConfig(backend="otlp_grpc", endpoint="http://localhost:4317")
        mock_grpc_exporter = MagicMock()
        mock_grpc_class = MagicMock(return_value=mock_grpc_exporter)

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter": MagicMock(),
                "opentelemetry.exporter.otlp": MagicMock(),
                "opentelemetry.exporter.otlp.proto": MagicMock(),
                "opentelemetry.exporter.otlp.proto.grpc": MagicMock(),
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(
                    OTLPSpanExporter=mock_grpc_class,
                ),
            },
        ):
            result = tracing_setup_module._build_exporter(cfg)
        assert result is mock_grpc_exporter

    def test_otlp_http(self):
        cfg = TracingConfig(backend="otlp_http", endpoint="http://localhost:4318")
        mock_http_exporter = MagicMock()
        mock_http_class = MagicMock(return_value=mock_http_exporter)

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter": MagicMock(),
                "opentelemetry.exporter.otlp": MagicMock(),
                "opentelemetry.exporter.otlp.proto": MagicMock(),
                "opentelemetry.exporter.otlp.proto.http": MagicMock(),
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": MagicMock(
                    OTLPSpanExporter=mock_http_class,
                ),
            },
        ):
            result = tracing_setup_module._build_exporter(cfg)
        assert result is mock_http_exporter

    def test_console_backend(self):
        cfg = TracingConfig(backend="console")
        mock_console_exporter = MagicMock()
        mock_console_cls = MagicMock(return_value=mock_console_exporter)

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.sdk": MagicMock(),
                "opentelemetry.sdk.trace": MagicMock(),
                "opentelemetry.sdk.trace.export": MagicMock(
                    ConsoleSpanExporter=mock_console_cls,
                ),
            },
        ):
            result = tracing_setup_module._build_exporter(cfg)
        assert result is mock_console_exporter

    def test_unknown_backend_rejected_by_validation(self):
        with pytest.raises(ValidationError, match="literal_error"):
            TracingConfig(backend="unknown_backend")

    def test_otlp_grpc_default_endpoint(self):
        cfg = TracingConfig(backend="otlp_grpc", endpoint="")
        mock_grpc_class = MagicMock()

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter": MagicMock(),
                "opentelemetry.exporter.otlp": MagicMock(),
                "opentelemetry.exporter.otlp.proto": MagicMock(),
                "opentelemetry.exporter.otlp.proto.grpc": MagicMock(),
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(
                    OTLPSpanExporter=mock_grpc_class,
                ),
            },
        ):
            tracing_setup_module._build_exporter(cfg)
        mock_grpc_class.assert_called_once_with(endpoint="http://localhost:4317")

    def test_otlp_http_default_endpoint(self):
        cfg = TracingConfig(backend="otlp_http", endpoint="")
        mock_http_class = MagicMock()

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter": MagicMock(),
                "opentelemetry.exporter.otlp": MagicMock(),
                "opentelemetry.exporter.otlp.proto": MagicMock(),
                "opentelemetry.exporter.otlp.proto.http": MagicMock(),
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": MagicMock(
                    OTLPSpanExporter=mock_http_class,
                ),
            },
        ):
            tracing_setup_module._build_exporter(cfg)
        mock_http_class.assert_called_once_with(endpoint="http://localhost:4318")
