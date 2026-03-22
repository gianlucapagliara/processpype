"""Tests for ApplicationCreator."""

import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.application import Application
from processpype.config.models import ProcessPypeConfig
from processpype.creator import ApplicationCreator


@pytest.fixture(autouse=True)
def reset_creator():
    """Reset ApplicationCreator singleton state between tests."""
    ApplicationCreator.app = None
    ApplicationCreator.is_shutting_down = False
    yield
    ApplicationCreator.app = None
    ApplicationCreator.is_shutting_down = False


class TestGetApplication:
    """Tests for get_application."""

    def test_creates_application_with_defaults(self) -> None:
        app = ApplicationCreator.get_application()
        assert isinstance(app, Application)
        assert ApplicationCreator.app is app

    def test_returns_same_instance_on_second_call(self) -> None:
        app1 = ApplicationCreator.get_application()
        app2 = ApplicationCreator.get_application()
        assert app1 is app2

    def test_uses_provided_config(self) -> None:
        config = ProcessPypeConfig(app={"title": "Custom"})
        app = ApplicationCreator.get_application(config=config)
        assert app.config.app.title == "Custom"

    def test_uses_custom_application_class(self) -> None:
        class CustomApp(Application):
            pass

        app = ApplicationCreator.get_application(application_class=CustomApp)
        assert isinstance(app, CustomApp)


class TestSetupLifespan:
    """Tests for _setup_lifespan."""

    def test_raises_if_app_is_none(self) -> None:
        ApplicationCreator.app = None
        with pytest.raises(RuntimeError, match="not initialized"):
            ApplicationCreator._setup_lifespan()

    def test_lifespan_context_is_set(self) -> None:
        app = ApplicationCreator.get_application()
        # lifespan_context should be set on the router
        assert app.api.router.lifespan_context is not None

    @pytest.mark.asyncio
    async def test_lifespan_initializes_and_starts_services(self) -> None:
        app = ApplicationCreator.get_application()
        mock_fastapi = MagicMock()

        with (
            patch.object(app, "initialize", new_callable=AsyncMock) as mock_init,
            patch.object(
                ApplicationCreator,
                "_start_enabled_services",
                new_callable=AsyncMock,
            ) as mock_start,
        ):
            lifespan = app.api.router.lifespan_context
            async with lifespan(mock_fastapi):
                mock_init.assert_awaited_once()
                mock_start.assert_awaited_once_with(app)

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_calls_stop(self) -> None:
        ApplicationCreator.is_shutting_down = False
        app = ApplicationCreator.get_application()
        mock_fastapi = MagicMock()

        with (
            patch.object(app, "initialize", new_callable=AsyncMock),
            patch.object(
                ApplicationCreator,
                "_start_enabled_services",
                new_callable=AsyncMock,
            ),
            patch.object(app, "stop", new_callable=AsyncMock) as mock_stop,
            patch("logging.getLogger"),
        ):
            lifespan = app.api.router.lifespan_context
            async with lifespan(mock_fastapi):
                pass
            mock_stop.assert_awaited_once()
            assert ApplicationCreator.is_shutting_down is True

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_skips_if_already_shutting_down(self) -> None:
        ApplicationCreator.is_shutting_down = True
        app = ApplicationCreator.get_application()
        mock_fastapi = MagicMock()

        with (
            patch.object(app, "initialize", new_callable=AsyncMock),
            patch.object(
                ApplicationCreator,
                "_start_enabled_services",
                new_callable=AsyncMock,
            ),
            patch.object(app, "stop", new_callable=AsyncMock) as mock_stop,
        ):
            lifespan = app.api.router.lifespan_context
            async with lifespan(mock_fastapi):
                pass
            mock_stop.assert_not_awaited()


class TestInstallSignalHandlers:
    """Tests for _install_signal_handlers."""

    def test_installs_sigterm_and_sigint(self) -> None:
        mock_app = MagicMock()
        with patch("signal.signal") as mock_signal:
            ApplicationCreator._install_signal_handlers(mock_app)
            calls = [c[0][0] for c in mock_signal.call_args_list]
            assert signal.SIGTERM in calls
            assert signal.SIGINT in calls

    def test_signal_handler_calls_sys_exit(self) -> None:
        mock_app = MagicMock()
        captured_handler = None

        def capture_handler(sig, handler):
            nonlocal captured_handler
            if sig == signal.SIGTERM:
                captured_handler = handler

        with patch("signal.signal", side_effect=capture_handler):
            ApplicationCreator._install_signal_handlers(mock_app)

        assert captured_handler is not None
        with pytest.raises(SystemExit):
            captured_handler(signal.SIGTERM, None)


class TestStartEnabledServices:
    """Tests for _start_enabled_services."""

    @pytest.mark.asyncio
    async def test_empty_env_does_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLED_SERVICES", "")
        mock_app = MagicMock()
        mock_app.register_service = MagicMock()
        await ApplicationCreator._start_enabled_services(mock_app)
        mock_app.register_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_service_logs_warning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLED_SERVICES", "nonexistent_svc")
        mock_app = MagicMock()
        with patch("processpype.creator.get_available_services", return_value={}):
            await ApplicationCreator._start_enabled_services(mock_app)
        mock_app.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_registers_and_starts_known_service(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLED_SERVICES", "my_svc")
        mock_svc_class = MagicMock()
        mock_app = MagicMock()
        mock_app.start_service = AsyncMock()

        with patch(
            "processpype.creator.get_available_services",
            return_value={"my_svc": mock_svc_class},
        ):
            await ApplicationCreator._start_enabled_services(mock_app)

        mock_app.register_service.assert_called_once_with(mock_svc_class, name="my_svc")
        mock_app.start_service.assert_awaited_once_with("my_svc")

    @pytest.mark.asyncio
    async def test_handles_service_start_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLED_SERVICES", "bad_svc")
        mock_svc_class = MagicMock()
        mock_app = MagicMock()
        mock_app.register_service.side_effect = RuntimeError("boom")

        with patch(
            "processpype.creator.get_available_services",
            return_value={"bad_svc": mock_svc_class},
        ):
            # Should not raise
            await ApplicationCreator._start_enabled_services(mock_app)

        mock_app.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_services_comma_separated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLED_SERVICES", "svc1, svc2")
        mock_cls1 = MagicMock()
        mock_cls2 = MagicMock()
        mock_app = MagicMock()
        mock_app.start_service = AsyncMock()

        with patch(
            "processpype.creator.get_available_services",
            return_value={"svc1": mock_cls1, "svc2": mock_cls2},
        ):
            await ApplicationCreator._start_enabled_services(mock_app)

        assert mock_app.register_service.call_count == 2
        assert mock_app.start_service.await_count == 2
