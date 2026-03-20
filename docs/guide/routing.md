# Routing

ProcessPype uses FastAPI routers to expose REST APIs for both the application and individual services. All routing is automatically configured when you register services.

## Application Router

`ApplicationRouter` mounts on the root path (`/` by default, or `api_prefix` if set). It provides:

### GET /

Returns the overall application status:

```json
{
  "version": "1.1.6",
  "state": "running",
  "services": {
    "clock": {
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
      "name": "clock",
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
  -d '{"service_name": "clock", "instance_name": "primary-clock"}'
```

Response:

```json
{
  "status": "registered",
  "service": "primary-clock",
  "type": "ClockService"
}
```

### DELETE /services/{service_name}

Deregister and stop a service:

```bash
curl -X DELETE http://localhost:8000/services/primary-clock
```

Response:

```json
{
  "status": "deregistered",
  "service": "primary-clock"
}
```

## Service Router

`ServiceRouter` is automatically created for every service and mounted at `/services/{name}`. It provides:

### GET /services/{name}

Returns the service status:

```bash
curl http://localhost:8000/services/clock
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
curl -X POST http://localhost:8000/services/clock/start
```

```json
{"status": "started", "service": "clock"}
```

### POST /services/{name}/stop

Stop the service:

```bash
curl -X POST http://localhost:8000/services/clock/stop
```

```json
{"status": "stopped", "service": "clock"}
```

### POST /services/{name}/configure

Configure the service with a JSON body:

```bash
curl -X POST http://localhost:8000/services/clock/configure \
  -H "Content-Type: application/json" \
  -d '{"tick_size": 1.0, "enabled": true}'
```

```json
{"status": "configured", "service": "clock"}
```

### POST /services/{name}/configure_and_start

Configure and start in a single call:

```bash
curl -X POST http://localhost:8000/services/clock/configure_and_start \
  -H "Content-Type: application/json" \
  -d '{"tick_size": 1.0}'
```

```json
{"status": "configured and started", "service": "clock"}
```

## Custom Service Routes

Add custom endpoints to a service by overriding `create_router()`:

```python
from fastapi import APIRouter
from processpype.core.service.router import ServiceRouter
from processpype.core.service.service import Service


class MetricsService(Service):
    def create_router(self) -> ServiceRouter:
        router = super().create_router()  # get default routes

        @router.get("/metrics")
        async def get_metrics() -> dict:
            return {"requests": 1234, "errors": 5}

        return router
```

Or create an entirely custom router subclass:

```python
class MetricsRouter(ServiceRouter):
    def __init__(self, name: str, get_status, get_metrics, **kwargs):
        self._get_metrics = get_metrics
        super().__init__(name=name, get_status=get_status, **kwargs)
        self._setup_metrics_routes()

    def _setup_metrics_routes(self) -> None:
        @self.get("/metrics")
        async def get_metrics() -> dict:
            return self._get_metrics()
```

## API Prefix

All routes are mounted under `api_prefix` when it is set:

```python
config = ApplicationConfiguration(api_prefix="/api/v1")
```

With this prefix:
- Application status: `GET /api/v1/`
- Service list: `GET /api/v1/services`
- Clock status: `GET /api/v1/services/clock`

## OpenAPI Documentation

FastAPI's interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

With an `api_prefix` set, the docs URLs also include the prefix.
