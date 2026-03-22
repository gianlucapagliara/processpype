# Docker

ProcessPype ships with a production-ready multi-stage Dockerfile and a `docker-compose.yml` for local development and testing.

## Dockerfile

The included `Dockerfile` uses a two-stage build:

**Builder stage** --- installs build dependencies, all Python packages, and the application using `uv`.

**Runtime stage** --- copies only the installed packages and application code into a minimal `python:3.13-slim` image. The application runs as a non-root user (`appuser`) and uses `tini` for proper signal handling.

```dockerfile
# Build stage
FROM python:3.13-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project
COPY . .
RUN uv sync --no-dev --extra all_py313

# Runtime stage
FROM python:3.13-slim as runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl tini && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app/processpype /app/processpype
COPY --from=builder /app/pyproject.toml /app/
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8000 APP_HOST=0.0.0.0 APP_PORT=8000 APP_ENV=production APP_DEBUG=false ENABLED_SERVICES=monitoring LOGFIRE_KEY=
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "processpype.main:app.api", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75", "--log-level", "info", "--timeout-graceful-shutdown", "10", "--no-access-log", "--use-colors"]
```

## Environment Variables

Configure the application via environment variables when running in Docker. The primary configuration mechanism is YAML files with `${ENV_VAR}` token replacement, but the following environment variables are recognized directly:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `"0.0.0.0"` | Bind host |
| `APP_PORT` | `"8000"` | Bind port |
| `APP_DEBUG` | `"false"` | Enable debug mode |
| `APP_ENV` | `"production"` | Environment name |
| `LOGFIRE_KEY` | (none) | Logfire API token |
| `ENABLED_SERVICES` | `""` | Comma-separated list of services to auto-register from the registry |

## Building the Image

```bash
# Build the image
docker build -t processpype:latest .

# Build with a specific target (builder or runtime)
docker build --target runtime -t processpype:latest .
```

## Running with Docker

```bash
# Run the application
docker run -p 8000:8000 \
  -e APP_ENV=production \
  -e ENABLED_SERVICES=monitoring \
  processpype:latest

# Run with Logfire enabled
docker run -p 8000:8000 \
  -e LOGFIRE_KEY=your-token \
  -e ENABLED_SERVICES=monitoring \
  processpype:latest
```

## Docker Compose

The included `docker-compose.yml` provides three service profiles:

### Development (`app`)

Mounts the local `processpype/` directory as a volume for hot-reloading during development:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
      - APP_TITLE=ProcessPype Dev
      - APP_ENV=development
      - APP_DEBUG=true
      - ENABLED_SERVICES=monitoring
      - LOGFIRE_KEY=
    volumes:
      - ./processpype:/app/processpype
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    stop_grace_period: 10s
```

```bash
docker compose up app
```

### Production (`app-prod`)

No volume mount, runs with `APP_ENV=production` and multiple services:

```yaml
services:
  app-prod:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8001:8000"
    environment:
      - APP_TITLE=ProcessPype Production
      - APP_ENV=production
      - APP_DEBUG=false
      - ENABLED_SERVICES=monitoring,clock
      - LOGFIRE_KEY=
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    stop_grace_period: 10s
```

```bash
docker compose up app-prod
```

### Testing (`test`)

Runs the test suite inside the builder stage:

```yaml
services:
  test:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder
    volumes:
      - .:/app
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
      - APP_ENV=test
      - APP_DEBUG=true
      - LOGFIRE_KEY=
    command: uv run pytest
```

```bash
docker compose run test
```

## Health Check

Both `app` and `app-prod` services include a health check that polls `http://localhost:8000/health`. Ensure your application responds to this endpoint, or adjust the health check URL to match your `api_prefix` and routing setup.

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

## Graceful Shutdown

`tini` is used as the container init process to properly forward `SIGTERM` and `SIGINT` signals to the Python process. The `ApplicationCreator` sets up signal handlers that trigger Uvicorn's graceful shutdown when these signals are received.

The `stop_grace_period` in docker-compose and `--timeout-graceful-shutdown` in Uvicorn control how long to wait for in-flight requests and services to stop before forceful termination.

## Custom Entry Point

To use a custom application class or register additional services at startup, create your own entry point instead of using `processpype.main`:

```python
# myapp/main.py
from processpype.creator import ApplicationCreator
from processpype.application import Application
from processpype import ProcessPypeConfig
from myapp.services import MyCustomService


class MyApplicationCreator(ApplicationCreator):
    @classmethod
    def get_application(cls, **kwargs) -> Application:
        config = ProcessPypeConfig(server={"host": "0.0.0.0", "port": 8080})
        app = Application(config)
        cls.app = app
        cls._setup_startup_callback()
        cls._setup_shutdown_callback()
        return app


app = MyApplicationCreator.get_application()
```

Then update the Dockerfile `CMD`:

```dockerfile
CMD ["python", "-m", "uvicorn", "myapp.main:app.api", "--host", "0.0.0.0", "--port", "8000"]
```
