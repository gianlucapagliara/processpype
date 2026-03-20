# ProcessPype

[![CI](https://github.com/gianlucapagliara/processpype/actions/workflows/ci.yml/badge.svg)](https://github.com/gianlucapagliara/processpype/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gianlucapagliara/processpype/branch/main/graph/badge.svg)](https://codecov.io/gh/gianlucapagliara/processpype)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/processpype)](https://pypi.org/project/processpype/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular application framework for building service-oriented Python applications with built-in FastAPI integration, structured logging, and pluggable services.

## Features

- **Service Framework** --- Define services with a clear lifecycle and automatic REST API endpoints
- **FastAPI Integration** --- Each service automatically exposes HTTP endpoints for status, start, stop, and configuration
- **Configuration Management** --- YAML file, environment variable, and programmatic configuration with Pydantic models
- **Pluggable Services** --- Built-in clock, database, storage, notification, and monitoring services
- **REST API** --- Application-level endpoints for service discovery, registration, and lifecycle management
- **Structured Logging** --- Integrated Logfire support for production-grade observability
- **Type Safe** --- Fully typed with MyPy strict mode compliance
- **Well Tested** --- Comprehensive test suite with high coverage

## Quick Example

```python
import asyncio
from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration, ServiceConfiguration
from processpype.core.service.service import Service
from processpype.core.service.manager import ServiceManager


class WorkerManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("Worker started")

    async def stop(self) -> None:
        self.logger.info("Worker stopped")


class WorkerService(Service):
    configuration_class = ServiceConfiguration

    def create_manager(self) -> WorkerManager:
        return WorkerManager(self.logger)

    def requires_configuration(self) -> bool:
        return False


async def main() -> None:
    config = ApplicationConfiguration(title="My App", port=8080)
    async with Application(config) as app:
        await app.initialize()
        service = app.register_service(WorkerService)
        await app.start_service(service.name)
        print(f"Service state: {service.status.state}")


asyncio.run(main())
```

## Architecture Overview

ProcessPype is organized around three core abstractions:

- **Application** orchestrates the FastAPI server, configuration loading, and service lifecycle. Use `Application.create()` for YAML-based setup or instantiate directly with `ApplicationConfiguration`.
- **Service** is the unit of work. Each service has a manager (business logic) and a router (HTTP API). Implement `create_manager()` to define what your service does.
- **ServiceManager** implements the actual `start()` and `stop()` logic for a service.

```
Application
├── ApplicationManager    ── service registry and lifecycle
├── ApplicationRouter     ── REST API for the application
└── Service (per service)
    ├── ServiceManager    ── business logic (start/stop)
    └── ServiceRouter     ── HTTP endpoints per service

Built-in Services
├── ClockService          ── chronopype clock management
├── DatabaseService       ── SQLite / PostgreSQL access
├── StorageService        ── local filesystem / S3
├── NotificationService   ── console / email channels
└── SystemMonitoringService ── CPU, memory, disk metrics
```

## Next Steps

- [Installation](getting-started/installation.md) --- Set up ProcessPype in your project
- [Quick Start](getting-started/quickstart.md) --- Build your first application and service
- [User Guide](guide/application.md) --- Learn about the application lifecycle and service patterns
- [API Reference](api/application.md) --- Full API documentation
