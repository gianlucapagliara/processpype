"""Communication dispatcher: routes outgoing messages to backends by label,
publishes incoming messages as eventspype events."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from eventspype import EventPublication, EventPublisher

from processpype.communications.models import IncomingMessage

if TYPE_CHECKING:
    from processpype.communications.base import Communicator
    from processpype.communications.models import OutgoingMessage

logger = logging.getLogger(__name__)


class CommunicationDispatcher:
    """Routes OutgoingMessage to registered Communicator backends by label.

    Incoming messages from backends are published as eventspype events via
    ``incoming_publisher``, allowing any part of the application to subscribe.
    """

    incoming_publication = EventPublication("incoming_message", IncomingMessage)

    def __init__(self) -> None:
        self._communicators: dict[str, Communicator] = {}
        self._label_map: dict[str, list[str]] = {}
        self._incoming_publisher = EventPublisher(self.incoming_publication)

    @property
    def incoming_publisher(self) -> EventPublisher:
        """Expose publisher so consumers can subscribe to incoming messages."""
        return self._incoming_publisher

    def register(
        self, communicator: Communicator, labels: list[str] | None = None
    ) -> None:
        """Register a communicator backend for the given labels."""
        self._communicators[communicator.name] = communicator
        for label in labels or ["default"]:
            names = self._label_map.setdefault(label, [])
            if communicator.name not in names:
                names.append(communicator.name)

        if communicator.supports_receiving:
            communicator.set_incoming_handler(self._publish_incoming)

        logger.info(
            "Registered communicator '%s' for labels %s",
            communicator.name,
            labels,
        )

    def unregister(self, name: str) -> None:
        """Remove a communicator backend."""
        self._communicators.pop(name, None)
        empty_labels = []
        for label, names in self._label_map.items():
            if name in names:
                names.remove(name)
            if not names:
                empty_labels.append(label)
        for label in empty_labels:
            del self._label_map[label]

    def _publish_incoming(self, message: IncomingMessage) -> None:
        """Called by backends when a message is received — publishes as event."""
        self._incoming_publisher.publish(message)

    async def emit(self, message: OutgoingMessage) -> None:
        """Send to all backends registered for message.label."""
        names = self._label_map.get(message.label, [])
        if not names:
            logger.debug(
                "No communicators for label '%s': source=%s message=%s",
                message.label,
                message.source,
                message.message[:80],
            )
            return

        for name in names:
            communicator = self._communicators.get(name)
            if communicator and communicator.is_started:
                try:
                    await communicator.send(message)
                except Exception:
                    logger.exception("Communicator '%s' failed to send", name)

    async def start_all(self) -> None:
        """Start all registered communicators."""
        for communicator in self._communicators.values():
            try:
                await communicator.start()
            except Exception:
                logger.exception("Failed to start communicator '%s'", communicator.name)

    async def stop_all(self) -> None:
        """Stop all registered communicators."""
        for communicator in self._communicators.values():
            try:
                await communicator.stop()
            except Exception:
                logger.exception("Failed to stop communicator '%s'", communicator.name)


# --- Module-level convenience ---

_dispatcher: CommunicationDispatcher | None = None
_dispatcher_lock = threading.Lock()


def get_dispatcher() -> CommunicationDispatcher:
    """Get or create the global communication dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        with _dispatcher_lock:
            if _dispatcher is None:
                _dispatcher = CommunicationDispatcher()
    return _dispatcher


async def emit_message(message: OutgoingMessage) -> None:
    """Convenience: emit a message via the global dispatcher."""
    await get_dispatcher().emit(message)
