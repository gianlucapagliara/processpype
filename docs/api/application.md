# Application API Reference

`processpype.application.Application`

## Class

```python
class Application:
    """Core application with built-in FastAPI integration."""
```

## Constructor

```python
def __init__(self, config: ProcessPypeConfig) -> None
```

Creates an `Application` instance and stores it as the singleton (`Application._instance`). Immediately creates the FastAPI instance.

**Parameters:**

- `config` (`ProcessPypeConfig`) --- Application configuration

## Class Methods

### `create`

```python
@classmethod
async def create(
    cls,
    config_file: str | None = None,
    **kwargs: Any,
) -> "Application"
```

Create an application instance by loading configuration from a YAML file and/or keyword arguments. Uses `load_config()` internally.

**Parameters:**

- `config_file` --- Optional path to a YAML configuration file
- `**kwargs` --- Configuration overrides (merged after the file)

**Returns:** `Application`

---

### `get_instance`

```python
@classmethod
def get_instance(cls) -> Application | None
```

Return the most recently created `Application` instance, or `None` if no instance exists.

## Properties

### `api`

```python
@property
def api(self) -> FastAPI
```

The underlying FastAPI application instance.

---

### `config`

```python
@property
def config(self) -> ProcessPypeConfig
```

The application configuration.

---

### `is_initialized`

```python
@property
def is_initialized(self) -> bool
```

`True` after `initialize()` has completed.

---

### `logger`

```python
@property
def logger(self) -> logging.Logger
```

Logger named `processpype.app`.

## Lifecycle Methods

### `initialize`

```python
async def initialize(self) -> None
```

Initialize the application. Idempotent --- safe to call multiple times.

Sets up:
1. System environment (timezone via `setup_environment()`)
2. Observability (logging + tracing via `init_observability()`)
3. `ApplicationManager` (service registry)
4. `ApplicationRouter` (REST endpoints)

---

### `start`

```python
async def start(self) -> None
```

Start the application: initialize, start enabled services, and run the Uvicorn server. Blocks until the server stops.

---

### `stop`

```python
async def stop(self) -> None
```

Stop all services and set application state to `STOPPED`. Waits up to `closing_timeout_seconds` for services to stop.

---

### `__aenter__` / `__aexit__`

Supports use as an async context manager. Calls `initialize()` on entry and `stop()` on exit.

```python
async with Application(config) as app:
    ...
```

## Service Management Methods

### `register_service`

```python
def register_service(
    self,
    service_class: type[Service],
    name: str | None = None,
) -> Service
```

Instantiate and register a service. Mounts the service router on the FastAPI instance.

**Parameters:**

- `service_class` --- The `Service` subclass to instantiate
- `name` --- Optional name override. Auto-generated from class name if omitted.

**Returns:** The registered `Service` instance

**Raises:**

- `RuntimeError` --- If the application is not initialized
- `ValueError` --- If the service name is already registered

---

### `register_service_by_name`

```python
def register_service_by_name(
    self,
    service_name: str,
    instance_name: str | None = None,
) -> Service | None
```

Look up a service class in the global registry by name and register an instance. Returns `None` if the class is not found.

---

### `deregister_service`

```python
async def deregister_service(self, service_name: str) -> bool
```

Stop and remove a service from the registry. Returns `True` on success.

**Raises:** `ValueError` if the service is not found.

---

### `get_service`

```python
def get_service(self, name: str) -> Service | None
```

Retrieve a registered service by name. Returns `None` if not found.

---

### `get_services_by_type`

```python
def get_services_by_type(self, service_type: type[Service]) -> list[Service]
```

Return all registered services that are instances of `service_type`.

---

### `start_service`

```python
async def start_service(self, service_name: str) -> None
```

Start a registered service by name.

**Raises:** `RuntimeError` if the application is not initialized, `ValueError` if the service is not found.

---

### `stop_service`

```python
async def stop_service(self, service_name: str) -> None
```

Stop a registered service by name.

## ApplicationCreator

`processpype.creator.ApplicationCreator`

A helper class used by `processpype.main` to create and manage the application singleton in a WSGI/ASGI entry-point context.

```python
class ApplicationCreator:
    is_shutting_down: bool
    app: Application | None

    @classmethod
    def get_application(
        cls,
        config: ProcessPypeConfig | None = None,
        application_class: type[Application] = Application,
    ) -> Application: ...
```

`get_application()` creates or returns the singleton `Application` instance, sets up signal handlers for graceful shutdown, and configures the FastAPI lifespan to initialize the app and start enabled services.
