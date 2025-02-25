"""Tests for the database models."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from processpype.services.database.models import DatabaseConfiguration, Transaction


def test_database_configuration_defaults():
    """Test the default values of DatabaseConfiguration."""
    config = DatabaseConfiguration()
    assert config.engine == "sqlite"
    assert config.connection_string == "sqlite:///data/database.db"
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.pool_timeout == 30
    assert config.echo is False


def test_database_configuration_custom_values():
    """Test custom values for DatabaseConfiguration."""
    config = DatabaseConfiguration(
        engine="postgres",
        connection_string="postgresql://user:pass@localhost:5432/db",
        pool_size=10,
        max_overflow=20,
        pool_timeout=60,
        echo=True,
    )
    assert config.engine == "postgres"
    assert config.connection_string == "postgresql://user:pass@localhost:5432/db"
    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 60
    assert config.echo is True


@pytest.mark.asyncio
async def test_transaction_context_manager_success():
    """Test the Transaction context manager with successful execution."""
    # Mock connection and transaction
    connection = MagicMock()
    transaction = AsyncMock()
    connection.begin = AsyncMock(return_value=transaction)

    # Use the transaction context manager
    async with Transaction(connection) as tx:
        assert tx.connection == connection
        assert tx.transaction == transaction

    # Verify transaction methods were called
    connection.begin.assert_called_once()
    transaction.commit.assert_called_once()
    transaction.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_transaction_context_manager_exception():
    """Test the Transaction context manager with an exception."""
    # Mock connection and transaction
    connection = MagicMock()
    transaction = AsyncMock()
    connection.begin = AsyncMock(return_value=transaction)

    # Use the transaction context manager with an exception
    try:
        async with Transaction(connection):
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Verify transaction methods were called
    connection.begin.assert_called_once()
    transaction.rollback.assert_called_once()
    transaction.commit.assert_not_called()


@pytest.mark.asyncio
async def test_transaction_context_manager_none_transaction():
    """Test the Transaction context manager with None transaction."""
    # Mock connection
    connection = MagicMock()
    connection.begin = AsyncMock(return_value=None)

    # Use the transaction context manager
    async with Transaction(connection) as tx:
        assert tx.connection == connection
        assert tx.transaction is None

    # Verify transaction methods were called
    connection.begin.assert_called_once()
    # No exception should be raised when transaction is None
