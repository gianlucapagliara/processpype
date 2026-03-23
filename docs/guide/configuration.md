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
| `CommunicationsConfig` | `communications` | `enabled`, `backends` |

### CommunicationsConfig

The `communications` section configures outbound messaging backends (Telegram, Email, or custom). Each backend is identified by a unique name and dispatched by its `type` field.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable the communications subsystem |
| `backends` | `dict[str, CommunicatorBackendConfig]` | `{}` | Named communicator backends |

#### CommunicatorBackendConfig (base)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | *(required)* | Backend type: `telegram`, `email`, or a custom identifier |
| `enabled` | `bool` | `True` | Whether this backend is active |
| `labels` | `list[str]` | `["default"]` | Labels this backend handles for message routing |

#### TelegramCommunicatorConfig

Extends `CommunicatorBackendConfig` with `type: telegram`. Requires the `telegram` extra (`pip install processpype[telegram]`).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_id` | `int` | *(required)* | Telegram API ID |
| `api_hash` | `str` | *(required)* | Telegram API hash |
| `token` | `str` | *(required)* | Bot token |
| `session_string` | `str` | `""` | Session string for auth |
| `listen_to_commands` | `bool` | `False` | Enable incoming message handling |
| `chats` | `dict[str, TelegramChatConfig]` | `{}` | Chat configurations keyed by label |

#### TelegramChatConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `chat_id` | `str` | *(required)* | Chat/channel identifier |
| `topic_id` | `int \| None` | `None` | Forum topic ID |
| `command_authorized` | `bool` | `False` | Accept commands from this chat |
| `active` | `bool` | `True` | Whether this chat is active |

#### EmailCommunicatorConfig

Extends `CommunicatorBackendConfig` with `type: email`. Requires the `email` extra (`pip install processpype[email]`).

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

#### Example

```yaml
communications:
  enabled: true
  backends:
    telegram_bot:
      type: telegram
      api_id: ${TELEGRAM_API_ID}
      api_hash: ${TELEGRAM_API_HASH}
      token: ${TELEGRAM_BOT_TOKEN}
      listen_to_commands: true
      labels:
        - alerts
        - reports
      chats:
        alerts:
          chat_id: "-1001234567890"
          topic_id: 42
        reports:
          chat_id: "-1009876543210"

    email_alerts:
      type: email
      host: smtp.example.com
      port: 587
      username: ${SMTP_USER}
      password: ${SMTP_PASS}
      from_address: alerts@example.com
      start_tls: true
      labels:
        - alerts
      default_recipients:
        - ops@example.com
```

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

### Secret token substitution

YAML values can also reference secrets loaded by the secrets subsystem using `${secret://backend:key}` tokens.
These are resolved as a second pass after the secrets manager is initialized:

```yaml
services:
  my_service:
    api_key: ${secret://env:API_KEY}
    db_password: ${secret://aws:postgres}
```

Secret tokens are left as literal strings during the initial `${ENV_VAR}` pass and resolved later.
See the [Secrets guide](secrets.md) for full configuration details.

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
