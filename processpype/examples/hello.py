"""HelloService — Minimal service example."""

from processpype.service import Service, ServiceManager


class HelloManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("Hello from ProcessPype!")

    async def stop(self) -> None:
        self.logger.info("Goodbye from ProcessPype!")


class HelloService(Service):
    """A minimal service that requires no configuration."""

    configuration_class = None  # type: ignore[assignment]

    def create_manager(self) -> HelloManager:
        return HelloManager(self.logger)

    def requires_configuration(self) -> bool:
        return False
