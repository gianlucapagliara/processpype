"""Example usage of ProcessPype framework.

Demonstrates registering and running example services.
"""

import asyncio

from processpype.core import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.examples import CounterService, HelloService, TickerService


async def main() -> None:
    app = Application(
        ApplicationConfiguration(
            title="Example App",
            version="1.0.0",
        )
    )

    await app.initialize()

    # Register example services
    app.register_service(HelloService)
    app.register_service(CounterService)
    app.register_service(TickerService)

    # Start services
    await app.start_service("hello")
    await app.start_service("counter")
    await app.start_service("ticker")

    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
