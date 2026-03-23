"""Tests for base communicator classes."""

import pytest

from processpype.communications.base import Communicator, NoOpCommunicator
from processpype.communications.models import IncomingMessage, OutgoingMessage


class TestNoOpCommunicator:
    """Tests for the NoOpCommunicator fallback."""

    def test_properties(self) -> None:
        noop = NoOpCommunicator()
        assert noop.name == "noop"
        assert noop.is_started is True
        assert noop.supports_receiving is False

    async def test_start_is_noop(self) -> None:
        noop = NoOpCommunicator()
        await noop.start()  # should not raise

    async def test_stop_is_noop(self) -> None:
        noop = NoOpCommunicator()
        await noop.stop()  # should not raise

    async def test_send_is_noop(self) -> None:
        noop = NoOpCommunicator()
        msg = OutgoingMessage(message="ignored")
        await noop.send(msg)  # should not raise


class TestCommunicatorABC:
    """Tests for the Communicator abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            Communicator(name="test", config=None)  # type: ignore[abstract]

    def test_set_incoming_handler(self) -> None:
        noop = NoOpCommunicator()
        called_with = []

        def handler(msg: IncomingMessage) -> None:
            called_with.append(msg)

        noop.set_incoming_handler(handler)
        assert noop._on_incoming is handler

        # Invoke it
        msg = IncomingMessage(text="test")
        noop._on_incoming(msg)
        assert called_with == [msg]
