# Models API Reference

`processpype.service.models`

## ServiceState

```python
class ServiceState(StrEnum):
```

A `StrEnum` representing every state a service or application can be in.

| Member | Value | Description |
|--------|-------|-------------|
| `INITIALIZED` | `"initialized"` | Created, not yet configured |
| `CONFIGURED` | `"configured"` | Configuration applied and validated |
| `STARTING` | `"starting"` | Start in progress |
| `RUNNING` | `"running"` | Actively running |
| `STOPPING` | `"stopping"` | Shutdown in progress |
| `STOPPED` | `"stopped"` | Fully stopped |
| `ERROR` | `"error"` | Error encountered |

Because `ServiceState` is a `StrEnum`, its values can be compared with plain strings:

```python
from processpype.service.models import ServiceState

assert ServiceState.RUNNING == "running"
state = ServiceState.RUNNING
print(state)  # "running"
```

## ServiceStatus

```python
class ServiceStatus(BaseModel):
```

Tracks the current state and metadata of a service instance. Returned by `service.status` and all status API endpoints.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `state` | `ServiceState` | (required) | Current lifecycle state |
| `error` | `str \| None` | `None` | Error message if state is `ERROR` |
| `metadata` | `dict[str, Any]` | `{}` | Service-specific status information |
| `is_configured` | `bool` | `False` | Whether `configure()` was successfully called |

### Example

```python
from processpype.service.models import ServiceStatus, ServiceState

status = ServiceStatus(state=ServiceState.RUNNING)
print(status.state)         # ServiceState.RUNNING
print(status.is_configured) # False
print(status.error)         # None

# JSON serialization
data = status.model_dump(mode="json")
# {"state": "running", "error": null, "metadata": {}, "is_configured": false}
```

## ApplicationStatus

```python
class ApplicationStatus(BaseModel):
```

The response model for the `GET /` application status endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | Application version string |
| `state` | `ServiceState` | Current state of the application |
| `services` | `dict[str, ServiceStatus]` | Map of service name to its status |

### Example

```python
from processpype.service.models import ApplicationStatus, ServiceState, ServiceStatus

app_status = ApplicationStatus(
    version="2.0.0",
    state=ServiceState.RUNNING,
    services={
        "counter": ServiceStatus(state=ServiceState.RUNNING, is_configured=True),
    },
)
data = app_status.model_dump(mode="json")
```

Response JSON from `GET /`:

```json
{
  "version": "2.0.0",
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

## ServiceRegistrationRequest

`processpype.server.app_router.ServiceRegistrationRequest`

Request body for `POST /services/register`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `service_name` | `str` | (required) | Registry key for the service class |
| `instance_name` | `str \| None` | `None` | Optional custom instance name |
