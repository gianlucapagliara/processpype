"""Bootstrap OpenTelemetry tracing for ProcessPype."""

from __future__ import annotations

import atexit
import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from processpype.observability.tracing.noop import NoOpTracer

if TYPE_CHECKING:
    from processpype.config.models import TracingConfig

logger = logging.getLogger(__name__)

_tracing_enabled: bool = False
_tracer: object | None = None
_config: TracingConfig | None = None
_trace_filter: Callable[[str], bool] | None = None


def register_trace_filter(filter_fn: Callable[[str], bool] | None) -> None:
    """Register an optional span-name filter callback."""
    global _trace_filter
    _trace_filter = filter_fn


def get_tracing_config() -> TracingConfig | None:
    return _config


def get_tracer() -> Any:
    """Return the global tracer (real or no-op)."""
    global _tracer
    if _tracer is None:
        _tracer = NoOpTracer()
    return _tracer


def is_tracing_enabled() -> bool:
    return _tracing_enabled


def setup_tracing(config: TracingConfig) -> None:
    """Initialise the OTEL TracerProvider according to *config*."""
    global _tracing_enabled, _tracer, _config

    _config = config

    if _tracing_enabled:
        logger.debug("Tracing already initialised - skipping.")
        return

    if not config.enabled:
        _tracer = NoOpTracer()
        logger.debug("Tracing is disabled by configuration.")
        return

    try:
        _setup_otel(config)
        _tracing_enabled = True
        logger.info(
            "Tracing enabled (backend=%s, service=%s, sample_rate=%.2f)",
            config.backend,
            config.service_name,
            config.sampling_rate,
        )
    except Exception:
        logger.exception("Failed to initialise tracing - falling back to no-op")
        _tracer = NoOpTracer()


def _setup_otel(config: TracingConfig) -> None:
    global _tracer

    if config.backend == "logfire":
        _setup_logfire(config)
    else:
        _setup_otel_sdk(config)

    from opentelemetry import trace

    _tracer = trace.get_tracer(config.service_name, "1.0.0")


def _setup_logfire(config: TracingConfig) -> None:
    import logfire

    logfire.configure(
        token=config.logfire.token or None,
        service_name=config.service_name,
        sampling=logfire.SamplingOptions(head=config.sampling_rate),
    )


def _setup_otel_sdk(config: TracingConfig) -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    resource_attrs: dict[str, str] = {"service.name": config.service_name}
    if version := os.environ.get("SERVICE_VERSION"):
        resource_attrs["service.version"] = version
    if instance_id := os.environ.get("INSTANCE_ID"):
        resource_attrs["service.instance.id"] = instance_id
    if env := os.environ.get("DEPLOY_ENV"):
        resource_attrs["deployment.environment"] = env

    resource = Resource.create(resource_attrs)
    sampler = TraceIdRatioBased(config.sampling_rate)
    provider = TracerProvider(resource=resource, sampler=sampler)

    exporter = _build_exporter(config)
    if exporter is not None:
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    atexit.register(provider.shutdown)


def _build_exporter(config: TracingConfig) -> Any | None:
    if config.backend == "otlp_grpc":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(
            endpoint=config.endpoint or "http://localhost:4317",
        )

    if config.backend == "otlp_http":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(
            endpoint=config.endpoint or "http://localhost:4318",
        )

    if config.backend == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        return ConsoleSpanExporter()

    return None
