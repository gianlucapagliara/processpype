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
│   ├── core/
│   │   ├── application.py         # Application class
│   │   ├── manager.py             # ApplicationManager
│   │   ├── models.py              # ServiceState, ServiceStatus, ApplicationStatus
│   │   ├── router.py              # ApplicationRouter
│   │   ├── system.py              # Timezone setup
│   │   ├── logfire.py             # Logging and Logfire integration
│   │   ├── configuration/
│   │   │   ├── models.py          # ConfigurationModel, ServiceConfiguration, ApplicationConfiguration
│   │   │   ├── manager.py         # ConfigurationManager
│   │   │   └── providers.py       # FileProvider, EnvProvider
│   │   └── service/
│   │       ├── service.py         # Service abstract base class
│   │       ├── manager.py         # ServiceManager abstract base class
│   │       └── router.py          # ServiceRouter
│   └── services/
│       ├── __init__.py            # Service registry helpers
│       ├── agent/                 # Agent service (requires agentspype)
│       ├── clock/                 # Clock service (wraps chronopype)
│       ├── database/              # Database service (SQLAlchemy)
│       ├── monitoring/
│       │   ├── system/            # System resource monitoring
│       │   ├── cloudwatch/        # AWS CloudWatch integration
│       │   └── cronitor/          # Cronitor integration
│       ├── notification/          # Notification service (console, email)
│       └── storage/               # Storage service (local, S3)
├── tests/
│   ├── conftest.py
│   └── ...
├── docs/                          # Documentation (mkdocs)
├── Dockerfile                     # Multi-stage production Dockerfile
├── docker-compose.yml             # Dev/prod/test compose profiles
└── pyproject.toml
```

## Adding a New Service

1. Create a directory under `processpype/services/your_service/`
2. Implement `config.py` (extend `ServiceConfiguration`)
3. Implement `manager.py` (extend `ServiceManager`, implement `start()` and `stop()`)
4. Implement `service.py` (extend `Service`, implement `create_manager()`)
5. Optionally implement `router.py` for custom endpoints
6. Decorate with `@register_service_class` for dynamic registration
7. Add documentation under `docs/services/`
8. Add tests under `tests/services/your_service/`

Example skeleton:

```python
# processpype/services/my_service/config.py
from pydantic import Field
from processpype.core.configuration.models import ServiceConfiguration

class MyServiceConfiguration(ServiceConfiguration):
    host: str = Field(default="localhost")
    port: int = Field(default=9090)


# processpype/services/my_service/manager.py
from processpype.core.service.manager import ServiceManager

class MyServiceManager(ServiceManager):
    async def start(self) -> None:
        self.logger.info("MyService started")

    async def stop(self) -> None:
        self.logger.info("MyService stopped")


# processpype/services/my_service/service.py
from processpype.services import register_service_class
from processpype.core.service.service import Service
from .config import MyServiceConfiguration
from .manager import MyServiceManager

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
