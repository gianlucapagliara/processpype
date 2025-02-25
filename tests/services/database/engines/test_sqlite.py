"""Tests for the SQLite engine."""

import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.services.database.engines.sqlite import SQLiteEngine


@pytest.fixture
def sqlite_engine():
    """Create a SQLite engine for testing."""
    logger = logging.getLogger("test_sqlite_engine")
    return SQLiteEngine(
        connection_string="sqlite:///test.db",
        logger=logger,
        echo=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
    )


@pytest.mark.asyncio
async def test_start(sqlite_engine):
    """Test starting the SQLite engine."""
    # Mock SQLite dependencies and directory creation
    with (
        patch.dict(sys.modules, {"aiosqlite": MagicMock()}),
        patch(
            "processpype.services.database.engines.sqlite.create_async_engine"
        ) as mock_create_engine,
        patch(
            "processpype.services.database.engines.sqlite.os.path.exists",
            return_value=False,
        ),
        patch(
            "processpype.services.database.engines.sqlite.os.path.dirname",
            return_value="test",
        ),
        patch(
            "processpype.services.database.engines.sqlite.os.makedirs"
        ) as mock_makedirs,
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Start the engine
        await sqlite_engine.start()

        # Verify directory was created
        mock_makedirs.assert_called_once()

        # Verify engine was created with correct parameters
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert "sqlite+aiosqlite://" in args[0]
        assert kwargs["echo"] == sqlite_engine.echo
        assert kwargs["pool_size"] == sqlite_engine.pool_size
        assert kwargs["max_overflow"] == sqlite_engine.max_overflow
        assert kwargs["pool_timeout"] == sqlite_engine.pool_timeout

        # Verify connection was established
        mock_engine.connect.assert_called_once()
        assert sqlite_engine.engine == mock_engine
        assert sqlite_engine.connection == mock_connection


@pytest.mark.asyncio
async def test_start_directory_exists(sqlite_engine):
    """Test starting the SQLite engine when the directory already exists."""
    # Mock SQLite dependencies and directory existence
    with (
        patch.dict(sys.modules, {"aiosqlite": MagicMock()}),
        patch(
            "processpype.services.database.engines.sqlite.create_async_engine"
        ) as mock_create_engine,
        patch(
            "processpype.services.database.engines.sqlite.os.path.exists",
            return_value=True,
        ),
        patch(
            "processpype.services.database.engines.sqlite.os.path.dirname",
            return_value="test",
        ),
        patch(
            "processpype.services.database.engines.sqlite.os.makedirs"
        ) as mock_makedirs,
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Start the engine
        await sqlite_engine.start()

        # Verify directory was not created
        mock_makedirs.assert_not_called()

        # Verify engine was created
        mock_create_engine.assert_called_once()


@pytest.mark.asyncio
async def test_start_import_error(sqlite_engine):
    """Test starting the SQLite engine when dependencies are missing."""
    # Mock missing SQLite dependencies
    with (
        patch.dict(sys.modules, {"aiosqlite": None}),
        pytest.raises(ImportError),
    ):
        # Start the engine
        await sqlite_engine.start()


@pytest.mark.asyncio
async def test_stop(sqlite_engine):
    """Test stopping the SQLite engine."""
    # Setup mock engine and connection
    mock_engine = AsyncMock()
    mock_connection = AsyncMock()

    # Patch the engine and connection directly
    with (
        patch.object(sqlite_engine, "engine", mock_engine),
        patch.object(sqlite_engine, "connection", mock_connection),
    ):
        # Stop the engine
        await sqlite_engine.stop()

        # Verify connection and engine were closed
        mock_connection.close.assert_called_once()
        mock_engine.dispose.assert_called_once()
        assert sqlite_engine.connection is None
        assert sqlite_engine.engine is None


@pytest.mark.asyncio
async def test_execute(sqlite_engine):
    """Test executing a database query."""
    # Setup mock connection
    mock_connection = AsyncMock()
    mock_result = MagicMock()
    mock_connection.execute.return_value = mock_result

    # Create a mock for the text function
    mock_text_obj = MagicMock()
    mock_text_obj.bindparams.return_value = mock_text_obj

    # Mock text function and patch connection
    with (
        patch(
            "processpype.services.database.engines.sqlite.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(sqlite_engine, "connection", mock_connection),
    ):
        # Execute a query
        result = await sqlite_engine.execute("SELECT * FROM test WHERE id = :id", id=1)

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        assert result == mock_result


@pytest.mark.asyncio
async def test_execute_no_connection(sqlite_engine):
    """Test executing a query when no connection is established."""
    # Ensure no connection
    with patch.object(sqlite_engine, "connection", None):
        # Execute a query
        with pytest.raises(RuntimeError, match="Database connection not established"):
            await sqlite_engine.execute("SELECT * FROM test")


@pytest.mark.asyncio
async def test_fetch_one(sqlite_engine):
    """Test fetching a single row from the database."""
    # Setup mock connection and result
    mock_connection = AsyncMock()
    mock_result = MagicMock()

    # Create a proper mock row that will convert to a dict correctly
    mock_row = MagicMock()
    mock_row_dict = {"id": 1, "name": "test"}
    # Make the row behave like a mapping
    mock_row.__iter__.return_value = mock_row_dict.items()
    mock_row.keys.return_value = mock_row_dict.keys()
    mock_row.__getitem__ = lambda self, key: mock_row_dict[key]

    mock_result.fetchone.return_value = mock_row
    mock_connection.execute.return_value = mock_result

    # Create a mock for the text function
    mock_text_obj = MagicMock()
    mock_text_obj.bindparams.return_value = mock_text_obj

    # Mock text function and patch connection
    with (
        patch(
            "processpype.services.database.engines.sqlite.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(sqlite_engine, "connection", mock_connection),
        # Mock the dict function to return our expected dictionary
        patch(
            "processpype.services.database.engines.sqlite.dict",
            return_value=mock_row_dict,
        ),
    ):
        # Fetch a row
        result = await sqlite_engine.fetch_one(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        mock_result.fetchone.assert_called_once()
        assert result == {"id": 1, "name": "test"}


@pytest.mark.asyncio
async def test_fetch_one_none(sqlite_engine):
    """Test fetching a single row that doesn't exist."""
    # Setup mock connection and result
    mock_connection = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_connection.execute.return_value = mock_result

    # Create a mock for the text function
    mock_text_obj = MagicMock()
    mock_text_obj.bindparams.return_value = mock_text_obj

    # Mock text function and patch connection
    with (
        patch(
            "processpype.services.database.engines.sqlite.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(sqlite_engine, "connection", mock_connection),
    ):
        # Fetch a row
        result = await sqlite_engine.fetch_one(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify result is None
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        assert result is None


@pytest.mark.asyncio
async def test_fetch_all(sqlite_engine):
    """Test fetching multiple rows from the database."""
    # Setup mock connection and result
    mock_connection = AsyncMock()
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
    mock_connection.execute.return_value = mock_result

    # Create a mock for the text function
    mock_text_obj = MagicMock()
    mock_text_obj.bindparams.return_value = mock_text_obj

    # Mock text function and patch connection
    with (
        patch(
            "processpype.services.database.engines.sqlite.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(sqlite_engine, "connection", mock_connection),
        # Mock the dict function to return our expected dictionaries
        patch(
            "processpype.services.database.engines.sqlite.dict",
            side_effect=[row1_dict, row2_dict],
        ),
    ):
        # Fetch rows
        result = await sqlite_engine.fetch_all("SELECT * FROM test")

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test")
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        mock_result.fetchall.assert_called_once()
        assert result == [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
