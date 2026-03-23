"""Secrets providers — ABC and built-in implementations."""

import json
import logging
import os
import re as _re
from abc import ABC, abstractmethod
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from processpype.secrets.exceptions import SecretNotFoundError, SecretsBackendError

logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    """Base secrets provider — fetches individual secrets by key.

    Providers receive *logical* keys (without the backend prefix from config).
    The ``SecretsManager`` is responsible for prepending/stripping the
    backend-level ``prefix`` before calling into the provider.
    """

    @abstractmethod
    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        """Fetch a single secret by its full name (prefix already applied).

        Returns the secret value as a string or parsed dict.
        When *raw* is True, return the string value without JSON parsing.
        Raises SecretNotFoundError if the key does not exist.
        Raises SecretsBackendError on infrastructure failures.
        """

    @abstractmethod
    def list_secrets(self, pattern: str) -> list[str]:
        """List secret full names matching a glob pattern (prefix already applied)."""


class EnvironmentProvider(SecretsProvider):
    """Reads secrets from environment variables."""

    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        value = os.environ.get(name)
        if value is None:
            raise SecretNotFoundError(f"Environment variable '{name}' not set")
        if raw:
            return value
        return _try_parse_json(value)

    def list_secrets(self, pattern: str) -> list[str]:
        return [key for key in os.environ if fnmatch(key, pattern)]


class FileSecretsProvider(SecretsProvider):
    """Reads secrets from a YAML file.

    The file is loaded once on first access and cached internally.
    Supports ``${ENV_VAR}`` token replacement in values.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._data is None:
            if not self._path.exists():
                raise SecretsBackendError(f"Secrets file not found: {self._path}")
            with open(self._path) as f:
                raw = yaml.safe_load(f) or {}
            from processpype.config.providers import replace_env_tokens

            try:
                self._data = replace_env_tokens(raw)
            except ValueError as e:
                raise SecretsBackendError(
                    f"Failed to process secrets file {self._path}: {e}"
                ) from e
        return self._data

    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        data = self._load()
        if name not in data:
            raise SecretNotFoundError(f"Secret '{name}' not found in {self._path}")
        value = data[name]
        if raw:
            return value if isinstance(value, str) else str(value)
        if isinstance(value, str | dict):
            return value
        return str(value)

    def list_secrets(self, pattern: str) -> list[str]:
        data = self._load()
        return [key for key in data if fnmatch(key, pattern)]


class DotenvProvider(SecretsProvider):
    """Reads secrets from a ``.env`` file.

    The file is parsed once on first access.  Lines must be in
    ``KEY=VALUE`` format (leading ``export`` is stripped, comments and
    blank lines are skipped).
    """

    def __init__(self, file_path: str | Path = ".env") -> None:
        self._path = Path(file_path)
        self._data: dict[str, str] | None = None

    def _load(self) -> dict[str, str]:
        if self._data is None:
            if not self._path.exists():
                raise SecretsBackendError(f"Dotenv file not found: {self._path}")
            self._data = _parse_dotenv(self._path)
        return self._data

    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        data = self._load()
        if name not in data:
            raise SecretNotFoundError(
                f"Key '{name}' not found in dotenv file {self._path}"
            )
        if raw:
            return data[name]
        return _try_parse_json(data[name])

    def list_secrets(self, pattern: str) -> list[str]:
        data = self._load()
        return [key for key in data if fnmatch(key, pattern)]


class AWSSecretsProvider(SecretsProvider):
    """Reads secrets from AWS Secrets Manager.

    Requires ``boto3`` — install with ``pip install processpype[aws]``.
    """

    def __init__(self, region_name: str = "", profile_name: str = "") -> None:
        self._region_name = region_name or None
        self._profile_name = profile_name or None
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
                import boto3.session
            except ImportError as e:
                raise SecretsBackendError(
                    "boto3 is required for AWS secrets. "
                    "Install with: pip install processpype[aws]"
                ) from e

            session = boto3.session.Session(
                profile_name=self._profile_name,
                region_name=self._region_name,
            )
            self._client = session.client(service_name="secretsmanager")
        return self._client

    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        client = self._get_client()
        try:
            response = client.get_secret_value(SecretId=name)
        except client.exceptions.ResourceNotFoundException as e:
            raise SecretNotFoundError(f"AWS secret '{name}' not found") from e
        except Exception as e:
            raise SecretsBackendError(
                f"AWS Secrets Manager error for '{name}': {e}"
            ) from e

        if "SecretString" not in response:
            raise SecretsBackendError(
                f"Secret '{name}' is binary — only string secrets are supported"
            )

        secret_string: str = response["SecretString"]
        if raw:
            return secret_string
        return _try_parse_json(secret_string)

    def list_secrets(self, pattern: str) -> list[str]:
        client = self._get_client()
        try:
            paginator = client.get_paginator("list_secrets")
            has_glob = bool(_re.search(r"[*?\[]", pattern))
            if has_glob:
                # No server-side filter — fetch all, filter client-side
                paginator_kwargs: dict[str, Any] = {}
            else:
                # Exact match — use server-side filter
                paginator_kwargs = {"Filters": [{"Key": "name", "Values": [pattern]}]}
            pages = paginator.paginate(**paginator_kwargs)
            names: list[str] = []
            for page in pages:
                for entry in page.get("SecretList", []):
                    name = entry.get("Name", "")
                    if fnmatch(name, pattern):
                        names.append(name)
            return names
        except Exception as e:
            raise SecretsBackendError(
                f"AWS ListSecrets error for pattern '{pattern}': {e}"
            ) from e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _try_parse_json(value: str) -> str | dict[str, Any]:
    """Attempt to parse a string as JSON dict, returning the original string on failure."""
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return value


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, handling common formats."""
    data: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip optional 'export ' prefix
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                logger.warning("Skipping malformed line in %s: %r", path, line)
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                quote_char = value[0]
                value = value[1:-1]
                if quote_char == '"':
                    value = (
                        value.replace("\\n", "\n")
                        .replace("\\t", "\t")
                        .replace("\\r", "\r")
                        .replace("\\\\", "\\")
                    )
            data[key] = value
    return data
