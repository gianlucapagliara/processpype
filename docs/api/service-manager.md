# ServiceManager API Reference

`processpype.core.service.manager.ServiceManager`

## Class

```python
class ServiceManager(ABC):
    """Base class for service managers.

    A service manager is responsible for handling the business logic
    and state management for a service.
    """
```

`ServiceManager` is an abstract base class. All service managers must implement `start()` and `stop()`.

## Constructor

```python
def __init__(self, logger: logging.Logger) -> None
```

**Parameters:**

- `logger` --- Logger instance configured for the parent service

## Properties

### `logger`

```python
@property
def logger(self) -> logging.Logger
```

The logger passed during construction.

## Abstract Methods

### `start`

```python
@abstractmethod
async def start(self) -> None
```

Start the service manager. Implement service-specific initialization here: open connections, start background tasks, acquire resources.

**Raises:** Any exception on failure. The calling `Service.start()` will catch the exception, set the error state, and re-raise.

---

### `stop`

```python
@abstractmethod
async def stop(self) -> None
```

Stop the service manager. Implement service-specific shutdown here: close connections, cancel background tasks, release resources.

## ApplicationManager

`processpype.core.manager.ApplicationManager`

The application-level manager that owns the service registry and delegates lifecycle operations.

```python
class ApplicationManager:
    def __init__(
        self,
        logger: logging.Logger,
        config: ApplicationConfiguration,
    ) -> None
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `state` | `ServiceState` | Current application state |
| `services` | `dict[str, Service]` | All registered services |

### Methods

| Method | Description |
|--------|-------------|
| `register_service(service_class, name)` | Instantiate, configure, and register a service |
| `get_service(name)` | Return a service by name, or `None` |
| `get_services_by_type(service_type)` | Return all services of a given type |
| `set_state(state)` | Update application state and log the transition |
| `start_service(service_name)` | Delegate to `service.start()` |
| `stop_service(service_name)` | Delegate to `service.stop()` |
| `configure_service(service_name, config)` | Delegate to `service.configure()` |
| `configure_and_start_service(service_name, config)` | Delegate to `service.configure_and_start()` |
| `start_enabled_services()` | Start all configured and enabled services |
| `stop_all_services()` | Stop all running services |

### `register_service`

```python
def register_service(
    self,
    service_class: type[Service],
    name: str | None = None,
) -> Service
```

Creates the service instance, applies any configuration from `ApplicationConfiguration.services`, and adds it to the registry.

Name auto-generation: strips `service` suffix from the class name (case-insensitive) and appends `_N` for duplicates.

**Raises:** `ValueError` if the name is already registered.

### `start_enabled_services`

```python
async def start_enabled_services(self) -> None
```

Iterates all registered services. Skips services where `config.enabled == False`. Starts services that are either configured or do not require configuration. Errors are caught, logged, and `set_error()` is called — other services continue starting.

### `stop_all_services`

```python
async def stop_all_services(self) -> None
```

Calls `stop()` on every service in `RUNNING` or `STARTING` state. Errors are caught and logged.
