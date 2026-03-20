# Router API Reference

`processpype.core.router` and `processpype.core.service.router`

## ApplicationRouter

`processpype.core.router.ApplicationRouter`

```python
class ApplicationRouter(APIRouter):
```

FastAPI router that provides application-level endpoints. Mounted on the root path (or `api_prefix`) of the FastAPI application.

### Constructor

```python
def __init__(
    self,
    *,
    get_version: Callable[[], str],
    get_state: Callable[[], ServiceState],
    get_services: Callable[[], dict[str, Service]],
) -> None
```

**Parameters:**

- `get_version` --- Callback returning the application version string
- `get_state` --- Callback returning the current `ServiceState`
- `get_services` --- Callback returning the `dict[str, Service]` of all registered services

### Endpoints

| Method | Path | Response model | Description |
|--------|------|----------------|-------------|
| `GET` | `/` | `ApplicationStatus` | Application version, state, and all service statuses |
| `GET` | `/services` | list | Summary of all registered services |
| `POST` | `/services/register` | dict | Register a service by name |
| `DELETE` | `/services/{service_name}` | dict | Deregister a service by name |

### POST /services/register

Accepts `ServiceRegistrationRequest`:

```python
class ServiceRegistrationRequest(BaseModel):
    service_name: str       # registry key (e.g. "clock")
    instance_name: str | None = None  # optional custom name
```

Looks up `service_name` in the global service registry, creates and registers an instance, and returns:

```json
{"status": "registered", "service": "clock", "type": "ClockService"}
```

**HTTP errors:**

- `404` --- Service class not found in registry
- `400` --- Service name already registered
- `500` --- Application instance not available or unexpected error

### DELETE /services/{service_name}

Stops and removes the named service. Returns:

```json
{"status": "deregistered", "service": "clock"}
```

**HTTP errors:**

- `404` --- Service not found

## ServiceRouter

`processpype.core.service.router.ServiceRouter`

```python
class ServiceRouter(APIRouter):
```

FastAPI router mounted at `/services/{name}` for a single service. Created automatically by `Service.create_router()`.

### Constructor

```python
def __init__(
    self,
    name: str,
    get_status: Callable[[], ServiceStatus],
    start_service: Callable[[], Any] | None = None,
    stop_service: Callable[[], Any] | None = None,
    configure_service: Callable[[dict[str, Any]], Any] | None = None,
    configure_and_start_service: Callable[[dict[str, Any]], Any] | None = None,
) -> None
```

**Parameters:**

- `name` --- Service name; sets the router prefix to `/services/{name}`
- `get_status` --- Callback returning `ServiceStatus`
- `start_service` --- Optional callback to start the service
- `stop_service` --- Optional callback to stop the service
- `configure_service` --- Optional callback to configure the service
- `configure_and_start_service` --- Optional callback to configure and start

Endpoints are registered only if their corresponding callback is provided.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/{name}` | Get service status as `ServiceStatus` JSON |
| `POST` | `/services/{name}/start` | Start the service |
| `POST` | `/services/{name}/stop` | Stop the service |
| `POST` | `/services/{name}/configure` | Configure with JSON body |
| `POST` | `/services/{name}/configure_and_start` | Configure and start with JSON body |

All write endpoints return `{"status": "...", "service": "{name}"}` on success and `500` with the error detail on failure.

### Extending ServiceRouter

Override `create_router()` in your service subclass to add custom endpoints:

```python
class MyService(Service):
    def create_router(self) -> ServiceRouter:
        router = super().create_router()

        @router.get("/custom")
        async def custom_endpoint() -> dict:
            return {"custom": "data"}

        return router
```

Or subclass `ServiceRouter` directly:

```python
class MyServiceRouter(ServiceRouter):
    def __init__(self, name: str, get_status, get_data, **kwargs):
        self._get_data = get_data
        super().__init__(name=name, get_status=get_status, **kwargs)
        self._setup_custom_routes()

    def _setup_custom_routes(self) -> None:
        @self.get("/data")
        async def get_data() -> dict:
            return self._get_data()
```
