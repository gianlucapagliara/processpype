"""Tests for the S3 storage backend."""

import datetime
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError

from processpype.services.storage.backends.base import StorageBackendError
from processpype.services.storage.backends.s3 import S3StorageBackend
from processpype.services.storage.models import StorageObject, StorageObjectMetadata


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch("boto3.client") as mock_boto3_client:
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def s3_backend(mock_s3_client):
    """Create an S3 backend for testing."""
    backend = S3StorageBackend(
        bucket="test-bucket",
        region="us-west-2",
        endpoint=None,
        access_key="test-access-key",
        secret_key="test-secret-key",
    )
    return backend


@pytest.mark.asyncio
async def test_initialize(s3_backend, mock_s3_client):
    """Test initializing the S3 backend."""
    # Setup the mock client
    mock_s3_client.head_bucket.return_value = {}

    # Initialize the backend
    await s3_backend.initialize()

    # Verify boto3.client was called with correct parameters
    boto3.client.assert_called_once_with(
        "s3",
        region_name="us-west-2",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
    )

    # Verify head_bucket was called to check if bucket exists
    mock_s3_client.head_bucket.assert_called_once_with(Bucket="test-bucket")


@pytest.mark.asyncio
async def test_initialize_bucket_not_found(s3_backend, mock_s3_client):
    """Test initializing the S3 backend when bucket doesn't exist."""
    # Setup the mock client to raise a 404 error
    error_response = {"Error": {"Code": "404"}}
    mock_s3_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    # Initialize the backend
    await s3_backend.initialize()

    # Verify create_bucket was called
    mock_s3_client.create_bucket.assert_called_once_with(Bucket="test-bucket")


@pytest.mark.asyncio
async def test_initialize_error(s3_backend, mock_s3_client):
    """Test initializing the S3 backend with an error."""
    # Setup the mock client to raise a non-404 error
    error_response = {"Error": {"Code": "403"}}
    mock_s3_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    # Initialize the backend should raise an error
    with pytest.raises(StorageBackendError):
        await s3_backend.initialize()


@pytest.mark.asyncio
async def test_shutdown(s3_backend):
    """Test shutting down the S3 backend."""
    # Initialize the backend first
    with patch("boto3.client"):
        await s3_backend.initialize()

    # Shutdown the backend
    await s3_backend.shutdown()

    # Verify client is None
    assert s3_backend._client is None


@pytest.mark.asyncio
async def test_get_object(s3_backend, mock_s3_client):
    """Test getting an object from S3."""
    # Setup the mock client
    mock_body = MagicMock()
    mock_body.read.return_value = b"test data"

    mock_s3_client.get_object.return_value = {
        "Body": mock_body,
        "Metadata": {"content-type": "text/plain"},
        "ContentLength": 9,
        "LastModified": datetime.datetime.now(),
    }

    # Initialize the backend
    await s3_backend.initialize()

    # Get the object
    obj = await s3_backend.get_object("test/object.txt")

    # Verify get_object was called
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-bucket", Key="test/object.txt"
    )

    # Verify the returned object
    assert isinstance(obj, StorageObject)
    assert obj.path == "test/object.txt"
    assert obj.content == b"test data"
    assert obj.size == 9
    assert "content-type" in obj.metadata


@pytest.mark.asyncio
async def test_get_object_not_found(s3_backend, mock_s3_client):
    """Test getting a non-existent object from S3."""
    # Setup the mock client to raise a NoSuchKey error
    error_response = {"Error": {"Code": "NoSuchKey"}}
    mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")

    # Initialize the backend
    await s3_backend.initialize()

    # Get the object should raise an error
    with pytest.raises(StorageBackendError, match="Object not found"):
        await s3_backend.get_object("test/object.txt")


@pytest.mark.asyncio
async def test_put_object(s3_backend, mock_s3_client):
    """Test putting an object to S3."""
    # Setup the mock client
    mock_s3_client.put_object.return_value = {}

    # For get_object_metadata which is called after put_object
    mock_s3_client.head_object.return_value = {
        "ContentLength": 9,
        "LastModified": datetime.datetime.now(),
        "Metadata": {"content-type": "text/plain"},
    }

    # Initialize the backend
    await s3_backend.initialize()

    # Put the object
    metadata = {"content-type": "text/plain"}
    result = await s3_backend.put_object("test/object.txt", b"test data", metadata)

    # Verify put_object was called with correct parameters
    mock_s3_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test/object.txt",
        Body=b"test data",
        Metadata={"content-type": "text/plain"},
    )

    # Verify the returned metadata
    assert isinstance(result, StorageObjectMetadata)
    assert result.path == "test/object.txt"
    assert result.size == 9


@pytest.mark.asyncio
async def test_delete_object(s3_backend, mock_s3_client):
    """Test deleting an object from S3."""
    # Setup the mock client
    mock_s3_client.delete_object.return_value = {}

    # Initialize the backend
    await s3_backend.initialize()

    # Delete the object
    await s3_backend.delete_object("test/object.txt")

    # Verify delete_object was called
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key="test/object.txt"
    )


@pytest.mark.asyncio
async def test_list_objects(s3_backend, mock_s3_client):
    """Test listing objects in S3."""
    # Setup the mock client
    mock_paginator = MagicMock()
    mock_s3_client.get_paginator.return_value = mock_paginator

    # Create a mock page iterator
    now = datetime.datetime.now()
    mock_page_iterator = [
        {
            "Contents": [
                {
                    "Key": "test/object1.txt",
                    "Size": 9,
                    "LastModified": now,
                },
                {
                    "Key": "test/object2.txt",
                    "Size": 10,
                    "LastModified": now,
                },
            ]
        }
    ]
    mock_paginator.paginate.return_value = mock_page_iterator

    # Initialize the backend
    await s3_backend.initialize()

    # List objects
    objects = await s3_backend.list_objects("test/")

    # Verify get_paginator was called
    mock_s3_client.get_paginator.assert_called_once_with("list_objects_v2")

    # Verify paginate was called with correct parameters
    mock_paginator.paginate.assert_called_once_with(
        Bucket="test-bucket", Prefix="test/"
    )

    # Verify the returned objects
    assert len(objects) == 2
    assert objects[0].path == "test/object1.txt"
    assert objects[0].size == 9
    assert objects[1].path == "test/object2.txt"
    assert objects[1].size == 10


@pytest.mark.asyncio
async def test_list_objects_empty(s3_backend, mock_s3_client):
    """Test listing objects when there are none."""
    # Setup the mock client
    mock_paginator = MagicMock()
    mock_s3_client.get_paginator.return_value = mock_paginator

    # Create a mock page iterator with no Contents
    mock_page_iterator = [{}]
    mock_paginator.paginate.return_value = mock_page_iterator

    # Initialize the backend
    await s3_backend.initialize()

    # List objects
    objects = await s3_backend.list_objects("test/")

    # Verify the returned objects
    assert len(objects) == 0


@pytest.mark.asyncio
async def test_object_exists(s3_backend, mock_s3_client):
    """Test checking if an object exists."""
    # Setup the mock client
    mock_s3_client.head_object.return_value = {}

    # Initialize the backend
    await s3_backend.initialize()

    # Check if object exists
    exists = await s3_backend.object_exists("test/object.txt")

    # Verify head_object was called
    mock_s3_client.head_object.assert_called_once_with(
        Bucket="test-bucket", Key="test/object.txt"
    )

    # Verify the result
    assert exists is True


@pytest.mark.asyncio
async def test_object_does_not_exist(s3_backend, mock_s3_client):
    """Test checking if a non-existent object exists."""
    # Setup the mock client to raise a 404 error
    error_response = {"Error": {"Code": "404"}}
    mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    # Initialize the backend
    await s3_backend.initialize()

    # Check if object exists
    exists = await s3_backend.object_exists("test/object.txt")

    # Verify the result
    assert exists is False


@pytest.mark.asyncio
async def test_get_object_metadata(s3_backend, mock_s3_client):
    """Test getting object metadata."""
    # Setup the mock client
    now = datetime.datetime.now()
    mock_s3_client.head_object.return_value = {
        "ContentLength": 9,
        "LastModified": now,
        "Metadata": {"content-type": "text/plain"},
    }

    # Initialize the backend
    await s3_backend.initialize()

    # Get object metadata
    metadata = await s3_backend.get_object_metadata("test/object.txt")

    # Verify head_object was called
    mock_s3_client.head_object.assert_called_once_with(
        Bucket="test-bucket", Key="test/object.txt"
    )

    # Verify the returned metadata
    assert isinstance(metadata, StorageObjectMetadata)
    assert metadata.path == "test/object.txt"
    assert metadata.size == 9
    assert metadata.last_modified == now.isoformat()


@pytest.mark.asyncio
async def test_get_object_metadata_not_found(s3_backend, mock_s3_client):
    """Test getting metadata for a non-existent object."""
    # Setup the mock client to raise a 404 error
    error_response = {"Error": {"Code": "404"}}
    mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    # Initialize the backend
    await s3_backend.initialize()

    # Get object metadata should raise an error
    with pytest.raises(StorageBackendError, match="Object not found"):
        await s3_backend.get_object_metadata("test/object.txt")


@pytest.mark.asyncio
async def test_check_client_not_initialized(s3_backend):
    """Test checking client when not initialized."""
    # Don't initialize the backend

    # Any operation should raise an error
    with pytest.raises(StorageBackendError, match="S3 client is not initialized"):
        await s3_backend.get_object("test/object.txt")
