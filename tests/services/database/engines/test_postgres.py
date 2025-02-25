"""Tests for the PostgreSQL engine."""

import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.services.database.engines.postgres import PostgresEngine


@pytest.fixture
def postgres_engine():
    """Create a PostgreSQL engine for testing."""
    logger = logging.getLogger("test_postgres_engine")
    return PostgresEngine(
        connection_string="postgresql://user:pass@localhost:5432/db",
        logger=logger,
        echo=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
    )


@pytest.mark.asyncio
async def test_start(postgres_engine):
    """Test starting the PostgreSQL engine."""
    # Mock PostgreSQL dependencies and SQLAlchemy
    with (
        patch.dict(sys.modules, {"asyncpg": MagicMock()}),
        patch(
            "processpype.services.database.engines.postgres.create_async_engine"
        ) as mock_create_engine,
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Start the engine
        await postgres_engine.start()

        # Verify engine was created with correct parameters
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert "postgresql+asyncpg://" in args[0]
        assert kwargs["echo"] == postgres_engine.echo
        assert kwargs["pool_size"] == postgres_engine.pool_size
        assert kwargs["max_overflow"] == postgres_engine.max_overflow
        assert kwargs["pool_timeout"] == postgres_engine.pool_timeout

        # Verify connection was established
        mock_engine.connect.assert_called_once()
        assert postgres_engine.engine == mock_engine
        assert postgres_engine.connection == mock_connection


@pytest.mark.asyncio
async def test_start_connection_string_conversion(postgres_engine):
    """Test starting the PostgreSQL engine with different connection string formats."""
    # Test with postgres:// prefix
    postgres_engine.connection_string = "postgres://user:pass@localhost:5432/db"

    # Mock PostgreSQL dependencies and SQLAlchemy
    with (
        patch.dict(sys.modules, {"asyncpg": MagicMock()}),
        patch(
            "processpype.services.database.engines.postgres.create_async_engine"
        ) as mock_create_engine,
    ):
        # Setup mock engine and connection
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        # Start the engine
        await postgres_engine.start()

        # Verify engine was created with correct connection string
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert "postgresql+asyncpg://" in args[0]
        assert "postgres://" not in args[0]


@pytest.mark.asyncio
async def test_start_import_error(postgres_engine):
    """Test starting the PostgreSQL engine when dependencies are missing."""
    # Mock missing PostgreSQL dependencies
    with (
        patch.dict(sys.modules, {"asyncpg": None}),
        pytest.raises(ImportError),
    ):
        # Start the engine
        await postgres_engine.start()


@pytest.mark.asyncio
async def test_stop(postgres_engine):
    """Test stopping the PostgreSQL engine."""
    # Setup mock engine and connection
    mock_engine = AsyncMock()
    mock_connection = AsyncMock()

    # Patch the engine and connection directly
    with (
        patch.object(postgres_engine, "engine", mock_engine),
        patch.object(postgres_engine, "connection", mock_connection),
    ):
        # Stop the engine
        await postgres_engine.stop()

        # Verify connection and engine were closed
        mock_connection.close.assert_called_once()
        mock_engine.dispose.assert_called_once()
        assert postgres_engine.connection is None
        assert postgres_engine.engine is None


@pytest.mark.asyncio
async def test_execute(postgres_engine):
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
            "processpype.services.database.engines.postgres.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(postgres_engine, "connection", mock_connection),
    ):
        # Execute a query
        result = await postgres_engine.execute(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        assert result == mock_result


@pytest.mark.asyncio
async def test_execute_no_connection(postgres_engine):
    """Test executing a query when no connection is established."""
    # Ensure no connection
    with patch.object(postgres_engine, "connection", None):
        # Execute a query
        with pytest.raises(RuntimeError, match="Database connection not established"):
            await postgres_engine.execute("SELECT * FROM test")


@pytest.mark.asyncio
async def test_execute_with_kwargs(postgres_engine):
    """Test executing a query with keyword arguments."""
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
            "processpype.services.database.engines.postgres.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(postgres_engine, "connection", mock_connection),
    ):
        # Execute a query with keyword arguments
        result = await postgres_engine.execute(
            "SELECT * FROM test WHERE id = :id AND name = :name",
            id=1,
            name="test",
        )

        # Verify query was executed
        mock_text.assert_called_once_with(
            "SELECT * FROM test WHERE id = :id AND name = :name"
        )
        mock_text_obj.bindparams.assert_called_once_with(id=1, name="test")
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        assert result == mock_result


@pytest.mark.asyncio
async def test_fetch_one(postgres_engine):
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
            "processpype.services.database.engines.postgres.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(postgres_engine, "connection", mock_connection),
        # Mock the dict function to return our expected dictionary
        patch(
            "processpype.services.database.engines.postgres.dict",
            return_value=mock_row_dict,
        ),
    ):
        # Fetch a row
        result = await postgres_engine.fetch_one(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        mock_result.fetchone.assert_called_once()
        assert result == {"id": 1, "name": "test"}


@pytest.mark.asyncio
async def test_fetch_one_none(postgres_engine):
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
            "processpype.services.database.engines.postgres.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(postgres_engine, "connection", mock_connection),
    ):
        # Fetch a row
        result = await postgres_engine.fetch_one(
            "SELECT * FROM test WHERE id = :id", id=1
        )

        # Verify result is None
        mock_text.assert_called_once_with("SELECT * FROM test WHERE id = :id")
        mock_text_obj.bindparams.assert_called_once_with(id=1)
        assert result is None


@pytest.mark.asyncio
async def test_fetch_all(postgres_engine):
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
            "processpype.services.database.engines.postgres.text",
            return_value=mock_text_obj,
        ) as mock_text,
        patch.object(postgres_engine, "connection", mock_connection),
        # Mock the dict function to return our expected dictionaries
        patch(
            "processpype.services.database.engines.postgres.dict",
            side_effect=[row1_dict, row2_dict],
        ),
    ):
        # Fetch rows
        result = await postgres_engine.fetch_all("SELECT * FROM test")

        # Verify query was executed
        mock_text.assert_called_once_with("SELECT * FROM test")
        mock_connection.execute.assert_called_once_with(mock_text_obj)
        mock_result.fetchall.assert_called_once()
        assert result == [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
