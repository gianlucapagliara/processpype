"""Exceptions for the secrets subsystem."""


class SecretsError(Exception):
    """Base exception for the secrets subsystem."""


class SecretNotFoundError(SecretsError):
    """Raised when a requested secret key does not exist."""


class SecretsBackendError(SecretsError):
    """Raised when the backend fails (network error, auth error, etc.)."""
