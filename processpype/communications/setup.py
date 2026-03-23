"""Communication subsystem initialization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from processpype.config.models import CommunicationsConfig

logger = logging.getLogger(__name__)


async def init_communications(config: CommunicationsConfig) -> None:
    """Initialize the communication dispatcher and backends from config."""
    if not config.enabled:
        logger.debug("Communications disabled by configuration.")
        return

    from processpype.communications.backends import create_communicator
    from processpype.communications.dispatcher import get_dispatcher

    dispatcher = get_dispatcher()

    for name, backend_config in config.backends.items():
        if not backend_config.enabled:
            logger.debug("Communicator '%s' disabled, skipping.", name)
            continue
        try:
            communicator = create_communicator(name, backend_config)
            dispatcher.register(communicator, labels=backend_config.labels)
        except Exception:
            logger.exception(
                "Failed to create communicator '%s' (type=%s)",
                name,
                backend_config.type,
            )

    await dispatcher.start_all()
