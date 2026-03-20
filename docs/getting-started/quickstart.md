# Quick Start

This guide walks through the basics of ProcessPype: creating an application, defining a service, and running it.

## Creating an Application

An `Application` is the top-level orchestrator. Create one with an `ApplicationConfiguration`:

```python
import asyncio
from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration

config = ApplicationConfiguration(
    title="My Application",
    host="0.0.0.0",
    port=8080,
    debug=True,
    environment="development",
)

app = Application(config)
```

You can also load configuration from a YAML file:

```python
app = await Application.create("config.yaml")
```

## Defining a Service

A service requires two classes: a manager (business logic) and the service itself.

```python
from processpype.core.service.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.configuration.models import ServiceConfiguration


class DataCollectorManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("Data collector started, beginning collection...")
        # Initialize connections, background tasks, etc.

    async def stop(self) -> None:
        self.logger.info("Data collector stopping...")
        # Clean up resources, cancel background tasks, etc.


class DataCollectorService(Service):
    configuration_class = ServiceConfiguration

    def create_manager(self) -> DataCollectorManager:
        return DataCollectorManager(self.logger)

    def requires_configuration(self) -> bool:
        return False  # can start without explicit configuration
```

## Adding Custom Configuration

Extend `ServiceConfiguration` to add service-specific settings:

```python
from pydantic import Field
from processpype.core.configuration.models import ServiceConfiguration


class DataCollectorConfiguration(ServiceConfiguration):
    interval_seconds: float = Field(default=5.0, description="Collection interval")
    endpoint: str = Field(default="http://localhost:9090", description="Data source URL")


class DataCollectorService(Service):
    configuration_class = DataCollectorConfiguration

    def create_manager(self) -> DataCollectorManager:
        return DataCollectorManager(self.logger)
```

## Registering Services

Initialize the application before registering services:

```python
async def main() -> None:
    config = ApplicationConfiguration(title="My App", port=8080)
    app = Application(config)
    await app.initialize()

    # Register the service — returns a Service instance
    service = app.register_service(DataCollectorService)
    print(f"Registered: {service.name}")  # "datacollector"
```

You can also register a service with a custom name:

```python
service = app.register_service(DataCollectorService, name="primary-collector")
```

## Starting Services

```python
async def main() -> None:
    config = ApplicationConfiguration(title="My App", port=8080)
    app = Application(config)
    await app.initialize()

    service = app.register_service(DataCollectorService)
    await app.start_service(service.name)

    print(f"State: {service.status.state}")  # ServiceState.RUNNING
```

## Configuring Services at Runtime

```python
await app.initialize()
service = app.register_service(DataCollectorService)

# Configure before starting
service.configure({
    "interval_seconds": 10.0,
    "endpoint": "http://prod.example.com:9090",
})

await app.start_service(service.name)
```

Or combine configure and start:

```python
await service.configure_and_start({
    "interval_seconds": 10.0,
    "endpoint": "http://prod.example.com:9090",
})
```

## Running the Application

Use `app.start()` to launch the Uvicorn server. This is the typical production entry point:

```python
import asyncio
from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration


async def main() -> None:
    config = ApplicationConfiguration(
        title="My Application",
        host="0.0.0.0",
        port=8080,
    )
    app = Application(config)
    await app.initialize()
    app.register_service(DataCollectorService)
    await app.start()  # blocks until server stops


asyncio.run(main())
```

The application exposes these endpoints automatically:

- `GET /` --- Application status and version
- `GET /services` --- List all registered services
- `POST /services/register` --- Register a service by name
- `DELETE /services/{name}` --- Deregister a service
- `GET /services/{name}` --- Service status
- `POST /services/{name}/start` --- Start a service
- `POST /services/{name}/stop` --- Stop a service
- `POST /services/{name}/configure` --- Configure a service

## YAML Configuration

Create a `config.yaml` file to configure the application and services:

```yaml
title: My Application
host: 0.0.0.0
port: 8080
debug: false
environment: production

services:
  datacollector:
    enabled: true
    autostart: false
    interval_seconds: 10.0
    endpoint: http://prod.example.com:9090
```

Load it with:

```python
app = await Application.create("config.yaml")
```

## Next Steps

- [Application Guide](../guide/application.md) --- Deep dive into the application lifecycle
- [Services Guide](../guide/services.md) --- Advanced service patterns and the state machine
- [Configuration Guide](../guide/configuration.md) --- Providers, YAML, and environment variables
- [Routing Guide](../guide/routing.md) --- Customizing REST endpoints
