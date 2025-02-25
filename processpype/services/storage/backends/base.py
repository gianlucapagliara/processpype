"""Base storage backend interface."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from ..models import StorageObject, StorageObjectMetadata


class StorageBackendError(Exception):
    """Exception raised when a storage operation fails."""

    pass


class StorageBackend(ABC):
    """Base class for storage backends."""

    def __init__(self, logger: logging.Logger):
        """Initialize the storage backend.

        Args:
            logger: Logger instance for backend operations
        """
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        """Get the backend logger.

        Returns:
            A logger instance configured for this backend.
        """
        return self._logger

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend.

        This method should be called before any other operations.
        It should establish connections, create directories, etc.

        Raises:
            StorageBackendError: If initialization fails
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the storage backend.

        This method should be called when the backend is no longer needed.
        It should close connections, release resources, etc.

        Raises:
            StorageBackendError: If shutdown fails
        """
        pass

    @abstractmethod
    async def get_object(self, path: str) -> StorageObject:
        """Retrieve an object from storage.

        Args:
            path: Path to the object

        Returns:
            The storage object

        Raises:
            StorageBackendError: If the object cannot be retrieved
        """
        pass

    @abstractmethod
    async def put_object(
        self, path: str, data: bytes, metadata: dict[str, Any] | None = None
    ) -> StorageObjectMetadata:
        """Store an object in storage.

        Args:
            path: Path to the object
            data: Object data
            metadata: Optional metadata to store with the object

        Returns:
            Metadata for the stored object

        Raises:
            StorageBackendError: If the object cannot be stored
        """
        pass

    @abstractmethod
    async def delete_object(self, path: str) -> None:
        """Delete an object from storage.

        Args:
            path: Path to the object

        Raises:
            StorageBackendError: If the object cannot be deleted
        """
        pass

    @abstractmethod
    async def list_objects(self, prefix: str = "") -> list[StorageObjectMetadata]:
        """List objects with the given prefix.

        Args:
            prefix: Prefix to filter objects by

        Returns:
            List of object metadata

        Raises:
            StorageBackendError: If the objects cannot be listed
        """
        pass

    @abstractmethod
    async def object_exists(self, path: str) -> bool:
        """Check if an object exists.

        Args:
            path: Path to the object

        Returns:
            True if the object exists, False otherwise

        Raises:
            StorageBackendError: If the check fails
        """
        pass

    @abstractmethod
    async def get_object_metadata(self, path: str) -> StorageObjectMetadata:
        """Get metadata for an object.

        Args:
            path: Path to the object

        Returns:
            Object metadata

        Raises:
            StorageBackendError: If the metadata cannot be retrieved
        """
        pass
