# BaseService API Reference

`processpype.service.base.Service`

## Class

```python
class Service(ABC):
    """Base class for all services.

    A service is composed of three main components:
    1. Service class: Handles lifecycle and configuration
    2. Manager: Handles business logic and state management
    3. Router: Handles HTTP endpoints and API
    """

    configuration_class: type[ServiceConfiguration]
```

Subclasses **must** define `configuration_class` and implement `create_manager()`.

## Constructor

```python
def __init__(self, name: str | None = None) -> None
```

**Parameters:**

- `name` --- Optional service name. Defaults to the class name lowercased with `service` suffix stripped (via `derive_service_name()`).

Initializes status as `ServiceState.INITIALIZED`, calls `create_manager()` and `create_router()`.

## Properties

### `name`

```python
@property
def name(self) -> str
```

The service name used as the registry key and in route prefixes.

---

### `status`

```python
@property
def status(self) -> ServiceStatus
```

Current `ServiceStatus` (state, error, metadata, is_configured).

---

### `config`

```python
@property
def config(self) -> ServiceConfiguration | None
```

The applied configuration, or `None` if not yet configured.

---

### `manager`

```python
@property
def manager(self) -> ServiceManager
```

The service manager instance.

---

### `router`

```python
@property
def router(self) -> ServiceRouter | None
```

The FastAPI router for this service.

---

### `logger`

```python
@property
def logger(self) -> logging.Logger
```

Logger named `processpype.services.{name}`.

## Abstract Methods

### `create_manager`

```python
@abstractmethod
def create_manager(self) -> ServiceManager
```

Create and return the service manager. Called once during `__init__`.

## Methods

### `create_router`

```python
def create_router(self) -> ServiceRouter
```

Create and return the service router. Override to customize endpoints. The default implementation creates a `ServiceRouter` with status, start, stop, configure, and configure-and-start endpoints.

---

### `configure`

```python
def configure(self, config: ServiceConfiguration | dict[str, Any]) -> None
```

Apply configuration to the service. If `config` is a `dict`, it is validated against `configuration_class`. Sets `status.is_configured = True` and `status.state = CONFIGURED`.

If `config.autostart` is `True`, schedules `start()` in the background.

**Raises:** `ConfigurationError` if configuration validation fails.

---

### `requires_configuration`

```python
def requires_configuration(self) -> bool
```

Return `True` (default) if the service must be configured before `start()` is called. Override to return `False` for services that can start without explicit configuration.

---

### `set_error`

```python
def set_error(self, error: str) -> None
```

Set `status.error = error`, `status.state = ERROR`, and log the error.

---

### `start`

```python
async def start(self) -> None
```

Start the service:

1. Validates state (must be `INITIALIZED`, `CONFIGURED`, or `STOPPED`)
2. Checks configuration if `requires_configuration()` is `True`
3. Sets state to `STARTING`
4. Calls `manager.start()`
5. Sets state to `RUNNING` on success, or calls `set_error()` and re-raises on failure

---

### `stop`

```python
async def stop(self) -> None
```

Stop the service:

1. Sets state to `STOPPING`
2. Calls `manager.stop()`
3. Sets state to `STOPPED` on success, or calls `set_error()` on failure

---

### `configure_and_start`

```python
async def configure_and_start(
    self,
    config: ServiceConfiguration | dict[str, Any],
) -> Self
```

Convenience method that calls `configure(config)` then `start()`. Returns `self` for chaining.

## ConfigurationError

```python
class ConfigurationError(Exception):
    """Raised when a service is not properly configured."""
```

Raised by `start()` when `requires_configuration()` is `True` and the service has not been configured.
