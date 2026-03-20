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

## Optional Extras

ProcessPype ships with a minimal core. Install extras for specific service types:

| Extra | Packages | Use case |
|-------|----------|----------|
| `agents` | agentspype | Agent-based services |
| `storage` | boto3 | AWS S3 storage backend |
| `database` | sqlalchemy, aiosqlite, asyncpg | SQLite and PostgreSQL |
| `database_py313` | sqlalchemy, aiosqlite | SQLite only (Python 3.13 compatible) |
| `notifications` | telethon, aiosmtplib | Telegram and email notifications |
| `monitoring` | cronitor, boto3 | Cronitor and CloudWatch monitoring |
| `all` | all of the above | Full installation |
| `all_py313` | all except asyncpg | Full installation for Python 3.13 |

```bash
# Install with database support
uv add "processpype[database]"

# Install with storage and monitoring
uv add "processpype[storage,monitoring]"

# Install everything
uv add "processpype[all_py313]"
```

## Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| [pydantic](https://docs.pydantic.dev/) | >= 2.10.4 | Configuration and data validation |
| [fastapi](https://fastapi.tiangolo.com/) | >= 0.115.6 | REST API framework |
| [uvicorn](https://www.uvicorn.org/) | >= 0.34.0 | ASGI server |
| [logfire](https://logfire.pydantic.dev/) | >= 4.16 | Structured logging and observability |
| [pyyaml](https://pyyaml.org/) | >= 6.0.2 | YAML configuration files |
| [eventspype](https://github.com/gianlucapagliara/eventspype) | >= 1.0.3 | Event publication framework |
| [chronopype](https://github.com/gianlucapagliara/chronopype) | >= 0.2.7 | Clock and time management |
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
