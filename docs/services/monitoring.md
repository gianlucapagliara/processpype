# Monitoring Services

ProcessPype includes several monitoring services for system resource tracking and external monitoring integrations.

## System Monitoring Service

`SystemMonitoringService` collects CPU, memory, and disk metrics from the host system using `psutil`.

### Installation

System monitoring is included in the core package — `psutil` is a core dependency.

### Usage

```python
from processpype.services.monitoring.system.service import SystemMonitoringService

service = app.register_service(SystemMonitoringService)
await app.start_service(service.name)
```

The service starts without configuration (`requires_configuration()` returns `False`).

### Configuration

```python
from processpype.services.monitoring.system.config import SystemMonitoringConfiguration

service.configure(SystemMonitoringConfiguration(
    interval=5.0,          # collection interval in seconds
    collect_cpu=True,      # collect CPU metrics
    collect_memory=True,   # collect memory metrics
    collect_disk=True,     # collect disk metrics
    disk_path="/",         # path to monitor for disk usage
))
```

### YAML Configuration

```yaml
services:
  system-monitoring:
    enabled: true
    autostart: true
    interval: 5.0
    collect_cpu: true
    collect_memory: true
    collect_disk: true
    disk_path: /
```

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/system-monitoring` | Service status |
| `GET` | `/services/system-monitoring/metrics` | Current system metrics |
| `POST` | `/services/system-monitoring/start` | Start collection |
| `POST` | `/services/system-monitoring/stop` | Stop collection |
| `POST` | `/services/system-monitoring/configure` | Configure the service |

### Metrics Response

```json
{
  "cpu_percent": 12.5,
  "memory_percent": 45.2,
  "memory_used_mb": 3686.4,
  "memory_total_mb": 8192.0,
  "disk_percent": 62.1,
  "disk_used_gb": 124.2,
  "disk_total_gb": 200.0
}
```

### Service Name

The system monitoring service defaults to the name `"system-monitoring"` (set explicitly in `__init__`).

---

## Cronitor Monitoring

The `cronitor` monitoring service integrates with [Cronitor](https://cronitor.io/) for job and heartbeat monitoring.

### Installation

```bash
uv add "processpype[monitoring]"
```

### Location

`processpype/services/monitoring/cronitor/`

### Usage

Configure your Cronitor API key and monitor slugs in YAML:

```yaml
services:
  cronitor:
    enabled: true
    api_key: your-cronitor-api-key
    monitor_slug: my-job-monitor
```

---

## CloudWatch Monitoring

The `cloudwatch` monitoring service publishes custom metrics to AWS CloudWatch.

### Installation

```bash
uv add "processpype[monitoring]"
```

### Location

`processpype/services/monitoring/cloudwatch/`

### Usage

```yaml
services:
  cloudwatch:
    enabled: true
    namespace: MyApp/Metrics
    region: us-east-1
```

---

## Enabling Monitoring in Docker

```bash
docker run -p 8000:8000 \
  -e ENABLED_SERVICES=system-monitoring \
  processpype:latest
```

The default `Dockerfile` and `docker-compose.yml` both set `ENABLED_SERVICES=monitoring` which starts the system monitoring service automatically.
