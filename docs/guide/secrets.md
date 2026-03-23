# Secrets

ProcessPype includes a multi-backend secrets framework for loading secrets from multiple sources --- environment variables, YAML files, `.env` files, and AWS Secrets Manager. Secrets are preloaded at startup, cached in memory, and accessible throughout your application via a unified `backend:key` API.

## Configuration

Enable the secrets subsystem and declare backends under the `secrets` key in your YAML config:

```yaml
secrets:
  enabled: true
  cache_enabled: true
  backends:
    aws:
      type: aws
      region_name: eu-west-1
      profile_name: my-profile
      prefix: "production/exchanges"
    env:
      type: env
    dotenv:
      type: dotenv
      path: .env
    local:
      type: file
      path: ./secrets.yaml
  load:
    - "aws:*"
    - "env:API_KEY"
    - "dotenv:DB_*"
    - "local:*"
```

### Top-level fields

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Enable the secrets subsystem |
| `cache_enabled` | `true` | Cache fetched secrets in memory |
| `backends` | `{}` | Named backend configurations |
| `load` | `[]` | Secret declarations to preload at startup |

## Backend Types

All backends support a `prefix` field that is transparently prepended to secret names (see [Prefix Support](#prefix-support) below).

### Environment (`type: env`)

Reads secrets from `os.environ`.

| Field | Default | Description |
|-------|---------|-------------|
| `type` | `"env"` | Backend type identifier |
| `prefix` | `""` | Prefix prepended to environment variable names |

```yaml
backends:
  env:
    type: env
    prefix: "APP_"
```

With this configuration, requesting `API_KEY` looks up the environment variable `APP_API_KEY`.

### File (`type: file`)

Reads secrets from a YAML file. The file is loaded once on first access. Values support `${ENV_VAR}` token replacement.

| Field | Default | Description |
|-------|---------|-------------|
| `type` | `"file"` | Backend type identifier |
| `path` | *required* | Path to the YAML secrets file |
| `prefix` | `""` | Prefix prepended to key lookups inside the file |

```yaml
backends:
  local:
    type: file
    path: ./secrets.yaml
```

Example `secrets.yaml`:

```yaml
db_host: localhost
db_password: "${DB_PASSWORD}"
api_credentials: '{"key": "abc", "secret": "xyz"}'
```

### Dotenv (`type: dotenv`)

Reads key-value pairs from a `.env` file. Lines must be in `KEY=VALUE` format. Leading `export` is stripped, comments and blank lines are skipped. Quoted values are unquoted automatically.

| Field | Default | Description |
|-------|---------|-------------|
| `type` | `"dotenv"` | Backend type identifier |
| `path` | `".env"` | Path to the `.env` file |
| `prefix` | `""` | Prefix prepended to key lookups |

```yaml
backends:
  dotenv:
    type: dotenv
    path: .env
```

### AWS Secrets Manager (`type: aws`)

Reads secrets from AWS Secrets Manager. Requires the optional AWS dependency:

```bash
pip install processpype[aws]
```

| Field | Default | Description |
|-------|---------|-------------|
| `type` | `"aws"` | Backend type identifier |
| `region_name` | `""` | AWS region name |
| `profile_name` | `""` | AWS profile name |
| `prefix` | `""` | Prefix prepended to all secret names |

```yaml
backends:
  aws:
    type: aws
    region_name: eu-west-1
    profile_name: my-profile
    prefix: "production/exchanges"
```

## Prefix Support

Every backend supports an optional `prefix` field. When set, the prefix is transparently prepended to all secret names. Callers always use logical keys --- the prefix is invisible at the API level.

For example, with `prefix: "production/exchanges"`:

- Requesting `binance` actually fetches `production/exchanges/binance` from the backend
- Listing secrets strips the prefix from the returned names

This lets you organize secrets by environment or namespace without changing application code.

## Load Declarations

The `load` list tells the secrets manager which secrets to preload at startup. Each entry uses the format `"backend_name:pattern"`.

```yaml
load:
  - "aws:binance"          # specific key
  - "aws:*"                # glob pattern — all secrets
  - "local:db_*"           # glob pattern — keys starting with db_
  - "env:API_KEY"          # specific environment variable
```

Patterns use glob-style matching (`*`, `?`, `[...]`). Matched secrets are fetched and stored in the cache so that subsequent `get()` calls return instantly.

For the AWS backend, glob patterns trigger client-side filtering --- all secrets are listed via the API and filtered locally. Exact matches (no glob characters) use server-side filtering for efficiency.

## Accessing Secrets in Code

Use the `SecretsManager` API with `"backend:key"` notation:

```python
# Get a secret (raises SecretNotFoundError if missing)
value = secrets.get("aws:binance")           # -> str | dict

# Get from environment backend
api_key = secrets.get("env:API_KEY")         # -> str

# Return None instead of raising
value = secrets.get_or_none("aws:missing")   # -> None

# Skip JSON parsing — always return the raw string
token = secrets.get("aws:token", raw=True)   # -> str
```

String values that are valid JSON objects are automatically parsed into dictionaries. Pass `raw=True` to disable this behavior and always receive the raw string.

## Secret Tokens in YAML Config

You can reference secrets directly in your YAML configuration using the `${secret://backend:key}` pattern. These tokens are resolved automatically after the secrets manager initializes.

```yaml
services:
  my_service:
    api_key: ${secret://env:API_KEY}
    db_password: ${secret://aws:postgres}
    exchange_credentials: ${secret://local:binance}
```

This lets you keep sensitive values out of your configuration files entirely.

## Accessing Secrets from Services

Services receive the secrets manager automatically during registration. Access it via the `secrets` property:

```python
class MyManager(ServiceManager):
    async def start(self) -> None:
        api_key = self.service.secrets.get("env:API_KEY")
        credentials = self.service.secrets.get("aws:binance")
```

The `ApplicationManager` injects the secrets manager into each service when it is registered. The `secrets` property returns `SecretsManager | None` --- it is `None` only when the secrets subsystem is disabled.

## Cache Management

Secrets are cached in memory by default (controlled by `cache_enabled`). The cache is thread-safe, protected by a `threading.Lock`.

```python
# Clear all cached secrets
secrets.clear_cache()

# Remove a specific secret from the cache
secrets.invalidate("aws:binance")
```

When `raw=True` is passed to `get()`, the cache is bypassed and the secret is fetched directly from the backend.

## Error Handling

The secrets subsystem defines three exceptions, all importable from `processpype.secrets`:

| Exception | Description |
|-----------|-------------|
| `SecretsError` | Base exception for the secrets subsystem |
| `SecretNotFoundError` | Raised when a requested secret key does not exist |
| `SecretsBackendError` | Raised on backend failures --- network errors, auth errors, missing files |

```python
from processpype.secrets import SecretNotFoundError, SecretsBackendError

try:
    value = secrets.get("aws:missing_key")
except SecretNotFoundError:
    # Key does not exist
    pass
except SecretsBackendError:
    # Infrastructure failure (network, auth, etc.)
    pass
```

## Custom Providers

Implement the `SecretsProvider` ABC to add your own backend:

```python
from typing import Any
from processpype.secrets import SecretsProvider, SecretNotFoundError

class VaultProvider(SecretsProvider):
    def __init__(self, vault_url: str, token: str) -> None:
        self._url = vault_url
        self._token = token

    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        # Fetch the secret from your backend.
        # Raise SecretNotFoundError if the key does not exist.
        ...

    def list_secrets(self, pattern: str) -> list[str]:
        # Return secret names matching the glob pattern.
        # The pattern already includes the configured prefix.
        ...
```

The `name` argument passed to both methods is the full name with the backend prefix already applied. The `SecretsManager` handles prefix prepending and stripping transparently.
