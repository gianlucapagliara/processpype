# Installation

## Requirements

- Python 3.13 or higher

## Install from PyPI

```bash
# Using pip
pip install processpype

# Using uv
uv add processpype

# Using poetry
poetry add processpype
```

## Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| [pydantic](https://docs.pydantic.dev/) | >= 2.10.4 | Configuration and data validation |
| [fastapi](https://fastapi.tiangolo.com/) | >= 0.115.6 | REST API framework |
| [uvicorn](https://www.uvicorn.org/) | >= 0.34.0 | ASGI server |
| [pyyaml](https://pyyaml.org/) | >= 6.0.2 | YAML configuration files |
| [httpx](https://www.python-httpx.org/) | >= 0.28.1 | Async HTTP client |

## Optional Dependencies

ProcessPype provides optional extras for additional functionality:

| Extra | Packages | Purpose |
|-------|----------|---------|
| `events` | eventspype >= 1.1.0, < 2 | Event publication framework |
| `tracing` | opentelemetry-api >= 1.20, opentelemetry-sdk >= 1.20 | OpenTelemetry tracing |
| `logfire` | logfire >= 4.16 + tracing deps | Pydantic Logfire observability |
| `otlp` | opentelemetry-exporter-otlp >= 1.20 + tracing deps | OTLP exporter for tracing |
| `full` | events + logfire | All optional dependencies |

Install extras with:

```bash
# Using pip
pip install processpype[tracing]
pip install processpype[logfire]
pip install processpype[full]

# Using uv
uv add processpype --extra tracing
uv add processpype --extra logfire
uv add processpype --extra full

# Using poetry
poetry add processpype[tracing]
```

## Verify Installation

```python
from processpype import Application, ServiceState

print("processpype installed successfully")
print(f"ServiceState values: {list(ServiceState)}")
```
