# Routing

ProcessPype uses FastAPI routers to expose REST APIs for both the application and individual services. All routing is automatically configured when you register services.

## Application Router

`ApplicationRouter` mounts on the root path (`/` by default, or `api_prefix` if set). It provides:

### GET /

Returns the overall application status:

```json
{
  "version": "1.2.1",
  "state": "running",
  "services": {
    "counter": {
      "state": "running",
      "error": null,
      "metadata": {},
      "is_configured": true
    }
  }
}
```

### GET /services

Returns a list of all registered services:

```json
{
  "services": [
    {
      "name": "counter",
      "state": "running",
      "is_configured": true,
      "error": null
    }
  ]
}
```

### POST /services/register

Register a service by its class name. The service must be in the global registry (decorated with `@register_service_class`):

```bash
curl -X POST http://localhost:8000/services/register \
  -H "Content-Type: application/json" \
  -d '{"service_name": "counter", "instance_name": "primary-counter"}'
```

Response:

```json
{
  "status": "registered",
  "service": "primary-counter",
  "type": "CounterService"
}
```

### DELETE /services/{service_name}

Deregister and stop a service:

```bash
curl -X DELETE http://localhost:8000/services/primary-counter
```

Response:

```json
{
  "status": "deregistered",
  "service": "primary-counter"
}
```

## Service Router

`ServiceRouter` is automatically created for every service and mounted at `/services/{name}`. It provides:

### GET /services/{name}

Returns the service status:

```bash
curl http://localhost:8000/services/counter
```

```json
{
  "state": "running",
  "error": null,
  "metadata": {},
  "is_configured": true
}
```

### POST /services/{name}/start

Start the service:

```bash
curl -X POST http://localhost:8000/services/counter/start
```

```json
{"status": "started", "service": "counter"}
```

### POST /services/{name}/stop

Stop the service:

```bash
curl -X POST http://localhost:8000/services/counter/stop
```

```json
{"status": "stopped", "service": "counter"}
```

### POST /services/{name}/configure

Configure the service with a JSON body:

```bash
curl -X POST http://localhost:8000/services/counter/configure \
  -H "Content-Type: application/json" \
  -d '{"initial_value": 10, "step": 5}'
```

```json
{"status": "configured", "service": "counter"}
```

### POST /services/{name}/configure_and_start

Configure and start in a single call:

```bash
curl -X POST http://localhost:8000/services/ticker/configure_and_start \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 2.0}'
```

```json
{"status": "configured and started", "service": "ticker"}
```

## Custom Service Routes

Add custom endpoints to a service by overriding `create_router()`. The `CounterService` example demonstrates this pattern with its `CounterRouter`:

```python
from processpype.core.service.router import ServiceRouter
from processpype.core.service.service import Service


class MyService(Service):
    def create_router(self) -> ServiceRouter:
        router = super().create_router()  # get default routes

        @router.get("/metrics")
        async def get_metrics() -> dict:
            return {"requests": 1234, "errors": 5}

        return router
```

Or create an entirely custom router subclass (as `CounterRouter` does):

```python
class MyRouter(ServiceRouter):
    def __init__(self, name: str, get_status, get_data, **kwargs):
        self._get_data = get_data
        super().__init__(name=name, get_status=get_status, **kwargs)
        self._setup_custom_routes()

    def _setup_custom_routes(self) -> None:
        @self.get("/data")
        async def get_data() -> dict:
            return self._get_data()
```

See `processpype/examples/counter.py` for a complete working example of a custom router.

## API Prefix

All routes are mounted under `api_prefix` when it is set:

```python
config = ApplicationConfiguration(api_prefix="/api/v1")
```

With this prefix:
- Application status: `GET /api/v1/`
- Service list: `GET /api/v1/services`
- Counter status: `GET /api/v1/services/counter`

## OpenAPI Documentation

FastAPI's interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

With an `api_prefix` set, the docs URLs also include the prefix.
