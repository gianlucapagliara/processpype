"""Models for the StorageService."""

from enum import Enum
from typing import Any

from pydantic import Field

from processpype.core.configuration.models import ServiceConfiguration


class StorageBackend(str, Enum):
    """Supported storage backends."""

    LOCAL = "local"
    S3 = "s3"


class StorageConfiguration(ServiceConfiguration):
    """Configuration for the StorageService."""

    backend: StorageBackend = Field(
        default=StorageBackend.LOCAL,
        description="Storage backend to use",
    )
    base_path: str = Field(
        default="./data",
        description="Base path for local storage",
    )

    # S3-specific configuration
    s3_bucket: str | None = Field(
        default=None,
        description="S3 bucket name",
    )
    s3_region: str | None = Field(
        default=None,
        description="S3 region",
    )
    s3_endpoint: str | None = Field(
        default=None,
        description="S3 endpoint URL (for custom S3-compatible services)",
    )
    s3_access_key: str | None = Field(
        default=None,
        description="S3 access key",
    )
    s3_secret_key: str | None = Field(
        default=None,
        description="S3 secret key",
    )


class StorageObject:
    """Represents an object in storage."""

    def __init__(
        self,
        path: str,
        content: bytes | None = None,
        metadata: dict[str, Any] | None = None,
        size: int | None = None,
        last_modified: str | None = None,
    ):
        """Initialize a storage object.

        Args:
            path: Path to the object
            content: Object content
            metadata: Object metadata
            size: Object size in bytes
            last_modified: Last modified timestamp
        """
        self.path = path
        self.content = content
        self.metadata = metadata or {}
        self.size = size
        self.last_modified = last_modified

    def __repr__(self) -> str:
        """Return string representation of the object."""
        return f"StorageObject(path={self.path}, size={self.size})"


class StorageObjectMetadata:
    """Metadata for a storage object."""

    def __init__(
        self,
        path: str,
        size: int | None = None,
        last_modified: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize storage object metadata.

        Args:
            path: Path to the object
            size: Object size in bytes
            last_modified: Last modified timestamp
            metadata: Additional metadata
        """
        self.path = path
        self.size = size
        self.last_modified = last_modified
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        """Return string representation of the metadata."""
        return f"StorageObjectMetadata(path={self.path}, size={self.size})"
