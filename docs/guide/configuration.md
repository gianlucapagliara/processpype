# Configuration

ProcessPype uses Pydantic models for all configuration. Configuration can be supplied via a YAML file, environment variable tokens within YAML, or directly in Python code.

## Configuration Models

### ConfigurationModel

The base for all configuration models. It allows extra fields and is frozen (immutable after creation):

```python
from processpype.config.models import ConfigurationModel

class MyConfig(ConfigurationModel):
    name: str = "default"
```

### ServiceConfiguration

Base configuration for all services:

```python
from processpype.config.models import ServiceConfiguration

class MyServiceConfig(ServiceConfiguration):
    # Inherited fields:
    # enabled: bool = True
    # autostart: bool = False

    host: str = "localhost"
    port: int = 9090
```

### ProcessPypeConfig

Top-level application configuration, organized into sub-models that mirror the YAML structure:

```python
from processpype import ProcessPypeConfig

config = ProcessPypeConfig(
    app={
        "title": "My App",
        "version": "1.0.0",
        "environment": "production",
        "debug": False,
        "timezone": "UTC",
    },
    server={
        "host": "0.0.0.0",
        "port": 8080,
        "api_prefix": "/api/v1",
        "closing_timeout_seconds": 30,
    },
    observability={
        "logging": {
            "level": "INFO",
            "format": "json",
        },
        "tracing": {
            "enabled": True,
            "backend": "logfire",
            "logfire": {"token": "your-logfire-token"},
        },
    },
    services={
        "counter": {"enabled": True, "initial_value": 0, "step": 1},
        "ticker": {"enabled": True, "interval_seconds": 2.0},
    },
)
```

#### Sub-models

| Model | Config key | Fields |
|-------|-----------|--------|
| `AppConfig` | `app` | `title`, `version`, `environment`, `debug`, `timezone` |
| `ServerConfig` | `server` | `host`, `port`, `api_prefix`, `closing_timeout_seconds` |
| `ObservabilityConfig` | `observability` | `logging` (LoggingConfig), `tracing` (TracingConfig) |
| `LoggingConfig` | `observability.logging` | `enabled`, `level`, `format`, `loggers`, `custom_levels`, `handlers`, `redaction`, `context` |
| `TracingConfig` | `observability.tracing` | `enabled`, `backend`, `service_name`, `endpoint`, `logfire` (LogfireConfig), `sampling_rate` |
| `LogfireConfig` | `observability.tracing.logfire` | `token`, `environment` |

## YAML Configuration

Create a `config.yaml` file to configure the application:

```yaml
app:
  title: My Application
  version: 1.0.0
  environment: production
  debug: false
  timezone: UTC

server:
  host: 0.0.0.0
  port: 8080
  api_prefix: ""
  closing_timeout_seconds: 60

observability:
  logging:
    level: INFO
    format: json
    redaction:
      enabled: true
    context:
      enabled: true
  tracing:
    enabled: true
    backend: logfire
    logfire:
      token: ${LOGFIRE_TOKEN}
      environment: production

services:
  counter:
    enabled: true
    autostart: false
    initial_value: 0
    step: 1

  ticker:
    enabled: true
    autostart: true
    interval_seconds: 2.0
```

Load the configuration:

```python
app = await Application.create("config.yaml")
```

### Environment variable substitution

YAML values can contain `${ENV_VAR}` tokens that are replaced at load time by the `FileProvider`:

- `${VAR}` — replaced with the value of environment variable `VAR`. Raises an error if the variable is not set.
- `${VAR:-default}` — replaced with the value of `VAR`, or `"default"` if the variable is not set.

```yaml
observability:
  tracing:
    logfire:
      token: ${LOGFIRE_TOKEN}

server:
  host: ${APP_HOST:-0.0.0.0}
  port: ${APP_PORT:-8000}
```

This replaces the v1 `EnvProvider` with a simpler, more explicit mechanism.

## Configuration Providers

### FileProvider

Reads a YAML file and performs `${ENV_VAR}` token replacement:

```python
from processpype.config.providers import FileProvider

provider = FileProvider("config.yaml")
config_dict = await provider.load()
```

### Custom providers

Implement `ConfigurationProvider` to add new sources:

```python
from processpype.config.providers import ConfigurationProvider
from typing import Any


class VaultProvider(ConfigurationProvider):
    async def load(self) -> dict[str, Any]:
        # Fetch secrets from HashiCorp Vault
        return {
            "observability": {
                "tracing": {
                    "logfire": {"token": "secret-from-vault"},
                },
            },
        }

    async def save(self, config: dict[str, Any]) -> None:
        pass  # read-only
```

## Loading Configuration

The `load_config()` function provides the standard way to load configuration:

```python
from processpype.config import load_config

# From a YAML file
config = await load_config("config.yaml")

# With overrides
config = await load_config(
    "config.yaml",
    app={"debug": True},
    server={"port": 9090},
)

# Defaults only (no file)
config = await load_config()
```

`load_config()` loads the YAML file via `FileProvider`, applies any keyword overrides (shallow-merged at the top level), and returns a validated `ProcessPypeConfig` instance.

`Application.create()` uses `load_config()` internally, so you rarely need to call it directly.
