"""Tests for the CommunicationDispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock

from eventspype import EventSubscriber

from processpype.communications.base import NoOpCommunicator
from processpype.communications.dispatcher import (
    CommunicationDispatcher,
    emit_message,
    get_dispatcher,
)
from processpype.communications.models import IncomingMessage, OutgoingMessage


class _CollectorSubscriber(EventSubscriber):
    """Subscriber that collects events into a list."""

    def __init__(self) -> None:
        super().__init__()
        self.received: list[IncomingMessage] = []

    def call(self, arg: IncomingMessage, tag: int, caller: object) -> None:
        self.received.append(arg)


class _FakeCommunicator(NoOpCommunicator):
    """A testable communicator that records sent messages."""

    def __init__(self, name: str = "fake", *, receiving: bool = False) -> None:
        super().__init__()
        self._name = name
        self._started = True
        self._receiving = receiving
        self.sent: list[OutgoingMessage] = []

    @property
    def supports_receiving(self) -> bool:
        return self._receiving

    async def send(self, message: OutgoingMessage) -> None:
        self.sent.append(message)


class _FailingCommunicator(_FakeCommunicator):
    """A communicator that always raises on send."""

    async def send(self, message: OutgoingMessage) -> None:
        raise RuntimeError("send failed")


class _FailingStartCommunicator(_FakeCommunicator):
    """A communicator that always raises on start."""

    async def start(self) -> None:
        raise RuntimeError("start failed")


class _FailingStopCommunicator(_FakeCommunicator):
    """A communicator that always raises on stop."""

    async def stop(self) -> None:
        raise RuntimeError("stop failed")


class TestDispatcherRegistration:
    """Tests for register/unregister."""

    def test_register_default_label(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        d.register(comm)
        assert "a" in d._communicators
        assert "a" in d._label_map["default"]

    def test_register_custom_labels(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        d.register(comm, labels=["alerts", "ops"])
        assert "a" in d._label_map["alerts"]
        assert "a" in d._label_map["ops"]
        assert "default" not in d._label_map

    def test_register_does_not_duplicate(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        d.register(comm, labels=["x"])
        d.register(comm, labels=["x"])
        assert d._label_map["x"].count("a") == 1

    def test_register_sets_incoming_handler_when_receiving(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("rx", receiving=True)
        d.register(comm)
        assert comm._on_incoming is not None

    def test_register_does_not_set_incoming_handler_when_not_receiving(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("tx", receiving=False)
        d.register(comm)
        assert comm._on_incoming is None

    def test_unregister_removes_communicator(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        d.register(comm, labels=["x", "y"])
        d.unregister("a")
        assert "a" not in d._communicators

    def test_unregister_removes_from_labels(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        d.register(comm, labels=["x", "y"])
        d.unregister("a")
        # Labels with no communicators should be cleaned up
        assert "x" not in d._label_map
        assert "y" not in d._label_map

    def test_unregister_preserves_other_communicators_on_same_label(self) -> None:
        d = CommunicationDispatcher()
        a = _FakeCommunicator("a")
        b = _FakeCommunicator("b")
        d.register(a, labels=["shared"])
        d.register(b, labels=["shared"])
        d.unregister("a")
        assert d._label_map["shared"] == ["b"]
        assert "b" in d._communicators

    def test_unregister_nonexistent_is_safe(self) -> None:
        d = CommunicationDispatcher()
        d.unregister("does_not_exist")  # should not raise


class TestDispatcherEmit:
    """Tests for message emission/routing."""

    async def test_emit_routes_to_correct_label(self) -> None:
        d = CommunicationDispatcher()
        alerts = _FakeCommunicator("alerts")
        ops = _FakeCommunicator("ops")
        d.register(alerts, labels=["alerts"])
        d.register(ops, labels=["ops"])

        msg = OutgoingMessage(message="fire!", label="alerts")
        await d.emit(msg)

        assert len(alerts.sent) == 1
        assert alerts.sent[0].message == "fire!"
        assert len(ops.sent) == 0

    async def test_emit_to_multiple_backends_on_same_label(self) -> None:
        d = CommunicationDispatcher()
        a = _FakeCommunicator("a")
        b = _FakeCommunicator("b")
        d.register(a, labels=["broadcast"])
        d.register(b, labels=["broadcast"])

        msg = OutgoingMessage(message="hello", label="broadcast")
        await d.emit(msg)

        assert len(a.sent) == 1
        assert len(b.sent) == 1

    async def test_emit_unknown_label_does_not_raise(self) -> None:
        d = CommunicationDispatcher()
        msg = OutgoingMessage(message="lost", label="unknown")
        await d.emit(msg)  # should just log debug and return

    async def test_emit_skips_stopped_communicator(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        comm._started = False
        d.register(comm, labels=["x"])

        msg = OutgoingMessage(message="hello", label="x")
        await d.emit(msg)

        assert len(comm.sent) == 0

    async def test_emit_catches_send_exception(self) -> None:
        d = CommunicationDispatcher()
        failing = _FailingCommunicator("bad")
        ok = _FakeCommunicator("ok")
        d.register(failing, labels=["shared"])
        d.register(ok, labels=["shared"])

        msg = OutgoingMessage(message="test", label="shared")
        await d.emit(msg)

        # The ok communicator should still receive the message
        assert len(ok.sent) == 1


class TestDispatcherLifecycle:
    """Tests for start_all / stop_all."""

    async def test_start_all(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        comm._started = False
        comm.start = AsyncMock()  # type: ignore[method-assign]
        d.register(comm)

        await d.start_all()
        comm.start.assert_awaited_once()

    async def test_start_all_catches_exception(self) -> None:
        d = CommunicationDispatcher()
        failing = _FailingStartCommunicator("bad")
        ok = _FakeCommunicator("ok")
        ok.start = AsyncMock()  # type: ignore[method-assign]
        d.register(failing)
        d.register(ok)

        await d.start_all()
        ok.start.assert_awaited_once()

    async def test_stop_all(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("a")
        comm.stop = AsyncMock()  # type: ignore[method-assign]
        d.register(comm)

        await d.stop_all()
        comm.stop.assert_awaited_once()

    async def test_stop_all_catches_exception(self) -> None:
        d = CommunicationDispatcher()
        failing = _FailingStopCommunicator("bad")
        ok = _FakeCommunicator("ok")
        ok.stop = AsyncMock()  # type: ignore[method-assign]
        d.register(failing)
        d.register(ok)

        await d.stop_all()
        ok.stop.assert_awaited_once()


class TestDispatcherIncoming:
    """Tests for incoming message publishing."""

    def test_publish_incoming(self) -> None:
        d = CommunicationDispatcher()
        sub = _CollectorSubscriber()
        d.incoming_publisher.add_subscriber(sub)

        msg = IncomingMessage(text="hello", backend_name="test")
        d._publish_incoming(msg)

        assert len(sub.received) == 1
        assert sub.received[0].text == "hello"

    def test_incoming_handler_set_on_receiving_backend(self) -> None:
        d = CommunicationDispatcher()
        comm = _FakeCommunicator("rx", receiving=True)
        d.register(comm)

        # Simulate a backend calling the handler
        sub = _CollectorSubscriber()
        d.incoming_publisher.add_subscriber(sub)

        msg = IncomingMessage(text="incoming", backend_name="rx")
        comm._on_incoming(msg)  # type: ignore[misc]

        assert len(sub.received) == 1
        assert sub.received[0].text == "incoming"


class TestGlobalDispatcher:
    """Tests for the module-level singleton."""

    def test_get_dispatcher_returns_instance(self) -> None:
        import processpype.communications.dispatcher as mod

        original = mod._dispatcher
        try:
            mod._dispatcher = None
            d = get_dispatcher()
            assert isinstance(d, CommunicationDispatcher)
            # Second call returns same instance
            assert get_dispatcher() is d
        finally:
            mod._dispatcher = original

    async def test_emit_message_uses_global_dispatcher(self) -> None:
        import processpype.communications.dispatcher as mod

        d = CommunicationDispatcher()
        comm = _FakeCommunicator("g")
        d.register(comm, labels=["default"])

        original = mod._dispatcher
        try:
            mod._dispatcher = d
            await emit_message(OutgoingMessage(message="global"))
            assert len(comm.sent) == 1
        finally:
            mod._dispatcher = original
