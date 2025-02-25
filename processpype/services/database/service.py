"""Database service implementation."""

from typing import TYPE_CHECKING, Any

from processpype.core.models import ServiceState
from processpype.core.service.service import ConfigurationError, Service
from processpype.services.database.manager import DatabaseManager
from processpype.services.database.models import DatabaseConfiguration, Transaction


class DatabaseService(Service):
    """Service for database operations."""

    configuration_class = DatabaseConfiguration

    if TYPE_CHECKING:
        manager: DatabaseManager

    def create_manager(self) -> DatabaseManager:
        """Create the database manager.

        Returns:
            A DatabaseManager instance
        """
        return DatabaseManager(self.logger)

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
        return await self.manager.execute(query, *args, **kwargs)

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
        return await self.manager.fetch_one(query, *args, **kwargs)

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
        return await self.manager.fetch_all(query, *args, **kwargs)

    async def begin_transaction(self) -> Transaction:
        """Begin a database transaction.

        Returns:
            A transaction context manager

        Raises:
            RuntimeError: If the database connection is not established
        """
        return await self.manager.begin_transaction()

    async def start(self) -> None:
        """Start the database service.

        This method handles the common service startup logic and then
        configures the database manager with the service configuration.

        Raises:
            ConfigurationError: If service is not properly configured
            Exception: If service fails to start
        """
        # Don't call super().start() as it would call manager.start()
        # Instead, implement the necessary parts from the parent class

        # Validate configuration before starting if required
        if self.requires_configuration() and not self.status.is_configured:
            error_msg = f"Service {self.name} must be configured before starting"
            self.set_error(error_msg)
            raise ConfigurationError(error_msg)

        self.logger.info(
            f"Starting {self.name} service", extra={"service_state": self.status.state}
        )
        self.status.state = ServiceState.STARTING
        self.status.error = None

        # Configure the manager with the service configuration
        if self.config is not None:
            self.manager.configure(self.config)

        # Start the manager
        try:
            await self.manager.start()
            self.status.state = ServiceState.RUNNING
            self.logger.info(
                f"Database service started with engine {self.config.engine if self.config else 'unknown'}"
            )
        except Exception as e:
            error_msg = f"Failed to start database service: {e}"
            self.set_error(error_msg)
            raise
