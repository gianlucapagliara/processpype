"""Application manager — service registration and lifecycle orchestration."""

import logging
from typing import Any

from processpype.config.models import ProcessPypeConfig, ServiceConfiguration
from processpype.service.base import Service
from processpype.service.models import ServiceState


class ApplicationManager:
    """Manages service registration, configuration, and lifecycle."""

    def __init__(self, logger: logging.Logger, config: ProcessPypeConfig) -> None:
        self._logger = logger
        self._config = config
        self._services: dict[str, Service] = {}
        self._state = ServiceState.STOPPED

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    def services(self) -> dict[str, Service]:
        return self._services

    def register_service(
        self, service_class: type[Service], name: str | None = None
    ) -> Service:
        if name is None:
            base_name = service_class.__name__.lower().replace("service", "")
            existing = [s for s in self._services.keys() if s.startswith(base_name)]
            name = f"{base_name}_{len(existing)}" if existing else base_name

        service = service_class(name)

        if service.name in self._services:
            raise ValueError(f"Service {service.name} already registered")

        # Apply config from YAML if present
        if service.name in self._config.services:
            service_config = self._config.services[service.name]
            if not isinstance(service_config, ServiceConfiguration):
                service_config = ServiceConfiguration.model_validate(service_config)
            service.configure(service_config)

        self._services[service.name] = service
        self._logger.info(f"Registered service: {service.name}")
        return service

    def get_service(self, name: str) -> Service | None:
        return self._services.get(name)

    def get_services_by_type(self, service_type: type[Service]) -> list[Service]:
        return [s for s in self._services.values() if isinstance(s, service_type)]

    def set_state(self, state: ServiceState) -> None:
        self._logger.info(f"Application state changed: {self._state} -> {state}")
        self._state = state

    async def start_service(self, service_name: str) -> None:
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        self._logger.info(f"Starting service: {service_name}")
        await service.start()

    async def stop_service(self, service_name: str) -> None:
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        self._logger.info(f"Stopping service: {service_name}")
        await service.stop()

    def configure_service(self, service_name: str, config: dict[str, Any]) -> None:
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        self._logger.info(f"Configuring service: {service_name}")
        service.configure(config)

    async def configure_and_start_service(
        self, service_name: str, config: dict[str, Any]
    ) -> None:
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        self._logger.info(f"Configuring and starting service: {service_name}")
        await service.configure_and_start(config)

    async def start_enabled_services(self) -> None:
        for service_name, service in self._services.items():
            if service_name in self._config.services:
                service_config = self._config.services[service_name]
                if isinstance(service_config, dict) and not service_config.get(
                    "enabled", True
                ):
                    self._logger.info(f"Skipping disabled service: {service_name}")
                    continue
                elif (
                    isinstance(service_config, ServiceConfiguration)
                    and not service_config.enabled
                ):
                    self._logger.info(f"Skipping disabled service: {service_name}")
                    continue

            if service.status.is_configured or not service.requires_configuration():
                self._logger.info(f"Starting enabled service: {service_name}")
                try:
                    await service.start()
                except Exception as e:
                    self._logger.error(
                        f"Failed to start service {service_name}: {e}", exc_info=True
                    )
                    service.set_error(str(e))

    async def stop_all_services(self) -> None:
        for service_name, service in self._services.items():
            if service.status.state in (ServiceState.RUNNING, ServiceState.STARTING):
                self._logger.info(f"Stopping service: {service_name}")
                try:
                    await service.stop()
                except Exception as e:
                    self._logger.error(
                        f"Failed to stop service {service_name}: {e}", exc_info=True
                    )
                    service.set_error(str(e))
