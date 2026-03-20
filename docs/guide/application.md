# Application

The `Application` class is the central orchestrator of a ProcessPype application. It manages the FastAPI server, service registry, configuration, and the overall application lifecycle.

## Creating an Application

### Direct instantiation

```python
from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration

config = ApplicationConfiguration(
    title="My Application",
    version="1.0.0",
    host="0.0.0.0",
    port=8080,
    debug=False,
    environment="production",
)
app = Application(config)
```

### From a YAML file

```python
app = await Application.create("config.yaml")
```

`Application.create()` uses the `ConfigurationManager` to load from a YAML file and merge environment variable overrides (prefixed with `PROCESSPYPE_`).

### Singleton access

`Application` stores its most recent instance as a class variable, accessible via:

```python
app = Application.get_instance()
```

This is used internally by `ApplicationRouter` to resolve service operations from HTTP requests.

## Initialization

Call `initialize()` before registering services or starting the server. This method:

1. Sets up the system timezone (UTC by default)
2. Configures Logfire if `logfire_key` is present in the configuration
3. Creates the `ApplicationManager` (service registry)
4. Mounts the `ApplicationRouter` onto the FastAPI instance

```python
await app.initialize()
```

`initialize()` is idempotent — subsequent calls return immediately. It is also called automatically by `start()` and `__aenter__`.

## Lifecycle

### Async context manager

```python
async with Application(config) as app:
    await app.initialize()
    app.register_service(MyService)
    await app.start_service("myservice")
    # app.stop() is called automatically on exit
```

### Manual lifecycle

```python
app = Application(config)
await app.initialize()
app.register_service(MyService)
await app.start()       # starts Uvicorn, blocks until server stops
await app.stop()        # stops all services and the application
```

### Startup and shutdown

`app.start()` performs these steps in order:

1. Calls `initialize()` if not already done
2. Sets application state to `STARTING`
3. Calls `start_enabled_services()` to start services that are configured and enabled
4. Starts the Uvicorn server (blocks until the server exits)
5. Calls `stop()` in a `finally` block

`app.stop()` performs these steps:

1. Sets application state to `STOPPING`
2. Calls `stop_all_services()` on the manager
3. Waits for all services to reach `STOPPED` state (up to `closing_timeout_seconds`)
4. Sets application state to `STOPPED`

## Service Management

### Registering services

```python
service = app.register_service(MyService)
service = app.register_service(MyService, name="custom-name")
```

If no name is provided, the name is derived from the class name by stripping the `Service` suffix and lowercasing. Duplicate names raise `ValueError`.

After registration, the service's router is mounted on the FastAPI instance automatically.

### Registering by name

Services can also be registered by their string name if they are in the global service registry (decorated with `@register_service_class`):

```python
service = app.register_service_by_name("clock")
service = app.register_service_by_name("clock", instance_name="primary-clock")
```

This is used by the `POST /services/register` HTTP endpoint.

### Starting and stopping individual services

```python
await app.start_service("myservice")
await app.stop_service("myservice")
```

### Retrieving services

```python
service = app.get_service("myservice")

# Get all services of a type
from processpype.services.clock.service import ClockService
clocks = app.get_services_by_type(ClockService)
```

### Deregistering services

```python
success = await app.deregister_service("myservice")
```

This stops the service if running and removes it from the registry. Note that FastAPI does not support removing routes after they are registered, so the routes remain but the service becomes unavailable.

## FastAPI Integration

The underlying `FastAPI` instance is accessible via:

```python
fastapi_app = app.api
```

This allows full access to FastAPI features — middleware, background tasks, dependency injection, and the interactive docs at `/docs` and `/redoc`.

The API prefix can be set via `ApplicationConfiguration.api_prefix`. All application and service routes are mounted under this prefix.

## Configuration Reference

`ApplicationConfiguration` fields:

| Field | Default | Description |
|-------|---------|-------------|
| `title` | `"ProcessPype"` | API title shown in OpenAPI docs |
| `version` | `"0.1.0"` | API version |
| `host` | `"0.0.0.0"` | Uvicorn bind host |
| `port` | `8000` | Uvicorn bind port |
| `debug` | `False` | Debug mode (verbose logging) |
| `environment` | `"development"` | Environment name for Logfire |
| `logfire_key` | `None` | Logfire API token; enables Logfire if set |
| `api_prefix` | `""` | URL prefix for all routes (e.g. `"/api/v1"`) |
| `closing_timeout_seconds` | `60` | Max seconds to wait for services to stop |
| `services` | `{}` | Per-service configuration dictionary |
