# Clock Service

The `ClockService` integrates the [chronopype](https://github.com/gianlucapagliara/chronopype) clock framework into ProcessPype, providing managed clock instances with REST API control.

## Installation

The clock service is included in the core package — no extra dependencies are required.

## Usage

```python
from processpype.services.clock.service import ClockService

service = app.register_service(ClockService)
await app.start_service(service.name)
```

Or register by name (requires `@register_service_class` — already applied):

```python
app.register_service_by_name("clock")
```

## Configuration

```python
from processpype.services.clock.config import ClockConfiguration
from chronopype import ClockMode

config = ClockConfiguration(
    enabled=True,
    autostart=False,
)
service.configure(config)
```

The `ClockConfiguration` extends `ServiceConfiguration` and wraps the chronopype `ClockConfig`.

## YAML Configuration

```yaml
services:
  clock:
    enabled: true
    autostart: false
```

## REST Endpoints

In addition to the standard service endpoints, the clock service exposes:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/clock` | Service and clock status |
| `GET` | `/services/clock/status` | Detailed clock status |
| `POST` | `/services/clock/start` | Start the clock service |
| `POST` | `/services/clock/stop` | Stop the clock service |
| `POST` | `/services/clock/configure` | Configure the clock |
| `POST` | `/services/clock/configure_and_start` | Configure and start |

The clock status response includes:

```json
{
  "configured": true,
  "running": true
}
```

## Service States

The clock service maps its internal state to `ServiceState` dynamically:

- Not configured → `INITIALIZED`
- Configured, not running → `CONFIGURED`
- Running → `RUNNING`

## No Configuration Required

`ClockService.requires_configuration()` returns `False`, meaning the service can be started without explicit configuration. It will use chronopype defaults.

## Notes

- `ClockService` is decorated with `@register_service_class`, making it available via `app.register_service_by_name("clock")`
- The service name defaults to `"clock"` (class name with `Service` suffix stripped)
