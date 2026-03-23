# Secrets API Reference

Module path: `processpype.secrets`

---

## SecretsConfig

`processpype.config.models.SecretsConfig`

```python
class SecretsConfig(ConfigurationModel):
    enabled: bool = False
    backends: dict[str, BackendConfig] = {}
    load: list[str] = []
    cache_enabled: bool = True
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable the secrets subsystem |
| `backends` | `dict[str, BackendConfig]` | `{}` | Named backend configurations |
| `load` | `list[str]` | `[]` | `"backend:pattern"` declarations to preload at startup |
| `cache_enabled` | `bool` | `True` | Enable in-memory caching of fetched secrets |

---

## Backend Configurations

Backend selection uses a discriminated union on the `type` field.

### AWSBackendConfig

`processpype.config.models.AWSBackendConfig`

```python
class AWSBackendConfig(ConfigurationModel):
    type: Literal["aws"] = "aws"
    region_name: str = ""
    profile_name: str = ""
    prefix: str = ""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `Literal["aws"]` | `"aws"` | Backend type discriminator |
| `region_name` | `str` | `""` | AWS region |
| `profile_name` | `str` | `""` | AWS profile |
| `prefix` | `str` | `""` | Prefix prepended to all secret names |

---

### FileBackendConfig

`processpype.config.models.FileBackendConfig`

```python
class FileBackendConfig(ConfigurationModel):
    type: Literal["file"] = "file"
    path: str = ""
    prefix: str = ""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `Literal["file"]` | `"file"` | Backend type discriminator |
| `path` | `str` | `""` | Path to YAML secrets file |
| `prefix` | `str` | `""` | Prefix prepended to key lookups |

---

### DotenvBackendConfig

`processpype.config.models.DotenvBackendConfig`

```python
class DotenvBackendConfig(ConfigurationModel):
    type: Literal["dotenv"] = "dotenv"
    path: str = ".env"
    prefix: str = ""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `Literal["dotenv"]` | `"dotenv"` | Backend type discriminator |
| `path` | `str` | `".env"` | Path to the .env file |
| `prefix` | `str` | `""` | Prefix prepended to key lookups |

---

### EnvBackendConfig

`processpype.config.models.EnvBackendConfig`

```python
class EnvBackendConfig(ConfigurationModel):
    type: Literal["env"] = "env"
    prefix: str = ""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `Literal["env"]` | `"env"` | Backend type discriminator |
| `prefix` | `str` | `""` | Prefix prepended to env var names |

---

## SecretsProvider

`processpype.secrets.providers.SecretsProvider`

Abstract base class for all secrets backends.

```python
class SecretsProvider(ABC):
    @abstractmethod
    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]: ...

    @abstractmethod
    def list_secrets(self, pattern: str) -> list[str]: ...
```

### get_secret

```python
def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]
```

Fetch a single secret by its full name (prefix already applied by the manager).

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Secret name |
| `raw` | `bool` | When `True`, return the raw string without JSON parsing |

**Returns** --- `str | dict[str, Any]`

**Raises**

- `SecretNotFoundError` --- key does not exist
- `SecretsBackendError` --- infrastructure failure

---

### list_secrets

```python
def list_secrets(self, pattern: str) -> list[str]
```

List secret names matching a glob pattern.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `pattern` | `str` | Glob pattern to match against secret names |

**Returns** --- `list[str]`

---

## Built-in Providers

### EnvironmentProvider

`processpype.secrets.providers.EnvironmentProvider`

Reads secrets from `os.environ`. Automatically parses JSON dict values unless `raw=True`.

---

### FileSecretsProvider

`processpype.secrets.providers.FileSecretsProvider`

```python
def __init__(self, file_path: str | Path) -> None
```

Loads a YAML file with `${ENV_VAR}` token replacement in values. The file is read once on first access and cached internally.

---

### DotenvProvider

`processpype.secrets.providers.DotenvProvider`

```python
def __init__(self, file_path: str | Path = ".env") -> None
```

Parses `.env` files in `KEY=VALUE` format. Handles single and double quotes, common escape sequences (`\n`, `\t`, `\r`, `\\`), and optional `export` prefixes.

---

### AWSSecretsProvider

`processpype.secrets.providers.AWSSecretsProvider`

```python
def __init__(self, region_name: str = "", profile_name: str = "") -> None
```

Reads secrets from AWS Secrets Manager. Requires `boto3` --- install with `pip install processpype[aws]`. Only string secrets are supported; binary secrets raise `SecretsBackendError`.

---

## SecretsManager

`processpype.secrets.manager.SecretsManager`

Central access point for secrets across multiple named backends. Resolves `backend:key` references, handles prefix mapping transparently, and provides optional in-memory caching.

```python
def __init__(
    self,
    backends: dict[str, _Backend],
    cache_enabled: bool = True,
) -> None
```

---

### load

```python
def load(self, declarations: list[str]) -> None
```

Resolve `backend:pattern` declarations and preload matching secrets into the cache.

Each declaration is split on the first `:` into a backend name and a glob pattern. The pattern is passed to the backend's `list_secrets` to discover matching keys, which are then fetched and cached.

Partial failures are tolerated --- individual keys that fail are logged and skipped. Raises `SecretsBackendError` only if **all** keys in a declaration fail.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `declarations` | `list[str]` | List of `"backend:pattern"` strings |

**Raises**

- `SecretsBackendError` --- unknown backend, or all keys in a declaration failed

---

### get

```python
def get(self, prefixed_key: str, *, raw: bool = False) -> str | dict[str, Any]
```

Get a secret by `"backend:key"`. Returns a cached value when available; otherwise fetches on demand and caches the result.

When `raw` is `True`, bypasses the cache and returns the raw string without JSON parsing.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `prefixed_key` | `str` | Key in `"backend:key"` format |
| `raw` | `bool` | Skip cache and JSON parsing |

**Returns** --- `str | dict[str, Any]`

**Raises**

- `SecretNotFoundError` --- key does not exist or unknown backend

---

### get_or_none

```python
def get_or_none(self, prefixed_key: str, *, raw: bool = False) -> str | dict[str, Any] | None
```

Same as `get`, but returns `None` instead of raising `SecretNotFoundError`.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `prefixed_key` | `str` | Key in `"backend:key"` format |
| `raw` | `bool` | Skip cache and JSON parsing |

**Returns** --- `str | dict[str, Any] | None`

---

### clear_cache

```python
def clear_cache(self) -> None
```

Clear all cached secrets.

---

### invalidate

```python
def invalidate(self, prefixed_key: str) -> None
```

Remove a specific key from the cache.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `prefixed_key` | `str` | Key in `"backend:key"` format |

---

## create_secrets_manager

`processpype.secrets.manager.create_secrets_manager`

```python
def create_secrets_manager(config: SecretsConfig) -> SecretsManager
```

Factory function. Builds backend instances from the provided config, creates a `SecretsManager`, and runs the initial `load()` if declarations are present.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `config` | `SecretsConfig` | Secrets subsystem configuration |

**Returns** --- `SecretsManager`

---

## resolve_secret_tokens

`processpype.config.providers.resolve_secret_tokens`

```python
def resolve_secret_tokens(value: Any, secrets_manager: Any) -> Any
```

Recursively replaces `${secret://backend:key}` tokens in strings, dicts, and lists using the provided secrets manager.

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| `value` | `Any` | Value to process (string, dict, list, or passthrough) |
| `secrets_manager` | `Any` | A `SecretsManager` instance |

**Returns** --- `Any` (same structure with tokens resolved)

---

## Exceptions

`processpype.secrets.exceptions`

### SecretsError

```python
class SecretsError(Exception): ...
```

Base exception for the secrets subsystem.

---

### SecretNotFoundError

```python
class SecretNotFoundError(SecretsError): ...
```

Raised when a requested secret key does not exist.

---

### SecretsBackendError

```python
class SecretsBackendError(SecretsError): ...
```

Raised on backend infrastructure failures (network errors, auth errors, missing files, etc.).
