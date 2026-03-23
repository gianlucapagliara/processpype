"""Backend registry and factory."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from processpype.communications.base import Communicator
    from processpype.config.models import CommunicatorBackendConfig

logger = logging.getLogger(__name__)

_backend_registry: dict[str, Callable[..., Communicator]] = {}


def register_backend(type_name: str, factory: Callable[..., Communicator]) -> None:
    """Register a custom communicator backend factory.

    The factory must accept (name: str, config: CommunicatorBackendConfig) and return a Communicator.
    """
    _backend_registry[type_name] = factory


def create_communicator(name: str, config: CommunicatorBackendConfig) -> Communicator:
    """Create a Communicator instance from config type.

    Uses lazy imports so optional dependencies only fail at the point of use.
    Falls back to NoOpCommunicator when a dependency is missing.
    """
    backend_type = config.type

    # Check plugin registry first
    if backend_type in _backend_registry:
        return _backend_registry[backend_type](name=name, config=config)

    if backend_type == "telegram":
        try:
            from processpype.communications.backends.telegram import (
                TelegramCommunicator,
            )

            return TelegramCommunicator(name=name, config=config)  # type: ignore[arg-type]
        except ImportError:
            logger.warning(
                "Telegram backend requested but telethon is not installed. "
                "Install processpype[telegram]."
            )
            from processpype.communications.base import NoOpCommunicator

            return NoOpCommunicator()

    if backend_type == "email":
        try:
            from processpype.communications.backends.email import (
                EmailCommunicator,
            )

            return EmailCommunicator(name=name, config=config)  # type: ignore[arg-type]
        except ImportError:
            logger.warning(
                "Email backend requested but aiosmtplib is not installed. "
                "Install processpype[email]."
            )
            from processpype.communications.base import NoOpCommunicator

            return NoOpCommunicator()

    # Unknown type — warn and return NoOp instead of raising
    logger.warning(
        "Unknown communicator backend type '%s'. "
        "Register it with register_backend() or install the appropriate extra.",
        backend_type,
    )
    from processpype.communications.base import NoOpCommunicator

    return NoOpCommunicator()
