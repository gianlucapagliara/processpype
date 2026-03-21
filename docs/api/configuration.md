# Configuration API Reference

`processpype.core.configuration`

## ConfigurationModel

`processpype.core.configuration.models.ConfigurationModel`

```python
class ConfigurationModel(BaseModel):
    class Config:
        extra = "allow"   # unknown fields are stored, not rejected
        frozen = True     # immutable after creation
```

Base for all configuration models. Extra fields are allowed so services can accept extended configuration from YAML without explicit field definitions.

## ServiceConfiguration

`processpype.core.configuration.models.ServiceConfiguration`

```python
class ServiceConfiguration(ConfigurationModel):
    enabled: bool = True
    autostart: bool = False
```

Base configuration for all services. Extend this class to add service-specific fields.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether the service participates in `start_enabled_services()` |
| `autostart` | `bool` | `False` | Schedule `start()` automatically after `configure()` |

## ApplicationConfiguration

`processpype.core.configuration.models.ApplicationConfiguration`

```python
class ApplicationConfiguration(ConfigurationModel):
    title: str = "ProcessPype"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: str = "development"
    logfire_key: str | None = None
    services: dict[str, ServiceConfiguration] = {}
    api_prefix: str = ""
    closing_timeout_seconds: int = 60
    logfire: LogfireConfiguration | None = None
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | `str` | `"ProcessPype"` | API title (shown in OpenAPI docs) |
| `version` | `str` | `"0.1.0"` | API version |
| `host` | `str` | `"0.0.0.0"` | Uvicorn bind host |
| `port` | `int` | `8000` | Uvicorn bind port |
| `debug` | `bool` | `False` | Enable debug logging |
| `environment` | `str` | `"development"` | Environment name for Logfire |
| `logfire_key` | `str \| None` | `None` | Logfire API token; enables Logfire if set |
| `services` | `dict[str, ServiceConfiguration]` | `{}` | Per-service configuration |
| `api_prefix` | `str` | `""` | URL prefix for all routes |
| `closing_timeout_seconds` | `int` | `60` | Max seconds to wait for services to stop |
| `logfire` | `LogfireConfiguration \| None` | `None` | Detailed Logfire settings |

`api_prefix` is validated to always start with `/` if non-empty.

## LogfireConfiguration

`processpype.core.configuration.models.LogfireConfiguration`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key` | `str \| None` | `None` | Logfire API key |
| `environment` | `str` | `"development"` | Environment name |
| `app_name` | `str` | `"ProcessPype"` | Application name |
| `enabled` | `bool` | `True` | Whether Logfire is enabled |
| `enable_logs` | `bool` | `True` | Whether to enable log forwarding |

## ConfigurationManager

`processpype.core.configuration.manager.ConfigurationManager`

Orchestrates configuration loading from multiple providers.

### Class Method: `load_application_config`

```python
@classmethod
async def load_application_config(
    cls,
    config_file: str | None = None,
    **kwargs: Any,
) -> ApplicationConfiguration
```

Load `ApplicationConfiguration` from a YAML file (optional) and keyword overrides.

If no `config_file` is provided, the returned configuration is built solely from `kwargs`.

If a file is provided, the manager adds a `FileProvider` and `EnvProvider`, initializes both, and returns the merged result as `ApplicationConfiguration`.

---

### `add_provider`

```python
async def add_provider(self, provider: ConfigurationProvider) -> None
```

Add a configuration provider. If the manager is already initialized, the new provider is loaded immediately and merged.

---

### `initialize`

```python
async def initialize(self) -> None
```

Load all registered providers. Providers are loaded in reverse registration order, so the first-added provider wins (last writer loses). Idempotent.

---

### `get`

```python
def get(self, key: str, default: Any = None) -> Any
```

Get a value from the merged configuration dictionary.

---

### `get_model`

```python
def get_model(self, model: type[ApplicationConfiguration]) -> ApplicationConfiguration
```

Validate and return the merged configuration as a Pydantic model.

---

### `set`

```python
async def set(self, key: str, value: Any, save: bool = True) -> None
```

Set a configuration value. If `save=True`, the value is written to all providers that support saving.

## Configuration Providers

### ConfigurationProvider (abstract)

`processpype.core.configuration.providers.ConfigurationProvider`

```python
class ConfigurationProvider(ABC):
    @abstractmethod
    async def load(self) -> dict[str, Any]: ...

    @abstractmethod
    async def save(self, config: dict[str, Any]) -> None: ...
```

### FileProvider

```python
class FileProvider(ConfigurationProvider):
    def __init__(self, path: str | Path) -> None
```

Reads and writes YAML files. Returns an empty dict if the file does not exist.

### EnvProvider

```python
class EnvProvider(ConfigurationProvider):
    def __init__(self, prefix: str = "PROCESSPYPE_") -> None
```

Reads environment variables with the given prefix. Double underscores (`__`) are split into nested dictionary keys. `save()` is a no-op.

Example: `PROCESSPYPE_SERVICES__COUNTER__ENABLED=true` sets `config["services"]["counter"]["enabled"] = "true"`.
