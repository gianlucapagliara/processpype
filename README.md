# Processpype

Processpype is a framework for building and managing an application that is composed of services.

## Architecture Overview

The core module provides the fundamental building blocks for creating and managing services in the ProcessPype framework.

### Core Components

#### 1. Application (`application.py`)
The central orchestrator that manages the lifecycle of the application and its services.

```python
from processpype.core import Application

app = await Application.create("config.yaml")
await app.start()
```

Key features:
- Async context manager support
- FastAPI integration
- Service lifecycle management
- Configuration management

#### 2. Application Manager (`manager.py`)
Handles service registration, state management, and lifecycle operations.

Key responsibilities:
- Service registration and retrieval
- Service state management
- Service startup/shutdown orchestration

#### 3. Router (`router.py`)
Provides REST API endpoints for application and service management.

Available endpoints:
- `GET /` - Application status
- `GET /services` - List registered services
- `POST /services/{service_name}/start` - Start a service
- `POST /services/{service_name}/stop` - Stop a service

#### 4. Models (`models.py`)
Core data models and enums for the application.

```python
from processpype.core.models import ServiceState

# Available states
ServiceState.STOPPED
ServiceState.STARTING
ServiceState.RUNNING
ServiceState.STOPPING
ServiceState.ERROR
```

#### 5. Configuration (`config/`)
Handles application and service configuration management using Pydantic models.

## Implementing New Services

### 1. Basic Service Structure

```python
from processpype.core.service import Service
from processpype.core.models import ServiceState

class MyService(Service):
    def __init__(self, name: str | None = None):
        super().__init__(name or "my_service")

    async def start(self) -> None:
        self.set_state(ServiceState.STARTING)
        # Initialize your service
        self.set_state(ServiceState.RUNNING)

    async def stop(self) -> None:
        self.set_state(ServiceState.STOPPING)
        # Cleanup resources
        self.set_state(ServiceState.STOPPED)
```

### 2. Adding Configuration

```python
from pydantic import BaseModel
from processpype.core.config.models import ServiceConfiguration

class MyServiceConfig(ServiceConfiguration):
    custom_field: str
    port: int = 8080

class MyService(Service):
    def configure(self, config: MyServiceConfig) -> None:
        self._config = config
        # Apply configuration
```

### 3. Adding API Routes

```python
from fastapi import APIRouter

class MyService(Service):
    def __init__(self, name: str | None = None):
        super().__init__(name or "my_service")
        self._router = APIRouter(prefix=f"/services/{self.name}")
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self._router.get("/status")
        async def get_status():
            return {"state": self.state}
```

### 4. Error Handling

```python
from processpype.core.models import ServiceState

class MyService(Service):
    async def start(self) -> None:
        try:
            self.set_state(ServiceState.STARTING)
            # Initialize
            self.set_state(ServiceState.RUNNING)
        except Exception as e:
            self.set_error(str(e))
            self.set_state(ServiceState.ERROR)
            raise
```

## Service Lifecycle

1. **Registration**
```python
app = await Application.create("config.yaml")
service = app.register_service(MyService)
```

2. **Configuration**
```yaml
# config.yaml
services:
  my_service:
    enabled: true
    custom_field: "value"
    port: 8080
```

3. **Startup**
- Service state transitions: STOPPED → STARTING → RUNNING
- Configuration is applied
- Resources are initialized
- API routes are registered

4. **Runtime**
- Service handles requests
- Maintains state
- Reports health status

5. **Shutdown**
- Service state transitions: RUNNING → STOPPING → STOPPED
- Resources are cleaned up
- API routes are unregistered

## Best Practices

1. **State Management**
- Always use `set_state()` for state transitions
- Handle errors appropriately with `set_error()`
- Check state before operations

2. **Configuration**
- Use Pydantic models for configuration
- Provide sensible defaults
- Validate configuration in `configure()`

3. **Resource Management**
- Initialize resources in `start()`
- Clean up resources in `stop()`
- Use async context managers when possible

4. **Error Handling**
- Catch and handle exceptions appropriately
- Set service state to ERROR on failures
- Provide meaningful error messages

5. **API Design**
- Use FastAPI best practices
- Prefix routes with service name
- Provide OpenAPI documentation

## Logging

The framework uses structured logging via `logfire.py`:

```python
from processpype.core.logfire import get_service_logger

class MyService(Service):
    def __init__(self, name: str | None = None):
        super().__init__(name or "my_service")
        self.logger = get_service_logger(self.name)

    async def start(self) -> None:
        self.logger.info("Starting service", extra={"config": self.config.model_dump()})
```

## Testing Services

1. **Unit Tests**
```python
async def test_my_service():
    service = MyService()
    await service.start()
    assert service.state == ServiceState.RUNNING
    await service.stop()
    assert service.state == ServiceState.STOPPED
```

2. **Integration Tests**
```python
from fastapi.testclient import TestClient

async def test_my_service_api():
    app = await Application.create()
    service = app.register_service(MyService)
    client = TestClient(app.api)

    response = client.get("/services/my_service/status")
    assert response.status_code == 200
```
