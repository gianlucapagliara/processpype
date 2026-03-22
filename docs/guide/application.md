# Application

The `Application` class is the central orchestrator of a ProcessPype application. It manages the FastAPI server, service registry, configuration, and the overall application lifecycle.

## Creating an Application

### Direct instantiation

```python
from processpype import Application, ProcessPypeConfig

config = ProcessPypeConfig(
    app={"title": "My Application", "version": "1.0.0", "environment": "production"},
    server={"host": "0.0.0.0", "port": 8080},
)
app = Application(config)
```

### From a YAML file

```python
app = await Application.create("config.yaml")
```

`Application.create()` uses the `load_config()` function to load configuration from a YAML file, with support for `${ENV_VAR}` token replacement and optional keyword overrides.

### Singleton access

`Application` stores its most recent instance as a class variable, accessible via:

```python
app = Application.get_instance()
```

This is used internally by `ApplicationRouter` to resolve service operations from HTTP requests.

## Initialization

Call `initialize()` before registering services or starting the server. This method:

1. Sets up the environment (timezone, project directory, run ID)
2. Initializes observability (logging formatters/filters and OpenTelemetry tracing)
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
service = app.register_service_by_name("counter")
service = app.register_service_by_name("counter", instance_name="primary-counter")
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
from processpype.examples import CounterService
counters = app.get_services_by_type(CounterService)
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

The API prefix can be set via `ProcessPypeConfig.server.api_prefix`. All application and service routes are mounted under this prefix.

## Configuration Reference

`ProcessPypeConfig` is the root configuration model. It contains the following sub-models:

### `AppConfig` (`config.app`)

| Field | Default | Description |
|-------|---------|-------------|
| `title` | `"ProcessPype"` | API title shown in OpenAPI docs |
| `version` | `"0.1.0"` | API version |
| `environment` | `"development"` | Environment name |
| `debug` | `False` | Debug mode (verbose logging) |
| `timezone` | `"UTC"` | Application timezone |

### `ServerConfig` (`config.server`)

| Field | Default | Description |
|-------|---------|-------------|
| `host` | `"0.0.0.0"` | Uvicorn bind host |
| `port` | `8000` | Uvicorn bind port |
| `api_prefix` | `""` | URL prefix for all routes (e.g. `"/api/v1"`) |
| `closing_timeout_seconds` | `60` | Max seconds to wait for services to stop |

### `ObservabilityConfig` (`config.observability`)

See the [Configuration](configuration.md) guide for full details on `logging` and `tracing` sub-models.

### `services` (`config.services`)

A dictionary mapping service names to `ServiceConfiguration` instances. See the [Services](services.md) guide for details.
