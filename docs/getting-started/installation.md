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
| [logfire](https://logfire.pydantic.dev/) | >= 4.16 | Structured logging and observability |
| [pyyaml](https://pyyaml.org/) | >= 6.0.2 | YAML configuration files |
| [eventspype](https://github.com/gianlucapagliara/eventspype) | >= 1.1.0 | Event publication framework |
| [psutil](https://psutil.readthedocs.io/) | >= 6.1.1 | System resource monitoring |
| [pytz](https://pythonhosted.org/pytz/) | >= 2024.2 | Timezone management |
| [httpx](https://www.python-httpx.org/) | >= 0.28.1 | Async HTTP client |

## Verify Installation

```python
from processpype.core.application import Application
from processpype.core.models import ServiceState

print("processpype installed successfully")
print(f"ServiceState values: {list(ServiceState)}")
```
