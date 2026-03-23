# Configuration API Reference

`processpype.config`

## ConfigurationModel

`processpype.config.models.ConfigurationModel`

```python
class ConfigurationModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
```

Base for all configuration models. Extra fields are allowed so services can accept extended configuration from YAML without explicit field definitions. Models are immutable after creation.

## ServiceConfiguration

`processpype.config.models.ServiceConfiguration`

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

## ProcessPypeConfig

`processpype.config.models.ProcessPypeConfig`

The root configuration model. Mirrors the YAML structure exactly.

```python
class ProcessPypeConfig(ConfigurationModel):
    app: AppConfig = AppConfig()
    server: ServerConfig = ServerConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    communications: CommunicationsConfig = CommunicationsConfig()
    secrets: SecretsConfig = SecretsConfig()
    services: dict[str, ServiceConfiguration] = {}
```

### AppConfig

`processpype.config.models.AppConfig`

Application identity and environment settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | `str` | `"ProcessPype"` | API title (shown in OpenAPI docs) |
| `version` | `str` | `"0.1.0"` | API version |
| `environment` | `str` | `"development"` | Environment name |
| `debug` | `bool` | `False` | Enable debug logging |
| `timezone` | `str` | `"UTC"` | Application timezone |

### ServerConfig

`processpype.config.models.ServerConfig`

FastAPI / Uvicorn server settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | `str` | `"0.0.0.0"` | Uvicorn bind host |
| `port` | `int` | `8000` | Uvicorn bind port |
| `api_prefix` | `str` | `""` | URL prefix for all routes |
| `closing_timeout_seconds` | `int` | `60` | Max seconds to wait for services to stop |

`api_prefix` is validated to always start with `/` if non-empty.

### ObservabilityConfig

`processpype.config.models.ObservabilityConfig`

Combined logging and tracing configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `logging` | `LoggingConfig` | `LoggingConfig()` | Logging subsystem settings |
| `tracing` | `TracingConfig` | `TracingConfig()` | Tracing subsystem settings |

### LoggingConfig

`processpype.config.models.LoggingConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | When `False`, no logging handlers are installed |
| `level` | `str` | `"INFO"` | Root log level |
| `format` | `str` | `"color"` | Default format: `text`, `color`, or `json` |
| `loggers` | `dict[str, str]` | `{}` | Per-logger level overrides (e.g. `{"noisy.lib": "WARNING"}`) |
| `custom_levels` | `dict[str, int]` | `{}` | Custom log level name to numeric value |
| `handlers` | `dict[str, dict]` | `{}` | Additional dictConfig-style handler definitions |
| `redaction` | `RedactionConfig` | `RedactionConfig()` | Secret redaction settings |
| `context` | `ContextConfig` | `ContextConfig()` | Async context injection settings |

### TracingConfig

`processpype.config.models.TracingConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable distributed tracing |
| `backend` | `str` | `"console"` | Tracing backend: `logfire`, `otlp_grpc`, `otlp_http`, `console` |
| `service_name` | `str` | `""` | OTEL service name |
| `endpoint` | `str` | `""` | OTLP collector endpoint |
| `logfire` | `LogfireConfig` | `LogfireConfig()` | Logfire-specific settings |
| `sampling_rate` | `float` | `1.0` | Trace sampling rate (0.0--1.0) |
| `instrumentation_name` | `str` | `"processpype"` | OpenTelemetry instrumentation scope name |
| `instrumentation_version` | `str` | `"1.0.0"` | OpenTelemetry instrumentation scope version |

### LogfireConfig

`processpype.config.models.LogfireConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `token` | `str` | `""` | Logfire API token |
| `environment` | `str` | `""` | Logfire environment tag |

### SecretsConfig

`processpype.config.models.SecretsConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable the secrets subsystem |
| `backends` | `dict[str, BackendConfig]` | `{}` | Named backend configurations |
| `load` | `list[str]` | `[]` | Preload declarations (`"backend:pattern"`) |
| `cache_enabled` | `bool` | `True` | Enable secret caching |

See the [Secrets API Reference](secrets.md) for backend configuration details.

### CommunicationsConfig

`processpype.config.models.CommunicationsConfig`

Top-level communications configuration. Backends are discriminated by the `type` field.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable the communications subsystem |
| `backends` | `dict[str, CommunicatorBackendConfigType]` | `{}` | Named communicator backends (dispatched by `type`) |

### CommunicatorBackendConfig

`processpype.config.models.CommunicatorBackendConfig`

Base configuration for a communicator backend instance.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | *(required)* | Backend type: `telegram`, `email`, or a custom identifier |
| `enabled` | `bool` | `True` | Whether this backend is active |
| `labels` | `list[str]` | `["default"]` | Labels this backend handles for message routing |

`labels` is validated to contain at least one entry.

### TelegramCommunicatorConfig

`processpype.config.models.TelegramCommunicatorConfig`

Extends `CommunicatorBackendConfig` with Telegram-specific fields.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_id` | `int` | *(required)* | Telegram API ID |
| `api_hash` | `str` | *(required)* | Telegram API hash |
| `token` | `str` | *(required)* | Bot token |
| `session_string` | `str` | `""` | Session string for auth |
| `listen_to_commands` | `bool` | `False` | Enable incoming message handling |
| `chats` | `dict[str, TelegramChatConfig]` | `{}` | Chat configurations keyed by label |

### TelegramChatConfig

`processpype.config.models.TelegramChatConfig`

Configuration for a single Telegram chat/channel destination.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `chat_id` | `str` | *(required)* | Chat/channel identifier (validated non-empty) |
| `topic_id` | `int \| None` | `None` | Forum topic ID |
| `command_authorized` | `bool` | `False` | Accept commands from this chat |
| `active` | `bool` | `True` | Whether this chat is active |

### EmailCommunicatorConfig

`processpype.config.models.EmailCommunicatorConfig`

Email-specific communicator settings (send-only).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | `str` | `"localhost"` | SMTP host |
| `port` | `int` | `587` | SMTP port |
| `username` | `str` | `""` | SMTP username |
| `password` | `str` | `""` | SMTP password |
| `from_address` | `str` | *(required)* | Sender email address |
| `use_tls` | `bool` | `True` | Use TLS |
| `start_tls` | `bool` | `False` | Use STARTTLS after connecting (for port 587) |
| `default_recipients` | `list[str]` | `[]` | Default recipient addresses |

### Example YAML

```yaml
app:
  title: "My App"
  version: "1.0.0"
  environment: production
  debug: false
  timezone: UTC

server:
  host: 0.0.0.0
  port: 8080
  api_prefix: /api/v1

observability:
  logging:
    level: INFO
    format: json
  tracing:
    enabled: true
    backend: logfire
    logfire:
      token: ${LOGFIRE_TOKEN}

communications:
  enabled: true
  backends:
    telegram_bot:
      type: telegram
      api_id: 12345
      api_hash: ${TELEGRAM_API_HASH}
      token: ${TELEGRAM_BOT_TOKEN}
      chats:
        alerts:
          chat_id: "-1001234567890"
    email_alerts:
      type: email
      host: smtp.example.com
      port: 587
      from_address: alerts@example.com
      start_tls: true

services:
  my_service:
    enabled: true
    autostart: true
```

## load_config

`processpype.config.manager.load_config`

```python
async def load_config(
    config_file: str | None = None,
    **overrides: Any,
) -> ProcessPypeConfig
```

Load `ProcessPypeConfig` from a YAML file with optional keyword overrides.

If no `config_file` is provided, the returned configuration is built solely from `overrides` (plus defaults).

If a file is provided, the function reads it via `FileProvider` (which performs `${ENV_VAR}` token replacement), then shallow-merges any `overrides` on top.

## Configuration Providers

### ConfigurationProvider (abstract)

`processpype.config.providers.ConfigurationProvider`

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

Reads and writes YAML files. Returns an empty dict if the file does not exist. Performs `${ENV_VAR}` and `${ENV_VAR:-default}` token replacement on load.

### Environment Variable Tokens

Instead of a dedicated `EnvProvider`, YAML values can reference environment variables using `${ENV_VAR}` syntax:

- `${VAR}` --- replaced with `os.environ["VAR"]`, raises if not set
- `${VAR:-default}` --- replaced with `os.environ.get("VAR", "default")`

Example:

```yaml
observability:
  tracing:
    logfire:
      token: ${LOGFIRE_TOKEN}
    endpoint: ${OTEL_ENDPOINT:-http://localhost:4317}
```

### Secret Tokens

`processpype.config.providers.resolve_secret_tokens`

```python
def resolve_secret_tokens(value: Any, secrets_manager: Any) -> Any
```

Recursively replaces `${secret://backend:key}` tokens in strings, dicts, and lists using the secrets manager. Called automatically during application initialization after the secrets manager is created.
