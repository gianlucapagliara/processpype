"""Database service models."""

from typing import Any, Literal

from pydantic import Field

from processpype.core.configuration.models import ServiceConfiguration


class DatabaseConfiguration(ServiceConfiguration):
    """Configuration for the DatabaseService."""

    engine: Literal["sqlite", "postgres"] = Field(
        default="sqlite",
        description="Database engine to use",
    )
    connection_string: str = Field(
        default="sqlite:///data/database.db",
        description="Database connection string",
    )
    pool_size: int = Field(
        default=5,
        description="Connection pool size",
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum number of connections to overflow",
    )
    pool_timeout: int = Field(
        default=30,
        description="Connection pool timeout in seconds",
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL statements to stdout",
    )


class Transaction:
    """Database transaction context manager."""

    def __init__(self, connection: Any):
        """Initialize the transaction.

        Args:
            connection: Database connection
        """
        self.connection = connection
        self.transaction = None

    async def __aenter__(self) -> "Transaction":
        """Enter the transaction context.

        Returns:
            The transaction instance
        """
        self.transaction = await self.connection.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the transaction context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self.transaction is None:
            return

        if exc_type is not None:
            await self.transaction.rollback()
        else:
            await self.transaction.commit()
