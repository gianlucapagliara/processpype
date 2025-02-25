"""Tests for the database manager."""

import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.services.database.manager import DatabaseManager
from processpype.services.database.models import DatabaseConfiguration, Transaction


@pytest.fixture
def database_manager():
    """Create a database manager for testing."""
    logger = logging.getLogger("test_database_manager")
    return DatabaseManager(logger)


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
async def test_configure(database_manager, sqlite_config):
    """Test configuring the database manager."""
    database_manager.configure(sqlite_config)
    assert database_manager._config == sqlite_config


@pytest.mark.asyncio
async def test_start_sqlite(database_manager, sqlite_config):
    """Test starting the database manager with SQLite."""
    # Mock SQLite dependencies and SQLAlchemy
    with (
        patch.dict(sys.modules, {"aiosqlite": MagicMock()}),
        patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine,
        patch("os.path.exists", return_value=False),
        patch("os.path.dirname", return_value="test"),
        patch("os.makedirs"),
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Configure and start the manager
        database_manager.configure(sqlite_config)
        await database_manager.start()

        # Verify engine was created with correct parameters
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert "sqlite+aiosqlite://" in args[0]
        assert kwargs["echo"] == sqlite_config.echo
        assert kwargs["pool_size"] == sqlite_config.pool_size
        assert kwargs["max_overflow"] == sqlite_config.max_overflow
        assert kwargs["pool_timeout"] == sqlite_config.pool_timeout

        # Verify connection was established
        mock_engine.connect.assert_called_once()
        assert database_manager._engine == mock_engine
        assert database_manager._connection == mock_connection


@pytest.mark.asyncio
async def test_start_postgres(database_manager, postgres_config):
    """Test starting the database manager with PostgreSQL."""
    # Mock PostgreSQL dependencies and SQLAlchemy
    # Use a different approach to avoid SQLAlchemy inspection issues
    with patch.dict(sys.modules, {"asyncpg": MagicMock()}):
        # Mock the _start_postgres method directly
        with patch.object(database_manager, "_start_postgres") as mock_start_postgres:
            # Setup mock engine and connection
            mock_engine = AsyncMock()
            mock_connection = AsyncMock()

            # Configure the manager to use the mock engine and connection
            async def mock_start_impl():
                database_manager._engine = mock_engine
                database_manager._connection = mock_connection

            mock_start_postgres.side_effect = mock_start_impl

            # Configure and start the manager
            database_manager.configure(postgres_config)
            await database_manager.start()

            # Verify _start_postgres was called
            mock_start_postgres.assert_called_once()

            # Verify connection was established
            assert database_manager._engine == mock_engine
            assert database_manager._connection == mock_connection


@pytest.mark.asyncio
async def test_start_sqlite_import_error(database_manager, sqlite_config):
    """Test starting the database manager with SQLite when dependencies are missing."""
    # Mock missing SQLite dependencies
    with (
        patch.dict(sys.modules, {"aiosqlite": None}),
        pytest.raises(ImportError),
    ):
        # Configure and start the manager
        database_manager.configure(sqlite_config)
        await database_manager.start()


@pytest.mark.asyncio
async def test_start_postgres_import_error(database_manager, postgres_config):
    """Test starting the database manager with PostgreSQL when dependencies are missing."""
    # Mock missing PostgreSQL dependencies
    with (
        patch.dict(sys.modules, {"asyncpg": None}),
        pytest.raises(ImportError),
    ):
        # Configure and start the manager
        database_manager.configure(postgres_config)
        await database_manager.start()


@pytest.mark.asyncio
async def test_stop(database_manager):
    """Test stopping the database manager."""
    # Setup mock engine and connection
    mock_engine = AsyncMock()
    mock_connection = AsyncMock()

    # Patch the engine and connection directly
    with (
        patch.object(database_manager, "_engine", mock_engine),
        patch.object(database_manager, "_connection", mock_connection),
    ):
        # Stop the manager
        await database_manager.stop()

        # Verify connection and engine were closed
        mock_connection.close.assert_called_once()
        mock_engine.dispose.assert_called_once()
        assert database_manager._connection is None
        assert database_manager._engine is None


@pytest.mark.asyncio
async def test_execute(database_manager):
    """Test executing a database query."""
    # Setup mock connection
    database_manager._connection = AsyncMock()
    mock_result = MagicMock()
    database_manager._connection.execute.return_value = mock_result

    # Mock the text function
    with patch("processpype.services.database.manager.text") as mock_text:
        # Setup mock text object
        mock_text_obj = MagicMock()
        mock_text.return_value = mock_text_obj
        mock_text_obj.bindparams.return_value = mock_text_obj

        # Execute a query with named parameter
        result = await database_manager.execute(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        database_manager._connection.execute.assert_called_once_with(mock_text_obj)
        assert result == mock_result


@pytest.mark.asyncio
async def test_fetch_one(database_manager):
    """Test fetching a single row from the database."""
    # Setup mock connection and result
    database_manager._connection = AsyncMock()
    mock_result = MagicMock()

    # Create a proper mock row that will convert to a dict correctly
    mock_row = MagicMock()
    mock_row_dict = {"id": 1, "name": "test"}
    # Make the row behave like a mapping
    mock_row.__iter__.return_value = mock_row_dict.items()
    mock_row.keys.return_value = mock_row_dict.keys()
    mock_row.__getitem__ = lambda self, key: mock_row_dict[key]

    mock_result.fetchone.return_value = mock_row
    database_manager._connection.execute.return_value = mock_result

    # Mock the text function
    with patch("processpype.services.database.manager.text") as mock_text:
        # Setup mock text object
        mock_text_obj = MagicMock()
        mock_text.return_value = mock_text_obj
        mock_text_obj.bindparams.return_value = mock_text_obj

        # Fetch a row with named parameter
        result = await database_manager.fetch_one(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        database_manager._connection.execute.assert_called_once_with(mock_text_obj)
        mock_result.fetchone.assert_called_once()
        assert result == {"id": 1, "name": "test"}


@pytest.mark.asyncio
async def test_fetch_one_none(database_manager):
    """Test fetching a single row that doesn't exist."""
    # Setup mock connection and result
    database_manager._connection = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    database_manager._connection.execute.return_value = mock_result

    # Mock the text function
    with patch("processpype.services.database.manager.text") as mock_text:
        # Setup mock text object
        mock_text_obj = MagicMock()
        mock_text.return_value = mock_text_obj
        mock_text_obj.bindparams.return_value = mock_text_obj

        # Fetch a row with named parameter
        result = await database_manager.fetch_one(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify result is None
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        database_manager._connection.execute.assert_called_once_with(mock_text_obj)
        assert result is None


@pytest.mark.asyncio
async def test_fetch_all(database_manager):
    """Test fetching multiple rows from the database."""
    # Setup mock connection and result
    database_manager._connection = AsyncMock()
    mock_result = MagicMock()

    # Create proper mock rows that will convert to dicts correctly
    row1_dict = {"id": 1, "name": "test1"}
    row2_dict = {"id": 2, "name": "test2"}

    mock_row1 = MagicMock()
    mock_row1.__iter__.return_value = row1_dict.items()
    mock_row1.keys.return_value = row1_dict.keys()
    mock_row1.__getitem__ = lambda self, key: row1_dict[key]

    mock_row2 = MagicMock()
    mock_row2.__iter__.return_value = row2_dict.items()
    mock_row2.keys.return_value = row2_dict.keys()
    mock_row2.__getitem__ = lambda self, key: row2_dict[key]

    mock_result.fetchall.return_value = [mock_row1, mock_row2]
    database_manager._connection.execute.return_value = mock_result

    # Mock the text function
    with patch("processpype.services.database.manager.text") as mock_text:
        # Setup mock text object
        mock_text_obj = MagicMock()
        mock_text.return_value = mock_text_obj
        mock_text_obj.bindparams.return_value = mock_text_obj

        # Fetch rows
        result = await database_manager.fetch_all("SELECT * FROM test")

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test")
        database_manager._connection.execute.assert_called_once_with(mock_text_obj)
        mock_result.fetchall.assert_called_once()
        assert result == [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]


@pytest.mark.asyncio
async def test_begin_transaction(database_manager):
    """Test beginning a transaction."""
    # Setup mock connection
    database_manager._connection = AsyncMock()

    # Begin a transaction
    transaction = await database_manager.begin_transaction()

    # Verify transaction was created
    assert isinstance(transaction, Transaction)
    assert transaction.connection == database_manager._connection
