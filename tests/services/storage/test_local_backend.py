"""Tests for the local storage backend."""

import tempfile
from pathlib import Path

import pytest

from processpype.services.storage.backends import LocalStorageBackend


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def local_backend(temp_dir):
    """Create a local storage backend for testing."""
    import logging

    logger = logging.getLogger("test_local_backend")
    backend = LocalStorageBackend(base_path=temp_dir, logger=logger)
    return backend


@pytest.mark.asyncio
async def test_initialize(local_backend, temp_dir):
    """Test initializing the local storage backend."""
    await local_backend.initialize()
    assert Path(temp_dir).exists()


@pytest.mark.asyncio
async def test_put_and_get_object(local_backend):
    """Test putting and getting an object."""
    # Initialize the backend
    await local_backend.initialize()

    # Test data
    path = "test/object.txt"
    data = b"Hello, world!"
    metadata = {"content-type": "text/plain"}

    # Put the object
    await local_backend.put_object(path, data, metadata)

    # Get the object
    obj = await local_backend.get_object(path)

    # Verify the object
    assert obj.path == path
    assert obj.content == data
    assert obj.size == len(data)
    assert obj.metadata == metadata


@pytest.mark.asyncio
async def test_list_objects(local_backend):
    """Test listing objects."""
    # Initialize the backend
    await local_backend.initialize()

    # Create some test objects
    await local_backend.put_object("test/object1.txt", b"Object 1")
    await local_backend.put_object("test/object2.txt", b"Object 2")
    await local_backend.put_object("other/object3.txt", b"Object 3")

    # List objects with prefix
    objects = await local_backend.list_objects("test")
    assert len(objects) == 2
    assert any(obj.path == "test/object1.txt" for obj in objects)
    assert any(obj.path == "test/object2.txt" for obj in objects)

    # List all objects
    objects = await local_backend.list_objects()
    assert len(objects) == 3


@pytest.mark.asyncio
async def test_delete_object(local_backend):
    """Test deleting an object."""
    # Initialize the backend
    await local_backend.initialize()

    # Create a test object
    path = "test/object.txt"
    await local_backend.put_object(path, b"Hello, world!")

    # Verify the object exists
    assert await local_backend.object_exists(path)

    # Delete the object
    await local_backend.delete_object(path)

    # Verify the object no longer exists
    assert not await local_backend.object_exists(path)


@pytest.mark.asyncio
async def test_get_object_metadata(local_backend):
    """Test getting object metadata."""
    # Initialize the backend
    await local_backend.initialize()

    # Create a test object
    path = "test/object.txt"
    data = b"Hello, world!"
    metadata = {"content-type": "text/plain"}
    await local_backend.put_object(path, data, metadata)

    # Get the object metadata
    obj_metadata = await local_backend.get_object_metadata(path)

    # Verify the metadata
    assert obj_metadata.path == path
    assert obj_metadata.size == len(data)
    assert obj_metadata.metadata == metadata
