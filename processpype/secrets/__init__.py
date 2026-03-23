"""Secrets management for ProcessPype."""

from processpype.config.models import (
    AWSBackendConfig,
    BackendConfig,
    DotenvBackendConfig,
    EnvBackendConfig,
    FileBackendConfig,
    SecretsConfig,
)
from processpype.secrets.exceptions import (
    SecretNotFoundError,
    SecretsBackendError,
    SecretsError,
)
from processpype.secrets.manager import SecretsManager, create_secrets_manager
from processpype.secrets.providers import SecretsProvider

__all__ = [
    "AWSBackendConfig",
    "BackendConfig",
    "DotenvBackendConfig",
    "EnvBackendConfig",
    "FileBackendConfig",
    "SecretNotFoundError",
    "SecretsBackendError",
    "SecretsConfig",
    "SecretsError",
    "SecretsManager",
    "SecretsProvider",
    "create_secrets_manager",
]
