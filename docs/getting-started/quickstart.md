# Quick Start

This guide walks through the basics of ProcessPype: creating an application, registering a service, and running it. ProcessPype ships with three example services that demonstrate common patterns.

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

## Using the Example Services

ProcessPype includes three example services in `processpype.examples` that serve as templates for building your own.

### HelloService --- Minimal Service

The simplest possible service. No configuration needed.

```python
import asyncio
from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.examples import HelloService


async def main() -> None:
    config = ApplicationConfiguration(title="My App", port=8080)
    app = Application(config)
    await app.initialize()

    service = app.register_service(HelloService)
    await app.start_service(service.name)
    print(f"State: {service.status.state}")  # ServiceState.RUNNING


asyncio.run(main())
```

### CounterService --- Configuration and Custom Routes

Demonstrates custom `ServiceConfiguration` with validation, and a custom `ServiceRouter` with domain-specific endpoints.

```python
from processpype.examples import CounterService

service = app.register_service(CounterService)
service.configure({"initial_value": 10, "step": 5})
await app.start_service(service.name)

# The counter exposes custom HTTP endpoints:
# GET  /services/counter/value
# POST /services/counter/increment
# POST /services/counter/reset
```

### TickerService --- Background Async Loop

Demonstrates a service that runs a periodic background task with graceful shutdown.

```python
from processpype.examples import TickerService

service = app.register_service(TickerService)
service.configure({"interval_seconds": 2.0})
await app.start_service(service.name)
# The ticker logs "Tick #N" every 2 seconds
```

## Building Your Own Service

A service requires two classes: a manager (business logic) and the service itself.

```python
from processpype.core.service.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.configuration.models import ServiceConfiguration


class MyManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("Service started")

    async def stop(self) -> None:
        self.logger.info("Service stopped")


class MyService(Service):
    configuration_class = ServiceConfiguration

    def create_manager(self) -> MyManager:
        return MyManager(self.logger)

    def requires_configuration(self) -> bool:
        return False
```

Use the example services as templates: `HelloService` for the simplest case, `CounterService` for configuration and custom routes, and `TickerService` for background tasks.

## Configuring Services at Runtime

```python
service = app.register_service(TickerService)

# Configure before starting
service.configure({"interval_seconds": 5.0})
await app.start_service(service.name)
```

Or combine configure and start:

```python
await service.configure_and_start({"interval_seconds": 5.0})
```

## Running the Application

Use `app.start()` to launch the Uvicorn server:

```python
import asyncio
from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.examples import CounterService, TickerService


async def main() -> None:
    config = ApplicationConfiguration(
        title="My Application",
        host="0.0.0.0",
        port=8080,
    )
    app = Application(config)
    await app.initialize()
    app.register_service(CounterService)
    app.register_service(TickerService)
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
  counter:
    enabled: true
    autostart: false
    initial_value: 0
    step: 1
  ticker:
    enabled: true
    autostart: true
    interval_seconds: 2.0
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
