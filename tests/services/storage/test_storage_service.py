"""Tests for the StorageService."""

import tempfile

import pytest

from processpype.core.models import ServiceState
from processpype.services.storage import StorageService
from processpype.services.storage.models import StorageBackend, StorageConfiguration


@pytest.fixture
def storage_config():
    """Create a storage configuration for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfiguration(
            backend=StorageBackend.LOCAL,
            base_path=temp_dir,
        )
        yield config


@pytest.fixture
def storage_service(storage_config):
    """Create a storage service for testing."""
    service = StorageService()
    service.configure(storage_config)
    return service


@pytest.mark.asyncio
async def test_service_lifecycle(storage_service):
    """Test the storage service lifecycle."""
    # Start the service
    await storage_service.start()
    assert storage_service.status.state == ServiceState.RUNNING

    # Stop the service
    await storage_service.stop()
    assert storage_service.status.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_service_operations(storage_service):
    """Test storage service operations."""
    # Start the service
    await storage_service.start()

    try:
        # Test data
        path = "test/object.txt"
        data = b"Hello, world!"
        metadata = {"content-type": "text/plain"}

        # Put an object
        await storage_service.put_object(path, data, metadata)

        # Check if the object exists
        assert await storage_service.object_exists(path)

        # Get the object
        obj = await storage_service.get_object(path)
        assert obj.path == path
        assert obj.content == data
        assert obj.size == len(data)

        # Get just the content
        content = await storage_service.get_object_content(path)
        assert content == data

        # Get metadata
        meta = await storage_service.get_object_metadata(path)
        assert meta.path == path
        assert meta.size == len(data)

        # List objects
        objects = await storage_service.list_objects()
        assert len(objects) == 1
        assert objects[0].path == path

        # Delete the object
        await storage_service.delete_object(path)
        assert not await storage_service.object_exists(path)

    finally:
        # Stop the service
        await storage_service.stop()


@pytest.mark.asyncio
async def test_service_with_s3_config():
    """Test creating a service with S3 configuration."""
    # Create an S3 configuration
    config = StorageConfiguration(
        backend=StorageBackend.S3,
        s3_bucket="test-bucket",
        s3_region="us-west-2",
    )

    # Create and configure the service
    service = StorageService()
    service.configure(config)

    # We're not actually starting the service to avoid S3 calls
    # Just verify the service was created and configured
    assert isinstance(service, StorageService)
    assert service.status.state == ServiceState.CONFIGURED
