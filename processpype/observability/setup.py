"""Unified observability initialisation for logging + tracing."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from processpype.config.models import ObservabilityConfig


def init_observability(config: ObservabilityConfig) -> None:
    """Initialize logging and tracing from the unified config."""
    from processpype.observability.logging.setup import init_logging

    init_logging(config.logging)

    if config.tracing.enabled:
        from processpype.observability.tracing.setup import setup_tracing

        setup_tracing(config.tracing)
