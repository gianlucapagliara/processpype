"""Storage service implementation."""

import logging
from typing import Any, cast

from processpype.core.service.manager import ServiceManager
from processpype.core.service.service import Service

from .backends import LocalStorageBackend, S3StorageBackend, StorageBackend
from .models import StorageBackend as StorageBackendEnum
from .models import StorageConfiguration, StorageObject, StorageObjectMetadata


class StorageServiceManager(ServiceManager):
    """Manager for the StorageService."""

    def __init__(
        self,
        config: StorageConfiguration,
        logger: logging.Logger,
    ):
        """Initialize the storage service manager.

        Args:
            config: Storage service configuration
            logger: Logger instance for service operations
        """
        super().__init__(logger)
        self._config = config
        self._backend: StorageBackend | None = None

    @property
    def backend(self) -> StorageBackend:
        """Get the storage backend.

        Returns:
            The storage backend instance

        Raises:
            RuntimeError: If the backend is not initialized
        """
        if self._backend is None:
            raise RuntimeError("Storage backend is not initialized")
        return self._backend

    async def start(self) -> None:
        """Start the storage service.

        Initializes the appropriate storage backend based on configuration.

        Raises:
            RuntimeError: If the service fails to start
        """
        try:
            # Create the appropriate backend based on configuration
            if self._config.backend == StorageBackendEnum.LOCAL:
                self._backend = LocalStorageBackend(
                    base_path=self._config.base_path,
                    logger=self.logger,
                )
            elif self._config.backend == StorageBackendEnum.S3:
                if not self._config.s3_bucket:
                    raise ValueError("S3 bucket name is required for S3 backend")

                self._backend = S3StorageBackend(
                    bucket=self._config.s3_bucket,
                    region=self._config.s3_region,
                    endpoint=self._config.s3_endpoint,
                    access_key=self._config.s3_access_key,
                    secret_key=self._config.s3_secret_key,
                    logger=self.logger,
                )
            else:
                raise ValueError(f"Unsupported storage backend: {self._config.backend}")

            # Initialize the backend
            await self._backend.initialize()
            self.logger.info(
                f"Started storage service with {self._config.backend} backend"
            )
        except Exception as e:
            self.logger.error(f"Failed to start storage service: {e}")
            raise RuntimeError(f"Failed to start storage service: {e}") from e

    async def stop(self) -> None:
        """Stop the storage service.

        Shuts down the storage backend.
        """
        if self._backend:
            try:
                await self._backend.shutdown()
                self.logger.info("Stopped storage service")
            except Exception as e:
                self.logger.error(f"Error shutting down storage service: {e}")
            finally:
                self._backend = None

    async def get_object(self, path: str) -> StorageObject:
        """Retrieve an object from storage.

        Args:
            path: Path to the object

        Returns:
            The storage object

        Raises:
            RuntimeError: If the object cannot be retrieved
        """
        try:
            return await self.backend.get_object(path)
        except Exception as e:
            self.logger.error(f"Failed to get object {path}: {e}")
            raise RuntimeError(f"Failed to get object {path}: {e}") from e

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
            RuntimeError: If the object cannot be stored
        """
        try:
            return await self.backend.put_object(path, data, metadata)
        except Exception as e:
            self.logger.error(f"Failed to put object {path}: {e}")
            raise RuntimeError(f"Failed to put object {path}: {e}") from e

    async def delete_object(self, path: str) -> None:
        """Delete an object from storage.

        Args:
            path: Path to the object

        Raises:
            RuntimeError: If the object cannot be deleted
        """
        try:
            await self.backend.delete_object(path)
        except Exception as e:
            self.logger.error(f"Failed to delete object {path}: {e}")
            raise RuntimeError(f"Failed to delete object {path}: {e}") from e

    async def list_objects(self, prefix: str = "") -> list[StorageObjectMetadata]:
        """List objects with the given prefix.

        Args:
            prefix: Prefix to filter objects by

        Returns:
            List of object metadata

        Raises:
            RuntimeError: If the objects cannot be listed
        """
        try:
            return await self.backend.list_objects(prefix)
        except Exception as e:
            self.logger.error(f"Failed to list objects with prefix {prefix}: {e}")
            raise RuntimeError(
                f"Failed to list objects with prefix {prefix}: {e}"
            ) from e

    async def object_exists(self, path: str) -> bool:
        """Check if an object exists.

        Args:
            path: Path to the object

        Returns:
            True if the object exists, False otherwise

        Raises:
            RuntimeError: If the check fails
        """
        try:
            return await self.backend.object_exists(path)
        except Exception as e:
            self.logger.error(f"Failed to check if object {path} exists: {e}")
            raise RuntimeError(f"Failed to check if object {path} exists: {e}") from e

    async def get_object_metadata(self, path: str) -> StorageObjectMetadata:
        """Get metadata for an object.

        Args:
            path: Path to the object

        Returns:
            Object metadata

        Raises:
            RuntimeError: If the metadata cannot be retrieved
        """
        try:
            return await self.backend.get_object_metadata(path)
        except Exception as e:
            self.logger.error(f"Failed to get metadata for object {path}: {e}")
            raise RuntimeError(f"Failed to get metadata for object {path}: {e}") from e


class StorageService(Service):
    """Service for accessing storage backends."""

    configuration_class = StorageConfiguration

    def create_manager(self) -> ServiceManager:
        """Create the service manager.

        Returns:
            The service manager instance
        """
        if self.config is None:
            config = StorageConfiguration()
        else:
            config = cast(StorageConfiguration, self.config)

        return StorageServiceManager(
            config=config,
            logger=self.logger,
        )

    @property
    def manager(self) -> StorageServiceManager:
        """Get the service manager.

        Returns:
            The manager instance for this service.
        """
        return cast(StorageServiceManager, super().manager)

    async def get_object(self, path: str) -> StorageObject:
        """Retrieve an object from storage.

        Args:
            path: Path to the object

        Returns:
            The storage object
        """
        return await self.manager.get_object(path)

    async def get_object_content(self, path: str) -> bytes:
        """Retrieve an object's content from storage.

        Args:
            path: Path to the object

        Returns:
            The object content as bytes
        """
        obj = await self.manager.get_object(path)
        if obj.content is None:
            raise ValueError(f"Object {path} has no content")
        return obj.content

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
        """
        return await self.manager.put_object(path, data, metadata)

    async def delete_object(self, path: str) -> None:
        """Delete an object from storage.

        Args:
            path: Path to the object
        """
        await self.manager.delete_object(path)

    async def list_objects(self, prefix: str = "") -> list[StorageObjectMetadata]:
        """List objects with the given prefix.

        Args:
            prefix: Prefix to filter objects by

        Returns:
            List of object metadata
        """
        return await self.manager.list_objects(prefix)

    async def object_exists(self, path: str) -> bool:
        """Check if an object exists.

        Args:
            path: Path to the object

        Returns:
            True if the object exists, False otherwise
        """
        return await self.manager.object_exists(path)

    async def get_object_metadata(self, path: str) -> StorageObjectMetadata:
        """Get metadata for an object.

        Args:
            path: Path to the object

        Returns:
            Object metadata
        """
        return await self.manager.get_object_metadata(path)
