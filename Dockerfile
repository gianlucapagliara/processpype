# Build stage
FROM python:3.13-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy only the files needed for installation
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN /root/.local/bin/poetry config virtualenvs.create false \
    && /root/.local/bin/poetry install --no-interaction --no-ansi --no-root --only main

# Copy the rest of the application
COPY . .

# Install the application
RUN /root/.local/bin/poetry install --no-interaction --no-ansi -E all_py313

# Runtime stage
FROM python:3.13-slim as runtime

WORKDIR /app

# Install curl for healthcheck and tini for proper signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app/processpype /app/processpype
COPY --from=builder /app/pyproject.toml /app/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Set default environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_ENV=production \
    APP_DEBUG=false \
    ENABLED_SERVICES=monitoring \
    LOGFIRE_KEY=

# Expose the application port
EXPOSE 8000

# Command to run the application with tini as init process
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "processpype.main:app.api", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75", "--log-level", "info", "--timeout-graceful-shutdown", "10", "--no-access-log", "--use-colors"]