# Agent Service

The `AgentService` integrates [agentspype](https://github.com/gianlucapagliara/agentspype) into ProcessPype, enabling agent-based workflows within the service framework.

## Installation

Install the `agents` extra:

```bash
uv add "processpype[agents]"
```

## Location

The agent service is located at `processpype/services/agent/`.

## Usage

```python
from processpype.services.agent.service import AgentService

service = app.register_service(AgentService)
await app.start_service(service.name)
```

## Overview

The `AgentService` wraps agentspype agent management inside the ProcessPype service lifecycle. Agents are autonomous units that can perform tasks, react to events, or drive complex workflows.

Refer to the [agentspype documentation](https://github.com/gianlucapagliara/agentspype) for details on implementing agents.

## REST Endpoints

The agent service uses the standard `ServiceRouter` endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/agent` | Service status |
| `POST` | `/services/agent/start` | Start the service |
| `POST` | `/services/agent/stop` | Stop the service |
| `POST` | `/services/agent/configure` | Configure the service |
| `POST` | `/services/agent/configure_and_start` | Configure and start |
