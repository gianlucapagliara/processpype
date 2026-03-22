# Contributing

## Development Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/gianlucapagliara/processpype.git
cd processpype
uv sync
```

## Running Tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=processpype --cov-report=term-missing
```

## Code Quality

### Linting and Formatting

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Type Checking

```bash
uv run mypy processpype
```

The project uses MyPy in strict mode. All public functions must have type annotations. Test files are excluded from strict checking.

### Pre-commit Hooks

Install hooks to run checks automatically before each commit:

```bash
uv run pre-commit install
```

Run all hooks manually:

```bash
uv run pre-commit run --all-files
```

## Project Structure

```
processpype/
├── processpype/
│   ├── __init__.py
│   ├── main.py                    # Default ASGI entry point
│   ├── creator.py                 # ApplicationCreator helper
│   ├── application.py             # Core Application class
│   ├── app_manager.py             # ApplicationManager
│   ├── config/
│   │   ├── models.py              # ProcessPypeConfig, AppConfig, ServerConfig, etc.
│   │   ├── manager.py             # load_config() function
│   │   └── providers.py           # ConfigurationProvider, FileProvider
│   ├── service/
│   │   ├── base.py                # Service abstract base class
│   │   ├── manager.py             # ServiceManager abstract base class
│   │   ├── models.py              # ServiceState, ServiceStatus, ApplicationStatus
│   │   ├── naming.py              # derive_service_name()
│   │   └── registry.py            # register_service_class, get_service_class
│   ├── server/
│   │   ├── app_router.py          # ApplicationRouter
│   │   └── service_router.py      # ServiceRouter
│   ├── observability/
│   │   ├── setup.py               # init_observability()
│   │   ├── logging/               # Logging setup, formatters, filters
│   │   └── tracing/               # OpenTelemetry tracing setup
│   ├── environment/
│   │   └── system.py              # setup_environment()
│   └── examples/
│       ├── __init__.py
│       ├── hello.py               # HelloService — minimal, no config
│       ├── counter.py             # CounterService — config + custom router
│       └── ticker.py              # TickerService — background async loop
├── tests/
│   ├── conftest.py
│   └── ...
├── docs/                          # Documentation (mkdocs)
├── Dockerfile                     # Multi-stage production Dockerfile
├── docker-compose.yml             # Dev/prod/test compose profiles
└── pyproject.toml
```

## Creating a New Service

Use the example services in `processpype/examples/` as templates:

- **HelloService** (`hello.py`) --- Minimal service, no configuration needed. Start here for the simplest case.
- **CounterService** (`counter.py`) --- Service with custom `ServiceConfiguration`, validation, and a custom `ServiceRouter` with domain-specific endpoints.
- **TickerService** (`ticker.py`) --- Service with a background async loop and graceful shutdown.

To create a new service:

1. Create a new module (e.g., `myapp/services/my_service.py`)
2. Define a `ServiceConfiguration` subclass if your service needs configuration
3. Define a `ServiceManager` subclass with `start()` and `stop()` methods
4. Define a `Service` subclass with `create_manager()` and `configuration_class`
5. Optionally subclass `ServiceRouter` for custom HTTP endpoints
6. Optionally decorate with `@register_service_class` for dynamic registration via the REST API
7. Add tests

Example skeleton:

```python
from pydantic import Field
from processpype.config.models import ServiceConfiguration
from processpype.service.manager import ServiceManager
from processpype.service.base import Service
from processpype.service.registry import register_service_class


class MyServiceConfiguration(ServiceConfiguration):
    host: str = Field(default="localhost")
    port: int = Field(default=9090)


class MyServiceManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("MyService started")

    async def stop(self) -> None:
        self.logger.info("MyService stopped")


@register_service_class
class MyService(Service):
    configuration_class = MyServiceConfiguration

    def create_manager(self) -> MyServiceManager:
        return MyServiceManager(self.logger)
```

## Building Documentation

Install the docs dependency group and build:

```bash
uv sync --group docs
uv run mkdocs build --strict
```

Serve locally:

```bash
uv run mkdocs serve
```

## Releasing

Releases are tagged on the `main` branch. CI publishes to PyPI automatically on tagged releases.

## CI/CD

- **CI** runs on every push and PR to `main`: linting (ruff), type checking (mypy), and tests with coverage
- **Docs** deploy to GitHub Pages on every push to `main`
- **Publish** runs on GitHub release creation: builds and publishes to PyPI
