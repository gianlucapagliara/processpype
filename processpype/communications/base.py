"""Abstract communicator protocol and NoOp fallback."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from processpype.communications.models import IncomingMessage, OutgoingMessage
    from processpype.config.models import CommunicatorBackendConfig


class Communicator(ABC):
    """Abstract base for communication backends.

    All backends must implement ``send()``. Backends that support receiving
    messages should override ``supports_receiving`` to return ``True`` and
    call ``self._on_incoming(msg)`` when a message arrives.
    """

    def __init__(self, name: str, config: CommunicatorBackendConfig) -> None:
        self._name = name
        self._config = config
        self._started = False
        self._on_incoming: Callable[[IncomingMessage], None] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def supports_receiving(self) -> bool:
        return False

    def set_incoming_handler(self, handler: Callable[[IncomingMessage], None]) -> None:
        """Set by dispatcher to route incoming messages to the event publisher.

        Note: This handler is synchronous by design — eventspype's EventPublisher.publish()
        dispatches synchronously. Subscribers to incoming message events must be non-blocking.
        For async processing, use eventspype's QueueEventSubscriber to bridge to an async consumer.
        """
        self._on_incoming = handler

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> None: ...


class NoOpCommunicator(Communicator):
    """Silent fallback when a backend is unavailable."""

    def __init__(self) -> None:
        self._name = "noop"
        self._config = None  # type: ignore[assignment]
        self._started = True
        self._on_incoming = None

    @property
    def supports_receiving(self) -> bool:
        return False

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, message: OutgoingMessage) -> None:
        pass
