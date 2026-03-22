"""Tracing configuration model.

Re-exports TracingConfig from the unified YAML config models for convenience.
"""

from processpype.config.models import LogfireConfig, TracingConfig

__all__ = ["LogfireConfig", "TracingConfig"]
