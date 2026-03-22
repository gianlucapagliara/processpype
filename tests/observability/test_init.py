"""Tests for observability __init__ exports and init_observability."""

from __future__ import annotations

from unittest.mock import patch

from processpype.config.models import (
    LoggingConfig,
    ObservabilityConfig,
    TracingConfig,
)
from processpype.observability import get_logger, init_observability


class TestGetLogger:
    def test_returns_logger_with_prefix(self):
        logger = get_logger("mymodule")
        assert logger.name == "processpype.mymodule"

    def test_custom_prefix(self):
        logger = get_logger("mymodule", prefix="custom")
        assert logger.name == "custom.mymodule"

    def test_empty_prefix(self):
        logger = get_logger("mymodule", prefix="")
        assert logger.name == "mymodule"


class TestInitObservability:
    def test_calls_init_logging(self):
        cfg = ObservabilityConfig(
            logging=LoggingConfig(enabled=False),
            tracing=TracingConfig(enabled=False),
        )
        with patch(
            "processpype.observability.logging.setup.init_logging"
        ) as mock_init_logging:
            init_observability(cfg)
            mock_init_logging.assert_called_once_with(cfg.logging)

    def test_calls_setup_tracing_when_enabled(self):
        cfg = ObservabilityConfig(
            logging=LoggingConfig(enabled=False),
            tracing=TracingConfig(enabled=True, service_name="test"),
        )
        with (
            patch("processpype.observability.logging.setup.init_logging"),
            patch(
                "processpype.observability.tracing.setup.setup_tracing"
            ) as mock_setup_tracing,
        ):
            init_observability(cfg)
            mock_setup_tracing.assert_called_once_with(cfg.tracing)

    def test_skips_tracing_when_disabled(self):
        cfg = ObservabilityConfig(
            logging=LoggingConfig(enabled=False),
            tracing=TracingConfig(enabled=False),
        )
        with (
            patch("processpype.observability.logging.setup.init_logging"),
            patch(
                "processpype.observability.tracing.setup.setup_tracing"
            ) as mock_setup_tracing,
        ):
            init_observability(cfg)
            mock_setup_tracing.assert_not_called()


class TestTracingConfigReexport:
    def test_imports(self):
        from processpype.observability.tracing.config import (
            LogfireConfig,
            TracingConfig,
        )

        assert TracingConfig is not None
        assert LogfireConfig is not None


class TestExports:
    def test_all_exports_importable(self):
        import processpype.observability as obs
        from processpype.observability import __all__

        for name in __all__:
            assert hasattr(obs, name), f"{name} not found in observability module"
