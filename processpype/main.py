"""Main entry point for ProcessPype."""

import asyncio
import logging

from .core.application import Application


async def main(
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "info"
) -> None:
    """Start the ProcessPype application.

    Args:
        host: Server host
        port: Server port
        log_level: Logging level
    """
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and start application
    app = Application(host=host, port=port)

    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
