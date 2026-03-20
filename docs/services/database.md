# Database Service

The `DatabaseService` provides async SQL database access using SQLAlchemy. It supports SQLite and PostgreSQL engines.

## Installation

Install the `database` extra:

```bash
uv add "processpype[database]"
# Python 3.13 only (no asyncpg):
uv add "processpype[database_py313]"
```

## Usage

```python
from processpype.services.database.service import DatabaseService
from processpype.services.database.models import DatabaseConfiguration

service = app.register_service(DatabaseService)
service.configure(DatabaseConfiguration(
    engine="sqlite",
    connection_string="sqlite+aiosqlite:///./app.db",
))
await app.start_service(service.name)
```

## Configuration

```python
from processpype.services.database.models import DatabaseConfiguration

config = DatabaseConfiguration(
    engine="sqlite",                              # "sqlite" or "postgres"
    connection_string="sqlite+aiosqlite:///./app.db",
    pool_size=5,                                  # connection pool size
    max_overflow=10,                              # additional connections allowed
    pool_timeout=30,                              # seconds to wait for a connection
    echo=False,                                   # log SQL statements
)
```

### YAML Configuration

```yaml
services:
  database:
    enabled: true
    autostart: true
    engine: sqlite
    connection_string: "sqlite+aiosqlite:///./data/app.db"
    pool_size: 5
    max_overflow: 10
    pool_timeout: 30
    echo: false
```

### PostgreSQL

```yaml
services:
  database:
    enabled: true
    engine: postgres
    connection_string: "postgresql+asyncpg://user:password@localhost:5432/mydb"
    pool_size: 10
    max_overflow: 20
```

## Executing Queries

Once the service is running, use the high-level methods on `DatabaseService`:

```python
# Execute a statement (INSERT, UPDATE, DELETE)
await service.execute(
    "INSERT INTO users (name, email) VALUES (:name, :email)",
    name="Alice",
    email="alice@example.com",
)

# Fetch a single row
row = await service.fetch_one(
    "SELECT * FROM users WHERE email = :email",
    email="alice@example.com",
)
if row:
    print(row["name"])

# Fetch multiple rows
rows = await service.fetch_all(
    "SELECT * FROM users WHERE active = :active",
    active=True,
)
```

## Transactions

Use `begin_transaction()` to wrap multiple queries in a transaction. The transaction commits on successful exit and rolls back on exception:

```python
async with await service.begin_transaction() as txn:
    await service.execute("INSERT INTO accounts (name) VALUES (:name)", name="Bob")
    await service.execute("UPDATE balances SET amount = amount - 100 WHERE account = :id", id=1)
    # commits automatically on exit
    # rolls back automatically if an exception is raised
```

## REST Endpoints

The database service uses the default `ServiceRouter` endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/database` | Service status |
| `POST` | `/services/database/start` | Start the service |
| `POST` | `/services/database/stop` | Stop the service |
| `POST` | `/services/database/configure` | Configure the service |
| `POST` | `/services/database/configure_and_start` | Configure and start |

## Configuration Reference

| Field | Default | Description |
|-------|---------|-------------|
| `engine` | `"sqlite"` | Database engine: `"sqlite"` or `"postgres"` |
| `connection_string` | `"sqlite:///data/database.db"` | SQLAlchemy connection URL |
| `pool_size` | `5` | Number of connections to maintain |
| `max_overflow` | `10` | Extra connections allowed above `pool_size` |
| `pool_timeout` | `30` | Seconds to wait for a connection from the pool |
| `echo` | `False` | Log all SQL statements to stdout |
