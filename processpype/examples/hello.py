"""HelloService — Minimal service example.

Demonstrates:
- Basic Service/ServiceManager implementation
- Service that requires no configuration
- Simple start/stop lifecycle
"""

from processpype.core.service import Service, ServiceManager


class HelloManager(ServiceManager):
    """Manager that logs a greeting on start and farewell on stop."""

    async def start(self) -> None:
        self.logger.info("Hello from ProcessPype!")

    async def stop(self) -> None:
        self.logger.info("Goodbye from ProcessPype!")


class HelloService(Service):
    """A minimal service that requires no configuration.

    Usage::

        app.register_service(HelloService)
        await app.start_service("hello")
    """

    configuration_class = None  # type: ignore[assignment]

    def create_manager(self) -> HelloManager:
        return HelloManager(self.logger)

    def requires_configuration(self) -> bool:
        return False
