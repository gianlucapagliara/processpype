from importlib import import_module
from typing import Any, Self, cast

from agentspype.agent.agent import Agent
from pydantic import Field, model_validator

from processpype.core.configuration.models import ServiceConfiguration


class AgentConfiguration(ServiceConfiguration):
    """Configuration for a single agent."""

    agent_name: str
    agent_path: str
    agent_configuration: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_agent_configuration(self) -> Self:
        """Validate the agent configuration."""
        if not self.agent_name.strip():
            raise ValueError("agent_name cannot be empty or whitespace")

        if not self.agent_path.strip():
            raise ValueError("agent_path cannot be empty or whitespace")

        # Validate the path format (should be a valid Python import path)
        if ".." in self.agent_path or "//" in self.agent_path:
            raise ValueError("agent_path contains invalid path sequences")

        return self

    @property
    def import_path(self) -> str:
        """Get the import path for the agent."""
        return self.agent_path.replace("/", ".").rstrip(".")

    def create_instance(self) -> Agent:
        """Create an instance of the agent."""
        try:
            agent_class = cast(
                type[Agent],
                import_module(self.import_path).__getattribute__(self.agent_name),
            )
            return agent_class(self.agent_configuration)
        except (ImportError, AttributeError) as e:
            import logging

            logging.getLogger("agent_service").error(
                f"Failed to import agent {self.agent_name} from {self.import_path}: {e}"
            )
            raise


class AgentServiceConfiguration(ServiceConfiguration):
    """Configuration for the agent service."""

    # Default import path for dynamic agent creation
    fixed_agent_name: str | None = None
    fixed_agent_path: str | None = None

    # List of agent configurations
    agents: list[AgentConfiguration | dict[str, Any]] = Field(
        default_factory=list, description="List of agent configurations"
    )

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        """Validate the configuration after model creation."""
        if not self.agents:
            raise ValueError("At least one agent configuration must be provided")

        for agent_config in self.agents:
            if isinstance(agent_config, dict):
                if not self.fixed_agent_name or not self.fixed_agent_path:
                    raise ValueError(
                        "fixed_agent_name and fixed_agent_path are required for dynamic agent creation"
                    )
                # Validate the agent configuration dictionary is not empty
                if not agent_config:
                    raise ValueError("Agent configuration dictionary cannot be empty")
            elif isinstance(agent_config, AgentConfiguration):
                # Validate agent paths
                if not agent_config.agent_path:
                    raise ValueError("Agent path cannot be empty")
                if not agent_config.agent_name:
                    raise ValueError("Agent name cannot be empty")
            else:
                raise ValueError(
                    f"Invalid agent configuration type: {type(agent_config).__name__}"
                )
        return self

    def get_agent_instances(self) -> list[Agent]:
        """Create instances of all configured agents."""
        instances = []

        for agent_config in self.agents:
            try:
                if isinstance(agent_config, dict):
                    agent_config = AgentConfiguration(
                        agent_name=cast(str, self.fixed_agent_name),
                        agent_path=cast(str, self.fixed_agent_path),
                        agent_configuration=agent_config,
                    )
                else:
                    agent_config = agent_config

                instances.append(agent_config.create_instance())
            except Exception as e:
                import logging

                logging.getLogger("agent_service").error(
                    f"Failed to create agent instance: {e}"
                )
                # Continue with other agents

        return instances
