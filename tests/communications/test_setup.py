"""Tests for the communications setup/initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from processpype.communications.setup import init_communications
from processpype.config.models import (
    CommunicationsConfig,
    CommunicatorBackendConfig,
)


class TestInitCommunications:
    """Tests for init_communications."""

    async def test_disabled_config_does_nothing(self) -> None:
        config = CommunicationsConfig(enabled=False)
        await init_communications(config)

    @patch("processpype.communications.dispatcher.get_dispatcher")
    @patch("processpype.communications.backends.create_communicator")
    async def test_enabled_no_backends(
        self, mock_create: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_dispatcher = MagicMock()
        mock_dispatcher.start_all = AsyncMock()
        mock_get.return_value = mock_dispatcher

        config = CommunicationsConfig(enabled=True, backends={})
        await init_communications(config)

        mock_create.assert_not_called()
        mock_dispatcher.start_all.assert_awaited_once()

    @patch("processpype.communications.dispatcher.get_dispatcher")
    @patch("processpype.communications.backends.create_communicator")
    async def test_disabled_backend_is_skipped(
        self, mock_create: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_dispatcher = MagicMock()
        mock_dispatcher.start_all = AsyncMock()
        mock_get.return_value = mock_dispatcher

        config = CommunicationsConfig(
            enabled=True,
            backends={
                "test": CommunicatorBackendConfig(type="custom", enabled=False),
            },
        )
        await init_communications(config)

        mock_create.assert_not_called()
        mock_dispatcher.start_all.assert_awaited_once()

    @patch("processpype.communications.dispatcher.get_dispatcher")
    @patch("processpype.communications.backends.create_communicator")
    async def test_backend_creation_failure_is_caught(
        self, mock_create: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_create.side_effect = RuntimeError("boom")
        mock_dispatcher = MagicMock()
        mock_dispatcher.start_all = AsyncMock()
        mock_get.return_value = mock_dispatcher

        config = CommunicationsConfig(
            enabled=True,
            backends={
                "bad": CommunicatorBackendConfig(type="custom", enabled=True),
            },
        )
        await init_communications(config)

        mock_dispatcher.start_all.assert_awaited_once()

    @patch("processpype.communications.dispatcher.get_dispatcher")
    @patch("processpype.communications.backends.create_communicator")
    async def test_successful_backend_is_registered(
        self, mock_create: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_comm = MagicMock()
        mock_create.return_value = mock_comm
        mock_dispatcher = MagicMock()
        mock_dispatcher.start_all = AsyncMock()
        mock_get.return_value = mock_dispatcher

        config = CommunicationsConfig(
            enabled=True,
            backends={
                "ok": CommunicatorBackendConfig(
                    type="custom", enabled=True, labels=["alerts"]
                ),
            },
        )
        await init_communications(config)

        mock_dispatcher.register.assert_called_once_with(mock_comm, labels=["alerts"])
        mock_dispatcher.start_all.assert_awaited_once()
