"""Secrets manager — multi-backend orchestrator with caching."""

import logging
import threading
from typing import Any

from processpype.config.models import SecretsConfig
from processpype.secrets.exceptions import (
    SecretNotFoundError,
    SecretsBackendError,
)
from processpype.secrets.providers import SecretsProvider

logger = logging.getLogger(__name__)


class _Backend:
    """Wraps a provider with its configured prefix."""

    __slots__ = ("provider", "prefix")

    def __init__(self, provider: SecretsProvider, prefix: str = "") -> None:
        self.provider = provider
        # Normalise: ensure prefix ends with separator when non-empty
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""

    def full_name(self, key: str) -> str:
        """Prepend prefix to a logical key."""
        return f"{self.prefix}{key}"

    def strip_prefix(self, full_name: str) -> str:
        """Strip prefix from a provider-level name to get the logical key."""
        if self.prefix and full_name.startswith(self.prefix):
            return full_name[len(self.prefix) :]
        return full_name

    def get_secret(self, key: str, *, raw: bool = False) -> str | dict[str, Any]:
        return self.provider.get_secret(self.full_name(key), raw=raw)

    def list_secrets(self, pattern: str) -> list[str]:
        """List secrets matching *pattern* (logical), returning logical keys."""
        full_pattern = self.full_name(pattern)
        full_names = self.provider.list_secrets(full_pattern)
        return [self.strip_prefix(n) for n in full_names]


class SecretsManager:
    """Central access point for secrets across multiple named backends.

    Resolves ``backend_name:pattern`` declarations at load time, caches results,
    and provides a ``get("backend:key")`` access API.

    Backend prefixes are handled transparently — callers always use logical
    keys (without the prefix).  For example, if backend ``aws`` has
    ``prefix: "production/exchanges"``, then ``get("aws:binance")`` fetches
    ``production/exchanges/binance`` from AWS Secrets Manager.
    """

    def __init__(
        self,
        backends: dict[str, _Backend],
        cache_enabled: bool = True,
    ) -> None:
        self._backends = backends
        self._cache_enabled = cache_enabled
        self._cache: dict[str, str | dict[str, Any]] = {}
        self._lock = threading.Lock()

    def load(self, declarations: list[str]) -> None:
        """Resolve all ``backend_name:pattern`` declarations and preload into cache.

        Each declaration is split on the first ``:`` into a backend name and a
        pattern.  The pattern is passed to the backend's ``list_secrets`` to
        discover matching keys, which are then fetched and cached.
        """
        for decl in declarations:
            backend_name, pattern = _split_declaration(decl)
            if backend_name not in self._backends:
                raise SecretsBackendError(
                    f"Unknown backend '{backend_name}' in declaration '{decl}'"
                )
            backend = self._backends[backend_name]
            keys = backend.list_secrets(pattern)
            logger.debug(
                "Loading %d secret(s) from '%s' matching '%s'",
                len(keys),
                backend_name,
                pattern,
            )
            failed = 0
            for key in keys:
                try:
                    prefixed = f"{backend_name}:{key}"
                    value = backend.get_secret(key)
                    with self._lock:
                        self._cache[prefixed] = value
                except (SecretNotFoundError, SecretsBackendError) as exc:
                    logger.warning(
                        "Failed to load secret '%s:%s': %s",
                        backend_name,
                        key,
                        exc,
                    )
                    failed += 1
            if failed == len(keys) and keys:
                raise SecretsBackendError(
                    f"All secrets failed to load for declaration '{decl}'"
                )

    def get(self, prefixed_key: str, *, raw: bool = False) -> str | dict[str, Any]:
        """Get a secret by ``backend:key``.

        Returns a cached value if available.  Otherwise fetches on demand from
        the named backend (and caches the result if caching is enabled).

        When *raw* is True, bypass the cache and return the string value
        without automatic JSON parsing.

        Raises ``SecretNotFoundError`` if the key does not exist.
        """
        if not raw:
            with self._lock:
                if self._cache_enabled and prefixed_key in self._cache:
                    return self._cache[prefixed_key]

        backend_name, key = _split_declaration(prefixed_key)
        if backend_name not in self._backends:
            raise SecretNotFoundError(f"Unknown backend: {backend_name}")

        value = self._backends[backend_name].get_secret(key, raw=raw)

        if self._cache_enabled and not raw:
            with self._lock:
                self._cache[prefixed_key] = value

        return value

    def get_or_none(
        self, prefixed_key: str, *, raw: bool = False
    ) -> str | dict[str, Any] | None:
        """Get a secret, returning ``None`` if not found."""
        try:
            return self.get(prefixed_key, raw=raw)
        except SecretNotFoundError:
            return None

    def clear_cache(self) -> None:
        """Clear all cached secrets."""
        with self._lock:
            self._cache.clear()

    def invalidate(self, prefixed_key: str) -> None:
        """Remove a specific secret from the cache."""
        with self._lock:
            self._cache.pop(prefixed_key, None)


def _create_backend(name: str, backend_cfg: Any) -> _Backend:
    """Create a single ``_Backend`` wrapper from its configuration."""
    from processpype.config.models import (
        AWSBackendConfig,
        DotenvBackendConfig,
        FileBackendConfig,
    )
    from processpype.secrets.providers import (
        AWSSecretsProvider,
        DotenvProvider,
        EnvironmentProvider,
        FileSecretsProvider,
    )

    backend_type = backend_cfg.type
    prefix = getattr(backend_cfg, "prefix", "")

    if backend_type == "env":
        return _Backend(EnvironmentProvider(), prefix)
    if backend_type == "file":
        if not isinstance(backend_cfg, FileBackendConfig):
            raise SecretsBackendError(
                f"Backend '{name}': expected file config, got {type(backend_cfg).__name__}"
            )
        if not backend_cfg.path:
            raise SecretsBackendError(
                f"Backend '{name}': 'path' is required for file backend"
            )
        return _Backend(FileSecretsProvider(backend_cfg.path), prefix)
    if backend_type == "dotenv":
        if not isinstance(backend_cfg, DotenvBackendConfig):
            raise SecretsBackendError(
                f"Backend '{name}': expected dotenv config, got {type(backend_cfg).__name__}"
            )
        return _Backend(DotenvProvider(backend_cfg.path), prefix)
    if backend_type == "aws":
        if not isinstance(backend_cfg, AWSBackendConfig):
            raise SecretsBackendError(
                f"Backend '{name}': expected aws config, got {type(backend_cfg).__name__}"
            )
        return _Backend(
            AWSSecretsProvider(
                region_name=backend_cfg.region_name,
                profile_name=backend_cfg.profile_name,
            ),
            prefix,
        )
    raise SecretsBackendError(f"Unknown backend type: {backend_type}")


def create_secrets_manager(config: SecretsConfig) -> SecretsManager:
    """Build backends from config, create manager, and run initial load."""
    backends = {
        name: _create_backend(name, cfg) for name, cfg in config.backends.items()
    }
    manager = SecretsManager(backends, cache_enabled=config.cache_enabled)

    if config.load:
        manager.load(config.load)
        logger.info(
            "Secrets manager ready: %d backend(s), %d secret(s) preloaded",
            len(backends),
            len(manager._cache),
        )
    else:
        logger.info("Secrets manager ready: %d backend(s), no preload", len(backends))

    return manager


def _split_declaration(decl: str) -> tuple[str, str]:
    """Split ``backend_name:pattern`` into ``(backend_name, pattern)``."""
    if ":" not in decl:
        raise ValueError(
            f"Invalid secret declaration '{decl}': expected 'backend_name:pattern'"
        )
    backend_name, _, pattern = decl.partition(":")
    return backend_name, pattern
