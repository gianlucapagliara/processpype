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

    def _read_metadata_file(self, rel_path: str) -> dict[str, Any]:
        """Read metadata from a file if it exists.

        Args:
            rel_path: Relative path of the object

        Returns:
            Metadata dictionary (empty if not found or parse error)
        """
        metadata_path = self._get_metadata_path(rel_path)
        if not metadata_path.exists():
            return {}
        try:
            with open(metadata_path) as f:
                return json.load(f)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse metadata for {rel_path}")
            return {}

    def _make_object_metadata(
        self, file_path: str, base_path_str: str
    ) -> StorageObjectMetadata:
        """Create StorageObjectMetadata from a file path.

        Args:
            file_path: Absolute file path
            base_path_str: Base path string for relative path calculation

        Returns:
            StorageObjectMetadata for the file
        """
        rel_path = os.path.relpath(file_path, base_path_str)
        stats = os.stat(file_path)
        last_modified = datetime.fromtimestamp(stats.st_mtime).isoformat()
        metadata = self._read_metadata_file(rel_path)
        return StorageObjectMetadata(
            path=rel_path,
            size=stats.st_size,
            last_modified=last_modified,
            metadata=metadata,
        )

    def _list_from_directory(
        self, walk_root: Path, base_path_str: str
    ) -> list[StorageObjectMetadata]:
        """List all non-metadata files under a directory.

        Args:
            walk_root: Directory to walk
            base_path_str: Base path for relative path calculation

        Returns:
            List of StorageObjectMetadata
        """
        result = []
        for root, _, files in os.walk(walk_root):
            for file in files:
                if file.endswith(".metadata.json"):
                    continue
                file_path = os.path.join(root, file)
                result.append(self._make_object_metadata(file_path, base_path_str))
        return result

    def _list_by_prefix_pattern(
        self, prefix_path: Path, prefix_name: str, base_path_str: str
    ) -> list[StorageObjectMetadata]:
        """List files in a directory that match a prefix pattern.

        Args:
            prefix_path: Parent directory to search in
            prefix_name: File name prefix to match
            base_path_str: Base path for relative path calculation

        Returns:
            List of StorageObjectMetadata
        """
        result = []
        for file in os.listdir(prefix_path):
            if file.endswith(".metadata.json"):
                continue
            if file.startswith(prefix_name):
                file_path = os.path.join(prefix_path, file)
                if os.path.isfile(file_path):
                    result.append(self._make_object_metadata(file_path, base_path_str))
        return result

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

            if prefix_path.is_dir():
                return self._list_from_directory(prefix_path, base_path_str)
            elif prefix:
                prefix_dir = prefix_path.parent
                if prefix_dir.is_dir():
                    return self._list_by_prefix_pattern(
                        prefix_dir, prefix_path.name, base_path_str
                    )
                return []
            else:
                return self._list_from_directory(self._base_path, base_path_str)
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
