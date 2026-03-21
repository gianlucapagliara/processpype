"""Example services demonstrating the ProcessPype framework patterns.

These lightweight services serve as templates for building your own services.
They have no external dependencies beyond the framework itself.

- HelloService: Minimal service with no configuration required
- CounterService: Service with configuration and custom router endpoints
- TickerService: Service with a background async loop
"""

from processpype.examples.counter import CounterService
from processpype.examples.hello import HelloService
from processpype.examples.ticker import TickerService

__all__ = [
    "HelloService",
    "CounterService",
    "TickerService",
]
