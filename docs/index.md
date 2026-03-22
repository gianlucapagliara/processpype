# ProcessPype

[![CI](https://github.com/gianlucapagliara/processpype/actions/workflows/ci.yml/badge.svg)](https://github.com/gianlucapagliara/processpype/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gianlucapagliara/processpype/branch/main/graph/badge.svg)](https://codecov.io/gh/gianlucapagliara/processpype)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/processpype)](https://pypi.org/project/processpype/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular application framework for building service-oriented Python applications with FastAPI integration, structured logging, and a clear service lifecycle.

## Features

- **Service Framework** --- Define services with a clear lifecycle and automatic REST API endpoints
- **FastAPI Integration** --- Each service automatically exposes HTTP endpoints for status, start, stop, and configuration
- **Configuration Management** --- YAML file, environment variable, and programmatic configuration with Pydantic models
- **Pure Framework** --- No built-in services — provides the infrastructure for building your own with clear patterns and examples
- **REST API** --- Application-level endpoints for service discovery, registration, and lifecycle management
- **Observability** --- Structured logging with multiple formatters (JSON, color, text), log redaction, and OpenTelemetry tracing support (Logfire, OTLP gRPC/HTTP, console)
- **Type Safe** --- Fully typed with MyPy strict mode compliance
- **Well Tested** --- Comprehensive test suite with high coverage

## Quick Example

```python
import asyncio
from processpype import Application, ProcessPypeConfig
from processpype.examples import HelloService


async def main() -> None:
    config = ProcessPypeConfig(
        app={"title": "My App"},
        server={"port": 8080},
    )
    async with Application(config) as app:
        await app.initialize()
        service = app.register_service(HelloService)
        await app.start_service(service.name)
        print(f"Service state: {service.status.state}")


asyncio.run(main())
```

## Architecture Overview

ProcessPype is organized around three core abstractions:

- **Application** orchestrates the FastAPI server, configuration loading, and service lifecycle. Instantiate directly with `ProcessPypeConfig`.
- **Service** is the unit of work. Each service has a manager (business logic) and a router (HTTP API). Implement `create_manager()` to define what your service does.
- **ServiceManager** implements the actual `start()` and `stop()` logic for a service.

```
Application
├── ProcessPypeConfig     ── hierarchical app/server/logging config
├── ApplicationManager    ── service registry and lifecycle
├── ApplicationRouter     ── REST API for the application
└── Service (per service)
    ├── ServiceManager    ── business logic (start/stop)
    └── ServiceRouter     ── HTTP endpoints per service
```

ProcessPype is a pure framework --- it provides the infrastructure for building services but does not ship any built-in service implementations. See the [example services](getting-started/quickstart.md) in `processpype.examples` for ready-made templates.

## Next Steps

- [Installation](getting-started/installation.md) --- Set up ProcessPype in your project
- [Quick Start](getting-started/quickstart.md) --- Build your first application and service
- [User Guide](guide/application.md) --- Learn about the application lifecycle and service patterns
- [API Reference](api/application.md) --- Full API documentation
