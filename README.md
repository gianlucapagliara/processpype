# ProcessPype

[![CI](https://github.com/gianlucapagliara/processpype/actions/workflows/ci.yml/badge.svg)](https://github.com/gianlucapagliara/processpype/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gianlucapagliara/processpype/branch/main/graph/badge.svg)](https://codecov.io/gh/gianlucapagliara/processpype)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/processpype)](https://pypi.org/project/processpype/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://gianlucapagliara.github.io/processpype/)

A modular application framework for building service-oriented Python applications with FastAPI integration, structured logging, and a clear service lifecycle.

## Features

- **Service Framework**: Define services with a clear lifecycle (initialize, configure, start, stop) and automatic REST API endpoints
- **FastAPI Integration**: Each service automatically gets HTTP endpoints for status, start, stop, and configuration
- **Configuration Management**: YAML file, environment variable, and programmatic configuration with Pydantic models
- **Pure Framework**: No built-in services — provides the infrastructure for building your own with clear patterns and examples
- **REST API**: Application-level endpoints for service discovery, registration, and lifecycle management
- **Observability**: Structured logging with multiple formatters (JSON, color, text), log redaction, and OpenTelemetry tracing support (Logfire, OTLP gRPC/HTTP, console)
- **Type Safe**: Fully typed with MyPy strict mode
- **Well Tested**: Comprehensive test suite with high coverage

## Installation

```bash
# Using pip
pip install processpype

# Using uv
uv add processpype
```

## Quick Start

```python
import asyncio
from processpype import Application, ProcessPypeConfig, Service, ServiceManager, ServiceConfiguration


class GreeterManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("Greeter ready")

    async def stop(self) -> None:
        self.logger.info("Greeter stopped")


class GreeterService(Service):
    configuration_class = ServiceConfiguration

    def create_manager(self) -> GreeterManager:
        return GreeterManager(self.logger)

    def requires_configuration(self) -> bool:
        return False


async def main() -> None:
    config = ProcessPypeConfig(
        app={"title": "Hello App"},
        server={"port": 8080},
    )
    async with Application(config) as app:
        await app.initialize()
        service = app.register_service(GreeterService)
        await app.start_service(service.name)


asyncio.run(main())
```

## Core Components

- **Application**: Central orchestrator that manages the FastAPI server, configuration, and service lifecycle
  - `Application(config)`: Create an instance with a `ProcessPypeConfig`
  - `app.register_service(ServiceClass)`: Register and wire a service into the application
  - `app.start_service(name)` / `app.stop_service(name)`: Lifecycle control

- **Service**: Abstract base class for all services — implement `create_manager()` and optionally `create_router()`
  - Automatic REST endpoints: `GET /services/{name}`, `POST /services/{name}/start`, `POST /services/{name}/stop`
  - Built-in state machine: `INITIALIZED → CONFIGURED → STARTING → RUNNING → STOPPING → STOPPED`

- **ServiceManager**: Handles business logic for a service — implement `start()` and `stop()`

- **Configuration**: Hierarchical `ProcessPypeConfig` with `app`, `server`, and `logging` sections — Pydantic-validated, loadable from YAML files, environment variables, or kwargs

## Documentation

Full documentation is available at [gianlucapagliara.github.io/processpype](https://gianlucapagliara.github.io/processpype/).

## Development

ProcessPype uses [uv](https://docs.astral.sh/uv/) for dependency management and packaging:

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run type checks
uv run mypy processpype

# Run linting
uv run ruff check .

# Run pre-commit hooks
uv run pre-commit run --all-files
```
