"""Service registry — deprecated re-exports from processpype.service.registry.

.. deprecated::
    Import directly from ``processpype.service.registry`` instead.
    This compatibility shim will be removed in a future release.
"""

import warnings

warnings.warn(
    "Importing from 'processpype.services' is deprecated. "
    "Use 'processpype.service.registry' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from processpype.service.registry import (  # noqa: E402
    AVAILABLE_SERVICES,
    get_available_services,
    get_service_class,
    register_service_class,
)

__all__ = [
    "AVAILABLE_SERVICES",
    "register_service_class",
    "get_available_services",
    "get_service_class",
]
