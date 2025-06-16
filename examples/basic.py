"""Example usage of ProcessPype framework."""

import asyncio

from processpype.core import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.services.monitoring.system import SystemMonitoringService


async def main() -> None:
    # Create application with Logfire integration
    app = Application(
        ApplicationConfiguration(
            title="Example App",
        )
    )

    # Initialize application
    await app.initialize()

    # Register monitoring service
    monitoring = app.register_service(SystemMonitoringService)

    # Start monitoring service
    await app.start_service(monitoring.name)

    try:
        # Start application (this will block until interrupted)
        await app.start()
    except KeyboardInterrupt:
        # Stop application and services
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
