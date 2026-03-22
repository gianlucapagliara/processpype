"""Example usage of ProcessPype framework.

Demonstrates creating a minimal service and running the application.
"""

import asyncio
import logging

from processpype import Application, ProcessPypeConfig, Service, ServiceManager
from processpype.config.models import ServiceConfiguration


class HelloManager(ServiceManager):
    """Simple manager that logs a greeting on start."""

    async def start(self) -> None:
        self.logger.info("Hello from the example service!")

    async def stop(self) -> None:
        self.logger.info("Goodbye from the example service!")


class HelloService(Service):
    """Minimal example service."""

    configuration_class = ServiceConfiguration

    def create_manager(self) -> ServiceManager:
        return HelloManager(self.logger)

    def requires_configuration(self) -> bool:
        return False


async def main() -> None:
    config = ProcessPypeConfig(
        app={"title": "Example App", "version": "1.0.0"},
    )
    app = Application(config)
    await app.initialize()

    # Register and start the example service
    app.register_service(HelloService)
    await app.start_service("hello")

    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
