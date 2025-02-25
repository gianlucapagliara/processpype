"""Local filesystem storage backend."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import StorageObject, StorageObjectMetadata
from .base import StorageBackend, StorageBackendError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str, logger: logging.Logger):
        """Initialize the local storage backend.

        Args:
            base_path: Base path for local storage
            logger: Logger instance for backend operations
        """
        super().__init__(logger)
        self._base_path = Path(base_path)

    @property
    def base_path(self) -> Path:
        """Get the base path for local storage.

        Returns:
            Base path for local storage
        """
        return self._base_path

    async def initialize(self) -> None:
        """Initialize the local storage backend.

        Creates the base directory if it doesn't exist.

        Raises:
            StorageBackendError: If initialization fails
        """
        try:
            os.makedirs(self._base_path, exist_ok=True)
            self.logger.info(f"Initialized local storage at {self._base_path}")
        except Exception as e:
            raise StorageBackendError(f"Failed to initialize local storage: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the local storage backend.

        This is a no-op for local storage.
        """
        self.logger.info("Shutting down local storage backend")

    def _get_full_path(self, path: str) -> Path:
        """Get the full path for an object.

        Args:
            path: Object path

        Returns:
            Full path to the object
        """
        # Normalize the path to prevent directory traversal attacks
        normalized_path = os.path.normpath(path)
        if normalized_path.startswith(".."):
            raise StorageBackendError(f"Invalid path: {path}")
        return self._base_path / normalized_path

    def _get_metadata_path(self, path: str) -> Path:
        """Get the path for the metadata file.

        Args:
            path: Object path

        Returns:
            Path to the metadata file
        """
        return self._get_full_path(f"{path}.metadata.json")

    async def get_object(self, path: str) -> StorageObject:
        """Retrieve an object from local storage.

        Args:
            path: Path to the object

        Returns:
            The storage object

        Raises:
            StorageBackendError: If the object cannot be retrieved
        """
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                raise StorageBackendError(f"Object not found: {path}")

            # Get file stats
            stats = full_path.stat()
            last_modified = datetime.fromtimestamp(stats.st_mtime).isoformat()

            # Read file content
            with open(full_path, "rb") as f:
                content = f.read()

            # Read metadata if it exists
            metadata = {}
            metadata_path = self._get_metadata_path(path)
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse metadata for {path}")

            return StorageObject(
                path=path,
                content=content,
                size=stats.st_size,
                last_modified=last_modified,
                metadata=metadata,
            )
        except StorageBackendError:
            raise
        except Exception as e:
            raise StorageBackendError(f"Failed to get object {path}: {e}") from e

    async def put_object(
        self, path: str, data: bytes, metadata: dict[str, Any] | None = None
    ) -> StorageObjectMetadata:
        """Store an object in local storage.

        Args:
            path: Path to the object
            data: Object data
            metadata: Optional metadata to store with the object (ignored for local storage)

        Returns:
            Metadata for the stored object

        Raises:
            StorageBackendError: If the object cannot be stored
        """
        try:
            full_path = self._get_full_path(path)

            # Create parent directories if they don't exist
            os.makedirs(full_path.parent, exist_ok=True)

            # Write file content
            with open(full_path, "wb") as f:
                f.write(data)

            # Write metadata if provided
            if metadata:
                metadata_path = self._get_metadata_path(path)
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)

            # Get file stats
            stats = full_path.stat()
            last_modified = datetime.fromtimestamp(stats.st_mtime).isoformat()

            return StorageObjectMetadata(
                path=path,
                size=stats.st_size,
                last_modified=last_modified,
                metadata=metadata or {},
            )
        except Exception as e:
            raise StorageBackendError(f"Failed to put object {path}: {e}") from e

    async def delete_object(self, path: str) -> None:
        """Delete an object from local storage.

        Args:
            path: Path to the object

        Raises:
            StorageBackendError: If the object cannot be deleted
        """
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                self.logger.warning(f"Object not found for deletion: {path}")
                return

            os.remove(full_path)

            # Delete metadata file if it exists
            metadata_path = self._get_metadata_path(path)
            if metadata_path.exists():
                os.remove(metadata_path)

        except Exception as e:
            raise StorageBackendError(f"Failed to delete object {path}: {e}") from e

    async def list_objects(self, prefix: str = "") -> list[StorageObjectMetadata]:
        """List objects with the given prefix.

        Args:
            prefix: Prefix to filter objects by

        Returns:
            List of object metadata

        Raises:
            StorageBackendError: If the objects cannot be listed
        """
        try:
            prefix_path = self._get_full_path(prefix)
            base_path_str = str(self._base_path)
            result = []

            # If the prefix is a directory, list all files in it
            if prefix_path.is_dir():
                for root, _, files in os.walk(prefix_path):
                    for file in files:
                        # Skip metadata files
                        if file.endswith(".metadata.json"):
                            continue

                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, base_path_str)
                        stats = os.stat(file_path)
                        last_modified = datetime.fromtimestamp(
                            stats.st_mtime
                        ).isoformat()

                        # Get metadata if it exists
                        metadata = {}
                        metadata_path = self._get_metadata_path(rel_path)
                        if metadata_path.exists():
                            try:
                                with open(metadata_path) as f:
                                    metadata = json.load(f)
                            except json.JSONDecodeError:
                                self.logger.warning(
                                    f"Failed to parse metadata for {rel_path}"
                                )

                        result.append(
                            StorageObjectMetadata(
                                path=rel_path,
                                size=stats.st_size,
                                last_modified=last_modified,
                                metadata=metadata,
                            )
                        )
            # If the prefix is a file pattern, list matching files
            elif prefix:
                prefix_dir = prefix_path.parent
                if prefix_dir.is_dir():
                    prefix_name = prefix_path.name
                    for file in os.listdir(prefix_dir):
                        # Skip metadata files
                        if file.endswith(".metadata.json"):
                            continue

                        if file.startswith(prefix_name):
                            file_path = os.path.join(prefix_dir, file)
                            if os.path.isfile(file_path):
                                rel_path = os.path.relpath(file_path, base_path_str)
                                stats = os.stat(file_path)
                                last_modified = datetime.fromtimestamp(
                                    stats.st_mtime
                                ).isoformat()

                                # Get metadata if it exists
                                metadata = {}
                                metadata_path = self._get_metadata_path(rel_path)
                                if metadata_path.exists():
                                    try:
                                        with open(metadata_path) as f:
                                            metadata = json.load(f)
                                    except json.JSONDecodeError:
                                        self.logger.warning(
                                            f"Failed to parse metadata for {rel_path}"
                                        )

                                result.append(
                                    StorageObjectMetadata(
                                        path=rel_path,
                                        size=stats.st_size,
                                        last_modified=last_modified,
                                        metadata=metadata,
                                    )
                                )
            # If no prefix, list all files
            else:
                for root, _, files in os.walk(self._base_path):
                    for file in files:
                        # Skip metadata files
                        if file.endswith(".metadata.json"):
                            continue

                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, base_path_str)
                        stats = os.stat(file_path)
                        last_modified = datetime.fromtimestamp(
                            stats.st_mtime
                        ).isoformat()

                        # Get metadata if it exists
                        metadata = {}
                        metadata_path = self._get_metadata_path(rel_path)
                        if metadata_path.exists():
                            try:
                                with open(metadata_path) as f:
                                    metadata = json.load(f)
                            except json.JSONDecodeError:
                                self.logger.warning(
                                    f"Failed to parse metadata for {rel_path}"
                                )

                        result.append(
                            StorageObjectMetadata(
                                path=rel_path,
                                size=stats.st_size,
                                last_modified=last_modified,
                                metadata=metadata,
                            )
                        )

            return result
        except Exception as e:
            raise StorageBackendError(
                f"Failed to list objects with prefix {prefix}: {e}"
            ) from e

    async def object_exists(self, path: str) -> bool:
        """Check if an object exists.

        Args:
            path: Path to the object

        Returns:
            True if the object exists, False otherwise

        Raises:
            StorageBackendError: If the check fails
        """
        try:
            full_path = self._get_full_path(path)
            return full_path.is_file()
        except Exception as e:
            raise StorageBackendError(
                f"Failed to check if object {path} exists: {e}"
            ) from e

    async def get_object_metadata(self, path: str) -> StorageObjectMetadata:
        """Get metadata for an object.

        Args:
            path: Path to the object

        Returns:
            Object metadata

        Raises:
            StorageBackendError: If the metadata cannot be retrieved
        """
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                raise StorageBackendError(f"Object not found: {path}")

            stats = full_path.stat()
            last_modified = datetime.fromtimestamp(stats.st_mtime).isoformat()

            # Get metadata if it exists
            metadata = {}
            metadata_path = self._get_metadata_path(path)
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse metadata for {path}")

            return StorageObjectMetadata(
                path=path,
                size=stats.st_size,
                last_modified=last_modified,
                metadata=metadata,
            )
        except StorageBackendError:
            raise
        except Exception as e:
            raise StorageBackendError(
                f"Failed to get metadata for object {path}: {e}"
            ) from e
