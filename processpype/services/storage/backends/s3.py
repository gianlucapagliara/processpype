"""S3 storage backend."""

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..models import StorageObject, StorageObjectMetadata
from .base import StorageBackend, StorageBackendError


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend."""

    def __init__(
        self,
        bucket: str,
        region: str | None = None,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        logger: logging.Logger | None = None,
    ):
        """Initialize the S3 storage backend.

        Args:
            bucket: S3 bucket name
            region: AWS region
            endpoint: Custom S3 endpoint URL (for S3-compatible services)
            access_key: AWS access key
            secret_key: AWS secret key
            logger: Logger instance for backend operations
        """
        super().__init__(logger or logging.getLogger(__name__))
        self._bucket = bucket
        self._region = region
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._client = None

    @property
    def bucket(self) -> str:
        """Get the S3 bucket name.

        Returns:
            S3 bucket name
        """
        return self._bucket

    def _check_client(self) -> None:
        """Check if the S3 client is initialized.

        Raises:
            StorageBackendError: If the client is not initialized
        """
        if self._client is None:
            raise StorageBackendError(
                "S3 client is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize the S3 storage backend.

        Creates the S3 client and verifies the bucket exists.

        Raises:
            StorageBackendError: If initialization fails
        """
        try:
            # Create S3 client
            kwargs = {}
            if self._endpoint:
                kwargs["endpoint_url"] = self._endpoint
            if self._region:
                kwargs["region_name"] = self._region
            if self._access_key and self._secret_key:
                kwargs["aws_access_key_id"] = self._access_key
                kwargs["aws_secret_access_key"] = self._secret_key

            self._client = boto3.client("s3", **kwargs)

            # Check if bucket exists
            try:
                self._client.head_bucket(Bucket=self._bucket)
                self.logger.info(f"Connected to S3 bucket: {self._bucket}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "404":
                    self.logger.info(f"Creating S3 bucket: {self._bucket}")
                    self._client.create_bucket(Bucket=self._bucket)
                else:
                    raise StorageBackendError(
                        f"Failed to access S3 bucket {self._bucket}: {e}"
                    ) from e
        except Exception as e:
            raise StorageBackendError(f"Failed to initialize S3 storage: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the S3 storage backend.

        Closes the S3 client.
        """
        self._client = None
        self.logger.info("Shutting down S3 storage backend")

    async def get_object(self, path: str) -> StorageObject:
        """Retrieve an object from S3 storage.

        Args:
            path: Path to the object

        Returns:
            The storage object

        Raises:
            StorageBackendError: If the object cannot be retrieved
        """
        try:
            self._check_client()
            response = self._client.get_object(Bucket=self._bucket, Key=path)
            content = response["Body"].read()
            metadata = response.get("Metadata", {})
            size = response.get("ContentLength")
            last_modified = (
                response.get("LastModified").isoformat()
                if response.get("LastModified")
                else None
            )

            return StorageObject(
                path=path,
                content=content,
                metadata=metadata,
                size=size,
                last_modified=last_modified,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise StorageBackendError(f"Object not found: {path}") from e
            raise StorageBackendError(f"Failed to get object {path}: {e}") from e
        except Exception as e:
            raise StorageBackendError(f"Failed to get object {path}: {e}") from e

    async def put_object(
        self, path: str, data: bytes, metadata: dict[str, Any] | None = None
    ) -> StorageObjectMetadata:
        """Store an object in S3 storage.

        Args:
            path: Path to the object
            data: Object data
            metadata: Optional metadata to store with the object

        Returns:
            Metadata for the stored object

        Raises:
            StorageBackendError: If the object cannot be stored
        """
        try:
            self._check_client()
            kwargs = {
                "Bucket": self._bucket,
                "Key": path,
                "Body": data,
            }
            if metadata:
                # S3 metadata must be strings
                string_metadata = {k: str(v) for k, v in metadata.items()}
                kwargs["Metadata"] = string_metadata

            self._client.put_object(**kwargs)

            # Get object metadata to return
            return await self.get_object_metadata(path)
        except Exception as e:
            raise StorageBackendError(f"Failed to put object {path}: {e}") from e

    async def delete_object(self, path: str) -> None:
        """Delete an object from S3 storage.

        Args:
            path: Path to the object

        Raises:
            StorageBackendError: If the object cannot be deleted
        """
        try:
            self._check_client()
            self._client.delete_object(Bucket=self._bucket, Key=path)
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
            self._check_client()
            result = []
            paginator = self._client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=self._bucket, Prefix=prefix)

            for page in page_iterator:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    path = obj.get("Key")
                    size = obj.get("Size")
                    last_modified = (
                        obj.get("LastModified").isoformat()
                        if obj.get("LastModified")
                        else None
                    )

                    result.append(
                        StorageObjectMetadata(
                            path=path,
                            size=size,
                            last_modified=last_modified,
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
            self._check_client()
            self._client.head_object(Bucket=self._bucket, Key=path)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                return False
            raise StorageBackendError(
                f"Failed to check if object {path} exists: {e}"
            ) from e
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
            self._check_client()
            response = self._client.head_object(Bucket=self._bucket, Key=path)
            metadata = response.get("Metadata", {})
            size = response.get("ContentLength")
            last_modified = (
                response.get("LastModified").isoformat()
                if response.get("LastModified")
                else None
            )

            return StorageObjectMetadata(
                path=path,
                size=size,
                last_modified=last_modified,
                metadata=metadata,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                raise StorageBackendError(f"Object not found: {path}") from e
            raise StorageBackendError(
                f"Failed to get metadata for object {path}: {e}"
            ) from e
        except Exception as e:
            raise StorageBackendError(
                f"Failed to get metadata for object {path}: {e}"
            ) from e
