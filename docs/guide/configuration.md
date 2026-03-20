# Configuration

ProcessPype uses Pydantic models for all configuration. Configuration can be supplied via YAML files, environment variables, or directly in Python code, with later sources overriding earlier ones.

## Configuration Models

### ConfigurationModel

The base for all configuration models. It allows extra fields and is frozen (immutable after creation):

```python
from processpype.core.configuration.models import ConfigurationModel

class MyConfig(ConfigurationModel):
    name: str = "default"
```

### ServiceConfiguration

Base configuration for all services:

```python
from processpype.core.configuration.models import ServiceConfiguration

class MyServiceConfig(ServiceConfiguration):
    # Inherited fields:
    # enabled: bool = True
    # autostart: bool = False

    host: str = "localhost"
    port: int = 9090
```

### ApplicationConfiguration

Top-level application configuration:

```python
from processpype.core.configuration.models import ApplicationConfiguration

config = ApplicationConfiguration(
    title="My App",
    version="1.0.0",
    host="0.0.0.0",
    port=8080,
    debug=False,
    environment="production",
    logfire_key="your-logfire-key",
    api_prefix="/api/v1",
    closing_timeout_seconds=30,
    services={
        "myservice": {"enabled": True, "host": "localhost", "port": 9090},
    },
)
```

## YAML Configuration

Create a `config.yaml` file to configure the application:

```yaml
title: My Application
version: 1.0.0
host: 0.0.0.0
port: 8080
debug: false
environment: production
api_prefix: ""
closing_timeout_seconds: 60

services:
  clock:
    enabled: true
    autostart: false

  storage:
    enabled: true
    autostart: true
    backend: local
    base_path: /data/storage

  database:
    enabled: true
    autostart: true
    engine: sqlite
    url: sqlite+aiosqlite:///./app.db
```

Load the configuration:

```python
app = await Application.create("config.yaml")
```

## Configuration Providers

`ConfigurationManager` chains multiple providers. Providers are loaded in reverse order of registration, so the last-added provider has the lowest priority (earlier providers win):

### FileProvider

Reads a YAML file:

```python
from processpype.core.configuration.providers import FileProvider

provider = FileProvider("config.yaml")
config_dict = await provider.load()
```

### EnvProvider

Reads environment variables with the `PROCESSPYPE_` prefix. Double underscores (`__`) map to nested keys:

```bash
# Sets config["host"]
export PROCESSPYPE_HOST=0.0.0.0

# Sets config["services"]["clock"]["enabled"]
export PROCESSPYPE_SERVICES__CLOCK__ENABLED=true
```

```python
from processpype.core.configuration.providers import EnvProvider

provider = EnvProvider(prefix="PROCESSPYPE_")
config_dict = await provider.load()
```

### Custom providers

Implement `ConfigurationProvider` to add new sources:

```python
from processpype.core.configuration.providers import ConfigurationProvider
from typing import Any


class VaultProvider(ConfigurationProvider):
    async def load(self) -> dict[str, Any]:
        # Fetch secrets from HashiCorp Vault
        return {"logfire_key": "secret-from-vault"}

    async def save(self, config: dict[str, Any]) -> None:
        pass  # read-only
```

## ConfigurationManager

`ConfigurationManager` orchestrates provider loading:

```python
from processpype.core.configuration.manager import ConfigurationManager
from processpype.core.configuration.providers import FileProvider, EnvProvider
from processpype.core.configuration.models import ApplicationConfiguration

manager = ConfigurationManager()
await manager.add_provider(FileProvider("config.yaml"))
await manager.add_provider(EnvProvider())
await manager.initialize()

config = manager.get_model(ApplicationConfiguration)
```

The `load_application_config` class method covers the common case:

```python
config = await ConfigurationManager.load_application_config(
    config_file="config.yaml",
    title="Override Title",  # kwargs override file values
)
```

## Logfire Configuration

Logfire integration is enabled when `logfire_key` is set in `ApplicationConfiguration`. Optionally configure via the `logfire` field:

```yaml
logfire_key: your-api-token
environment: production
logfire:
  key: your-api-token
  environment: production
  app_name: MyApplication
  enabled: true
  enable_logs: true
```

## Environment Variables for ApplicationCreator

When using `processpype.main` (the default entry point), these environment variables are read directly:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_TITLE` | `"Trading Application"` | Application title |
| `APP_HOST` | `"0.0.0.0"` | Bind host |
| `APP_PORT` | `"8000"` | Bind port |
| `APP_DEBUG` | `"false"` | Debug mode |
| `APP_ENV` | `"production"` | Environment name |
| `LOGFIRE_KEY` | (none) | Logfire API token |
| `API_PREFIX` | `""` | URL prefix |
| `ENABLED_SERVICES` | `""` | Comma-separated list of services to start |
