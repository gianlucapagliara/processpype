# Services

A service in ProcessPype is a self-contained unit of functionality with a well-defined lifecycle, automatic REST endpoints, and structured configuration. Every service is composed of three parts:

1. **Service class** --- Handles lifecycle coordination and configuration
2. **ServiceManager** --- Implements the actual business logic (`start` / `stop`)
3. **ServiceRouter** --- Exposes HTTP endpoints for the service

## Service State Machine

Every service moves through a defined set of states:

```
INITIALIZED
    │
    ▼ (configure)
CONFIGURED
    │
    ▼ (start)
STARTING
    │
    ▼ (success)
RUNNING
    │
    ▼ (stop)
STOPPING
    │
    ▼ (success)
STOPPED

Any state ──► ERROR  (on exception)
```

States are defined in `ServiceState` (a `StrEnum`):

| State | Value | Description |
|-------|-------|-------------|
| `INITIALIZED` | `"initialized"` | Service created, not yet configured |
| `CONFIGURED` | `"configured"` | Configuration applied and validated |
| `STARTING` | `"starting"` | Start in progress |
| `RUNNING` | `"running"` | Actively running |
| `STOPPING` | `"stopping"` | Shutdown in progress |
| `STOPPED` | `"stopped"` | Fully stopped |
| `ERROR` | `"error"` | Error encountered |

## Implementing a Service

### Minimal service

```python
from processpype.core.service.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.configuration.models import ServiceConfiguration


class EchoManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("Echo service ready")

    async def stop(self) -> None:
        self.logger.info("Echo service stopped")


class EchoService(Service):
    configuration_class = ServiceConfiguration

    def create_manager(self) -> EchoManager:
        return EchoManager(self.logger)

    def requires_configuration(self) -> bool:
        return False
```

### Service with custom configuration

```python
from pydantic import Field
from processpype.core.configuration.models import ServiceConfiguration


class EchoConfiguration(ServiceConfiguration):
    prefix: str = Field(default="Echo", description="Message prefix")
    max_length: int = Field(default=1000, description="Maximum message length")


class EchoService(Service):
    configuration_class = EchoConfiguration

    def create_manager(self) -> EchoManager:
        return EchoManager(self.logger)
```

### Accessing configuration in the manager

Pass configuration to the manager during `configure()`, or access it via `service.config`:

```python
class EchoManager(ServiceManager):
    def __init__(self, logger, config: EchoConfiguration):
        super().__init__(logger)
        self._config = config

    async def start(self) -> None:
        self.logger.info(f"Echo service ready with prefix: {self._config.prefix}")

    async def stop(self) -> None:
        pass
```

## ServiceManager

`ServiceManager` is the abstract base class for all service business logic. Subclasses must implement:

```python
@abstractmethod
async def start(self) -> None: ...

@abstractmethod
async def stop(self) -> None: ...
```

The `logger` property provides a pre-configured logger named after the service.

## ServiceStatus

Every service exposes a `ServiceStatus` model:

```python
class ServiceStatus(BaseModel):
    state: ServiceState          # current lifecycle state
    error: str | None            # error message if state is ERROR
    metadata: dict[str, Any]     # service-specific metadata
    is_configured: bool          # whether configure() was called
```

Access it via:

```python
print(service.status.state)
print(service.status.is_configured)
print(service.status.error)
```

## Configuration and Autostart

`ServiceConfiguration` base fields:

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `True` | Whether the service participates in `start_enabled_services()` |
| `autostart` | `False` | If `True`, `configure()` will schedule `start()` automatically |

When `autostart=True`, calling `configure()` immediately schedules an async `start()`:

```python
service.configure({"autostart": True, "prefix": "Hello"})
# start() is scheduled in the background
```

## Requires Configuration

Override `requires_configuration()` to control whether the service can start without being configured:

```python
def requires_configuration(self) -> bool:
    return False  # allow starting without configure()
```

When `True` (the default), calling `start()` on an unconfigured service raises `ConfigurationError`.

## Error Handling

```python
class RobustManager(ServiceManager):
    async def start(self) -> None:
        try:
            # ... initialize resources ...
            pass
        except Exception as e:
            raise RuntimeError(f"Failed to initialize: {e}") from e

    async def stop(self) -> None:
        # ... clean up ...
        pass
```

The `Service.start()` base method catches exceptions from `manager.start()`, calls `service.set_error(message)`, and re-raises. `set_error()` sets `status.state = ERROR` and logs the error.

## Registering Services Globally

Decorate a service class with `@register_service_class` to add it to the global registry, making it available via `app.register_service_by_name()` and `POST /services/register`:

```python
from processpype.services import register_service_class


@register_service_class
class EchoService(Service):
    ...
```

The registry key is the class name lowercased with the `service` suffix stripped (e.g., `EchoService` → `"echo"`).

## Lifecycle Hooks

The `Service` base class calls `manager.start()` and `manager.stop()`. Override `start()` or `stop()` in the service subclass to add custom logic:

```python
class EchoService(Service):
    async def start(self) -> None:
        # Custom pre-start logic
        await super().start()
        # Custom post-start logic

    async def stop(self) -> None:
        # Custom pre-stop logic
        await super().stop()
        # Custom post-stop logic
```
