"""Database service manager."""

import logging
from typing import Any

from sqlalchemy import text

from processpype.core.service.manager import ServiceManager
from processpype.services.database.models import DatabaseConfiguration, Transaction


class DatabaseManager(ServiceManager):
    """Manager for database operations."""

    def __init__(
        self, logger: logging.Logger, config: DatabaseConfiguration | None = None
    ):
        """Initialize the database manager.

        Args:
            logger: Logger instance for service operations
            config: Database configuration
        """
        super().__init__(logger)
        self._config = config
        self._engine = None
        self._connection = None

    @property
    def engine(self) -> Any:
        """Get the database engine.

        Returns:
            The database engine instance
        """
        return self._engine

    @property
    def connection(self) -> Any:
        """Get the database connection.

        Returns:
            The database connection instance
        """
        return self._connection

    def configure(self, config: DatabaseConfiguration) -> None:
        """Configure the database manager.

        Args:
            config: Database configuration
        """
        self._config = config

    async def start(self) -> None:
        """Start the database manager.

        This method creates the database engine and connection pool.

        Raises:
            ImportError: If required database dependencies are not installed
            Exception: If the database connection fails
        """
        if self._config is None:
            self.logger.warning("Database manager not configured, using defaults")
            self._config = DatabaseConfiguration()

        self.logger.info(
            f"Starting database manager with engine {self._config.engine}",
            extra={"connection_string": self._config.connection_string},
        )

        if self._config.engine == "sqlite":
            await self._start_sqlite()
        elif self._config.engine == "postgres":
            await self._start_postgres()
        else:
            raise ValueError(f"Unsupported database engine: {self._config.engine}")

        self.logger.info("Database manager started successfully")

    async def _start_sqlite(self) -> None:
        """Start the SQLite database engine.

        Raises:
            ImportError: If SQLite dependencies are not installed
            Exception: If the database connection fails
        """
        try:
            import aiosqlite
            from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
        except ImportError as e:
            self.logger.error(f"Failed to import SQLite dependencies: {e}")
            raise ImportError(
                "SQLite dependencies not installed. "
                "Install with 'pip install aiosqlite sqlalchemy'"
            ) from e

        # Ensure config is not None (should be set in start method)
        if self._config is None:
            self._config = DatabaseConfiguration()

        # Convert connection string to async format if needed
        conn_str = self._config.connection_string
        if not conn_str.startswith("sqlite+aiosqlite://"):
            conn_str = conn_str.replace("sqlite://", "sqlite+aiosqlite://")

        try:
            self._engine = create_async_engine(
                conn_str,
                echo=self._config.echo,
                pool_size=self._config.pool_size,
                max_overflow=self._config.max_overflow,
                pool_timeout=self._config.pool_timeout,
            )
            self._connection = await self._engine.connect()
            self.logger.info("SQLite database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    async def _start_postgres(self) -> None:
        """Start the PostgreSQL database engine.

        Raises:
            ImportError: If PostgreSQL dependencies are not installed
            Exception: If the database connection fails
        """
        try:
            import asyncpg
            from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
        except ImportError as e:
            self.logger.error(f"Failed to import PostgreSQL dependencies: {e}")
            raise ImportError(
                "PostgreSQL dependencies not installed. "
                "Install with 'pip install asyncpg sqlalchemy'"
            ) from e

        # Ensure config is not None (should be set in start method)
        if self._config is None:
            self._config = DatabaseConfiguration()

        # Convert connection string to async format if needed
        conn_str = self._config.connection_string
        if not conn_str.startswith("postgresql+asyncpg://"):
            conn_str = conn_str.replace("postgresql://", "postgresql+asyncpg://")
            conn_str = conn_str.replace("postgres://", "postgresql+asyncpg://")

        try:
            self._engine = create_async_engine(
                conn_str,
                echo=self._config.echo,
                pool_size=self._config.pool_size,
                max_overflow=self._config.max_overflow,
                pool_timeout=self._config.pool_timeout,
            )
            self._connection = await self._engine.connect()
            self.logger.info("PostgreSQL database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL database: {e}")
            raise

    async def stop(self) -> None:
        """Stop the database manager.

        This method closes the database connection and disposes of the engine.
        """
        self.logger.info("Stopping database manager")
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

        self.logger.info("Database manager stopped successfully")

    async def execute(self, query: str, *args, **kwargs) -> Any:
        """Execute a database query.

        Args:
            query: SQL query to execute
            *args: Positional arguments for the query
            **kwargs: Keyword arguments for the query

        Returns:
            Query execution result

        Raises:
            Exception: If the query execution fails
        """
        if self._connection is None:
            raise RuntimeError("Database connection not established")

        try:
            # Convert string query to SQLAlchemy text object
            sql = text(query)
            # Bind parameters if provided
            if args or kwargs:
                sql = sql.bindparams(*args, **kwargs)
            result = await self._connection.execute(sql)
            return result
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}", extra={"query": query})
            raise

    async def fetch_one(self, query: str, *args, **kwargs) -> dict[str, Any] | None:
        """Fetch a single row from the database.

        Args:
            query: SQL query to execute
            *args: Positional arguments for the query
            **kwargs: Keyword arguments for the query

        Returns:
            A single row as a dictionary, or None if no rows were found

        Raises:
            Exception: If the query execution fails
        """
        if self._connection is None:
            raise RuntimeError("Database connection not established")

        try:
            # Convert string query to SQLAlchemy text object
            sql = text(query)
            # Bind parameters if provided
            if args or kwargs:
                sql = sql.bindparams(*args, **kwargs)
            result = await self._connection.execute(sql)
            row = result.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}", extra={"query": query})
            raise

    async def fetch_all(self, query: str, *args, **kwargs) -> list[dict[str, Any]]:
        """Fetch multiple rows from the database.

        Args:
            query: SQL query to execute
            *args: Positional arguments for the query
            **kwargs: Keyword arguments for the query

        Returns:
            A list of rows as dictionaries

        Raises:
            Exception: If the query execution fails
        """
        if self._connection is None:
            raise RuntimeError("Database connection not established")

        try:
            # Convert string query to SQLAlchemy text object
            sql = text(query)
            # Bind parameters if provided
            if args or kwargs:
                sql = sql.bindparams(*args, **kwargs)
            result = await self._connection.execute(sql)
            rows = result.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}", extra={"query": query})
            raise

    async def begin_transaction(self) -> Transaction:
        """Begin a database transaction.

        Returns:
            A transaction context manager

        Raises:
            RuntimeError: If the database connection is not established
        """
        if self._connection is None:
            raise RuntimeError("Database connection not established")

        return Transaction(self._connection)
