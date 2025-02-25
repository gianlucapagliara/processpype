"""SQLite database engine implementation."""

import logging
import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


class SQLiteEngine:
    """SQLite database engine implementation."""

    def __init__(
        self,
        connection_string: str,
        logger: logging.Logger,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
    ):
        """Initialize the SQLite engine.

        Args:
            connection_string: Database connection string
            logger: Logger instance
            echo: Whether to echo SQL statements
            pool_size: Connection pool size
            max_overflow: Maximum number of connections to overflow
            pool_timeout: Connection pool timeout in seconds
        """
        self.logger = logger
        self.connection_string = connection_string
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.engine: AsyncEngine | None = None
        self.connection: AsyncConnection | None = None

    async def start(self) -> None:
        """Start the SQLite engine.

        This method creates the database engine and connection pool.

        Raises:
            ImportError: If SQLite dependencies are not installed
            Exception: If the database connection fails
        """
        try:
            import aiosqlite
        except ImportError as e:
            self.logger.error(f"Failed to import SQLite dependencies: {e}")
            raise ImportError(
                "SQLite dependencies not installed. "
                "Install with 'pip install aiosqlite sqlalchemy'"
            ) from e

        # Convert connection string to async format if needed
        conn_str = self.connection_string
        if not conn_str.startswith("sqlite+aiosqlite://"):
            conn_str = conn_str.replace("sqlite://", "sqlite+aiosqlite://")

        # Ensure the directory exists for file-based SQLite
        if "sqlite+aiosqlite:///" in conn_str and not conn_str.endswith(":memory:"):
            db_path = conn_str.split("sqlite+aiosqlite:///")[1]
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info(f"Created directory for SQLite database: {db_dir}")

        try:
            self.engine = create_async_engine(
                conn_str,
                echo=self.echo,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
            )
            self.connection = await self.engine.connect()
            self.logger.info("SQLite database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    async def stop(self) -> None:
        """Stop the SQLite engine.

        This method closes the database connection and disposes of the engine.
        """
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None

        self.logger.info("SQLite engine stopped successfully")

    async def execute(self, query: str, *args, **kwargs) -> Any:
        """Execute a database query.

        Args:
            query: SQL query to execute
            *args: Positional arguments for the query
            **kwargs: Keyword arguments for the query

        Returns:
            Query execution result

        Raises:
            RuntimeError: If the database connection is not established
            Exception: If the query execution fails
        """
        if self.connection is None:
            raise RuntimeError("Database connection not established")

        try:
            # Convert string query to SQLAlchemy text object
            sql = text(query)
            # Bind parameters if provided
            if args or kwargs:
                sql = sql.bindparams(*args, **kwargs)
            result = await self.connection.execute(sql)
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
            RuntimeError: If the database connection is not established
            Exception: If the query execution fails
        """
        if self.connection is None:
            raise RuntimeError("Database connection not established")

        try:
            # Convert string query to SQLAlchemy text object
            sql = text(query)
            # Bind parameters if provided
            if args or kwargs:
                sql = sql.bindparams(*args, **kwargs)
            result = await self.connection.execute(sql)
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
            RuntimeError: If the database connection is not established
            Exception: If the query execution fails
        """
        if self.connection is None:
            raise RuntimeError("Database connection not established")

        try:
            # Convert string query to SQLAlchemy text object
            sql = text(query)
            # Bind parameters if provided
            if args or kwargs:
                sql = sql.bindparams(*args, **kwargs)
            result = await self.connection.execute(sql)
            rows = result.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}", extra={"query": query})
            raise
