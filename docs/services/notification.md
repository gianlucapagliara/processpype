# Notification Service

The `NotificationService` sends notifications through multiple configurable channels. It supports console output and email, with the channel list extensible for future backends.

## Installation

Install the `notifications` extra for email support:

```bash
uv add "processpype[notifications]"
```

Console notifications work without any extra packages.

## Usage

```python
from processpype.services.notification.service import NotificationService
from processpype.services.notification.models import (
    NotificationConfiguration,
    NotificationChannel,
    NotificationLevel,
)

service = app.register_service(NotificationService)
service.configure(NotificationConfiguration(
    enabled_channels=[NotificationChannel.CONSOLE],
    default_level=NotificationLevel.INFO,
))
await app.start_service(service.name)

# Send a notification
await service.notify("Application started successfully")
```

## Configuration

```python
from processpype.services.notification.models import (
    NotificationConfiguration,
    NotificationChannel,
    NotificationLevel,
)

config = NotificationConfiguration(
    enabled_channels=[NotificationChannel.CONSOLE, NotificationChannel.EMAIL],
    default_level=NotificationLevel.INFO,
    # Email channel settings
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_user="sender@example.com",
    smtp_password="app-password",
    email_from="sender@example.com",
    email_to=["recipient@example.com"],
)
```

### YAML Configuration

```yaml
services:
  notification:
    enabled: true
    autostart: true
    enabled_channels:
      - console
    default_level: info
```

With email:

```yaml
services:
  notification:
    enabled: true
    enabled_channels:
      - console
      - email
    default_level: info
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_user: sender@example.com
    smtp_password: app-password
    email_from: sender@example.com
    email_to:
      - recipient@example.com
```

## Notification Channels

| Channel | Value | Description | Extra required |
|---------|-------|-------------|----------------|
| `CONSOLE` | `"console"` | Prints to stdout/logs | None |
| `EMAIL` | `"email"` | Sends via SMTP | `notifications` |
| `TELEGRAM` | `"telegram"` | Telegram bot (placeholder) | `notifications` |

## Notification Levels

| Level | Description |
|-------|-------------|
| `DEBUG` | Verbose diagnostic messages |
| `INFO` | Informational messages |
| `WARNING` | Warning conditions |
| `ERROR` | Error conditions |
| `CRITICAL` | Critical failures |

## Sending Notifications

### Direct message

```python
await service.notify("Service restarted")
await service.notify("Disk usage above 90%", level=NotificationLevel.WARNING)

# Send to specific channels only
await service.notify(
    "Critical failure",
    level=NotificationLevel.CRITICAL,
    channels=[NotificationChannel.EMAIL],
    metadata={"service": "database", "error": "connection timeout"},
)
```

### Using templates

Register a template once and reuse it:

```python
from processpype.services.notification.models import NotificationTemplate, NotificationLevel

service.register_template(NotificationTemplate(
    name="service_restart",
    template="Service {service_name} restarted after {attempts} attempts",
    default_level=NotificationLevel.WARNING,
))

await service.notify_with_template(
    "service_restart",
    context={"service_name": "database", "attempts": 3},
)
```

Built-in templates registered at startup:

- `service_status` --- `"Service {service_name} status changed to {status}"`
- `error` --- `"Error: {message}"`

## REST Endpoints

The notification service uses the default service router endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/notification` | Service status |
| `POST` | `/services/notification/start` | Start the service |
| `POST` | `/services/notification/stop` | Stop the service |
| `POST` | `/services/notification/configure` | Configure the service |
| `POST` | `/services/notification/configure_and_start` | Configure and start |

## Telegram Message Handling

If the Telegram channel is configured, you can add a handler for incoming messages:

```python
def handle_telegram_message(event) -> None:
    print(f"Received: {event.message.text}")

service.add_telegram_message_handler(handle_telegram_message)
```
