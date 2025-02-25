"""Tests for the DatabaseService."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.core.models import ServiceState
from processpype.core.service.service import ConfigurationError
from processpype.services.database import DatabaseService
from processpype.services.database.models import DatabaseConfiguration, Transaction


@pytest.fixture
def database_service():
    """Create a database service for testing."""
    service = DatabaseService()
    # Reset the manager to avoid test interference
    service.manager.start = AsyncMock()
    service.manager.stop = AsyncMock()
    service.manager.configure = MagicMock()
    service.manager.execute = AsyncMock()
    service.manager.fetch_one = AsyncMock()
    service.manager.fetch_all = AsyncMock()
    service.manager.begin_transaction = AsyncMock()
    return service


@pytest.fixture
def sqlite_config():
    """Create a SQLite configuration for testing."""
    return DatabaseConfiguration(
        engine="sqlite",
        connection_string="sqlite:///data/test.db",
        echo=True,
    )


@pytest.fixture
def postgres_config():
    """Create a PostgreSQL configuration for testing."""
    return DatabaseConfiguration(
        engine="postgres",
        connection_string="postgresql://user:pass@localhost:5432/db",
        echo=True,
    )


@pytest.mark.asyncio
async def test_create_manager():
    """Test creating the database manager."""
    service = DatabaseService()
    assert service.manager is not None
    assert service.manager.logger is not None


@pytest.mark.asyncio
async def test_configuration_class():
    """Test the configuration class."""
    service = DatabaseService()
    assert service.configuration_class == DatabaseConfiguration


@pytest.mark.asyncio
async def test_start_without_configuration(database_service):
    """Test starting the service without configuration."""
    # Ensure service is not configured
    database_service.status.is_configured = False

    # Start the service
    with pytest.raises(ConfigurationError):
        await database_service.start()

    # Verify manager was not started
    database_service.manager.start.assert_not_called()


@pytest.mark.asyncio
async def test_start_with_configuration(database_service, sqlite_config):
    """Test starting the service with configuration."""
    # Configure the service
    database_service.configure(sqlite_config)

    # Start the service
    await database_service.start()

    # Verify manager was configured and started
    database_service.manager.configure.assert_called_once_with(sqlite_config)
    database_service.manager.start.assert_called_once()
    assert database_service.status.state == ServiceState.RUNNING


@pytest.mark.asyncio
async def test_start_with_manager_error(database_service, sqlite_config):
    """Test starting the service when the manager fails to start."""
    # Configure the service
    database_service.configure(sqlite_config)

    # Make manager.start raise an exception
    database_service.manager.start.side_effect = Exception("Failed to start")

    # Start the service
    with pytest.raises(Exception, match="Failed to start"):
        await database_service.start()

    # Verify error was set
    assert database_service.status.error is not None
    assert "Failed to start database service" in database_service.status.error


@pytest.mark.asyncio
async def test_stop(database_service):
    """Test stopping the service."""
    # Set service state to running
    database_service.status.state = ServiceState.RUNNING

    # Stop the service
    await database_service.stop()

    # Verify manager was stopped
    database_service.manager.stop.assert_called_once()
    assert database_service.status.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_execute(database_service):
    """Test executing a database query."""
    # Mock manager.execute
    mock_result = MagicMock()
    database_service.manager.execute.return_value = mock_result

    # Execute a query with named parameter
    result = await database_service.execute(
        "SELECT * FROM test WHERE id = :id", id=1, name="test"
    )

    # Verify manager.execute was called
    database_service.manager.execute.assert_called_once_with(
        "SELECT * FROM test WHERE id = :id", id=1, name="test"
    )
    assert result == mock_result


@pytest.mark.asyncio
async def test_fetch_one(database_service):
    """Test fetching a single row from the database."""
    # Mock manager.fetch_one
    mock_result = {"id": 1, "name": "test"}
    database_service.manager.fetch_one.return_value = mock_result

    # Fetch a row with named parameter
    result = await database_service.fetch_one("SELECT * FROM test WHERE id = :id", id=1)

    # Verify manager.fetch_one was called
    database_service.manager.fetch_one.assert_called_once_with(
        "SELECT * FROM test WHERE id = :id", id=1
    )
    assert result == mock_result


@pytest.mark.asyncio
async def test_fetch_all(database_service):
    """Test fetching multiple rows from the database."""
    # Mock manager.fetch_all
    mock_result = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
    database_service.manager.fetch_all.return_value = mock_result

    # Fetch rows
    result = await database_service.fetch_all("SELECT * FROM test")

    # Verify manager.fetch_all was called
    database_service.manager.fetch_all.assert_called_once_with("SELECT * FROM test")
    assert result == mock_result


@pytest.mark.asyncio
async def test_begin_transaction(database_service):
    """Test beginning a transaction."""
    # Mock manager.begin_transaction
    mock_transaction = MagicMock(spec=Transaction)
    database_service.manager.begin_transaction.return_value = mock_transaction

    # Begin a transaction
    result = await database_service.begin_transaction()

    # Verify manager.begin_transaction was called
    database_service.manager.begin_transaction.assert_called_once()
    assert result == mock_transaction


@pytest.mark.asyncio
async def test_configure_and_start(database_service, sqlite_config):
    """Test configuring and starting the service in one step."""
    # Configure and start the service
    await database_service.configure_and_start(sqlite_config)

    # Verify service was configured and started
    assert database_service.config == sqlite_config
    assert database_service.status.is_configured is True
    database_service.manager.configure.assert_called_once_with(sqlite_config)
    database_service.manager.start.assert_called_once()
    assert database_service.status.state == ServiceState.RUNNING


@pytest.mark.asyncio
async def test_sqlite_integration():
    """Test SQLite integration with actual engine creation."""
    # Create a fresh service for this test to avoid mock interference
    database_service = DatabaseService()
    config = DatabaseConfiguration(
        engine="sqlite",
        connection_string="sqlite:///data/test.db",
        echo=True,
    )

    # Setup mocks
    with (
        patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine,
        patch.dict(sys.modules, {"aiosqlite": MagicMock()}),
        patch("processpype.services.database.engines.sqlite.text") as mock_text,
        patch("os.path.exists", return_value=False),
        patch("os.path.dirname", return_value="test"),
        patch("os.makedirs"),
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Setup mock text object
        mock_text_obj = MagicMock()
        mock_text.return_value = mock_text_obj
        mock_text_obj.bindparams.return_value = mock_text_obj

        # Configure and start the service
        await database_service.configure_and_start(config)

        # Verify SQLite engine was created
        mock_create_engine.assert_called_once()
        mock_engine.connect.assert_called_once()

        # Stop the service
        await database_service.stop()

        # Verify connection was closed
        mock_connection.close.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_integration():
    """Test PostgreSQL integration with actual engine creation."""
    # Create a fresh service for this test to avoid mock interference
    database_service = DatabaseService()
    config = DatabaseConfiguration(
        engine="postgres",
        connection_string="postgresql://user:pass@localhost:5432/db",
        echo=True,
    )

    # Setup mocks
    with (
        patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine,
        patch.dict(sys.modules, {"asyncpg": MagicMock()}),
        patch("processpype.services.database.engines.postgres.text") as mock_text,
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Setup mock text object
        mock_text_obj = MagicMock()
        mock_text.return_value = mock_text_obj
        mock_text_obj.bindparams.return_value = mock_text_obj

        # Configure and start the service
        await database_service.configure_and_start(config)

        # Verify PostgreSQL engine was created
        mock_create_engine.assert_called_once()
        mock_engine.connect.assert_called_once()

        # Stop the service
        await database_service.stop()

        # Verify connection was closed
        mock_connection.close.assert_called_once()
        mock_engine.dispose.assert_called_once()
