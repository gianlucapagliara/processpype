# Communications

The communications module provides a backend-agnostic messaging layer for sending and receiving messages. Outgoing messages are routed by label to one or more backends (Telegram, Email, or custom). Incoming messages from backends that support receiving are published as eventspype events, making them available to any subscriber in your application.

## Architecture

```
                        ┌──────────────────────────┐
                        │  CommunicationDispatcher  │
                        └────────┬─────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
     ┌────────▼───────┐  ┌──────▼────────┐  ┌───────▼───────┐
     │    Telegram     │  │     Email     │  │    Custom     │
     │   Communicator  │  │  Communicator │  │  Communicator │
     └────────┬────────┘  └───────────────┘  └───────────────┘
              │
   ┌──────────┴──────────┐
   │  Outgoing           │  Incoming
   │  label routing      │  eventspype events
   │  → send to chats    │  → publish IncomingMessage
   └─────────────────────┘
```

**Outgoing flow:** Your code creates an `OutgoingMessage` with a label. The dispatcher finds all backends registered for that label and calls `send()` on each.

**Incoming flow:** Backends that support receiving (e.g. Telegram) forward messages to the dispatcher, which publishes them as eventspype events. Any part of your application can subscribe.

## Configuration

Enable communications and declare backends under the `communications` key in your YAML config:

```yaml
communications:
  enabled: true
  backends:
    my_telegram:
      type: telegram
      api_id: ${TELEGRAM_API_ID}
      api_hash: ${TELEGRAM_API_HASH}
      token: ${TELEGRAM_BOT_TOKEN}
      labels:
        - default
        - alerts
      listen_to_commands: true
      chats:
        default:
          chat_id: "-1001234567890"
          active: true
        alerts:
          chat_id: "-1009876543210"
          topic_id: 42
          command_authorized: true
          active: true

    my_email:
      type: email
      host: smtp.example.com
      port: 587
      username: ${SMTP_USER}
      password: ${SMTP_PASS}
      from_address: noreply@example.com
      start_tls: true
      default_recipients:
        - ops@example.com
      labels:
        - alerts
```

### Top-level fields

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Enable the communication system |
| `backends` | `{}` | Named backend instances |

### Backend base fields

Every backend inherits these fields from `CommunicatorBackendConfig`:

| Field | Default | Description |
|-------|---------|-------------|
| `type` | --- | Backend type: `telegram`, `email`, or a custom registered name |
| `enabled` | `true` | Whether this backend is active |
| `labels` | `["default"]` | Labels this backend handles |

Labels connect outgoing messages to backends. A message with `label="alerts"` is sent to every backend whose `labels` list includes `"alerts"`.

## Sending Messages

Create an `OutgoingMessage` and emit it through the dispatcher:

```python
from processpype.communications import OutgoingMessage, emit_message

msg = OutgoingMessage(
    message="Deployment completed successfully",
    label="default",
    source="deploy-service",
    severity="info",
)
await emit_message(msg)
```

### OutgoingMessage fields

| Field | Default | Description |
|-------|---------|-------------|
| `message` | --- | The message text |
| `label` | `"default"` | Routing label (must match a backend's labels) |
| `source` | `None` | Identifier of the sender (for logging/display) |
| `severity` | `"info"` | One of `debug`, `info`, `warning`, `error`, `critical` |
| `metadata` | `{}` | Arbitrary data passed to backends |
| `subject` | `None` | Subject line (used by email backend) |

### Label routing

A single message can reach multiple backends if they share the same label:

```python
# Both my_telegram and my_email are registered for "alerts"
await emit_message(OutgoingMessage(
    message="Database connection lost",
    label="alerts",
    severity="critical",
    subject="DB Alert",  # used by email backend
))
```

If no backend is registered for a label, the message is silently dropped and a debug log is emitted.

### Using the dispatcher directly

For more control, access the dispatcher instance:

```python
from processpype.communications import get_dispatcher

dispatcher = get_dispatcher()
await dispatcher.emit(message)
```

## Receiving Messages

Backends that support receiving (currently Telegram) publish incoming messages as eventspype events. Subscribe to them through the dispatcher's `incoming_publisher`.

### IncomingMessage fields

| Field | Default | Description |
|-------|---------|-------------|
| `text` | --- | The message text |
| `sender` | `None` | Sender username |
| `sender_id` | `None` | Sender identifier |
| `chat_label` | `"default"` | Label of the chat that received the message |
| `backend_name` | `""` | Name of the backend that received it |
| `timestamp` | `None` | Message timestamp |
| `metadata` | `{}` | Backend-specific metadata |
| `raw_event` | `None` | Original backend event (excluded from serialization) |

### Subscribing with eventspype

The dispatcher exposes an `incoming_publisher` that you can subscribe to using any eventspype subscriber:

```python
from eventspype.subscribers import FunctionalEventSubscriber
from processpype.communications import get_dispatcher, IncomingMessage

dispatcher = get_dispatcher()

# Simple functional subscriber
subscriber = FunctionalEventSubscriber(
    name="my_handler",
    publication=dispatcher.incoming_publication,
)

@subscriber.on_event
async def handle_message(message: IncomingMessage) -> None:
    print(f"[{message.backend_name}] {message.sender}: {message.text}")

subscriber.subscribe(dispatcher.incoming_publisher)
```

### TrackingEventSubscriber

Use `TrackingEventSubscriber` to keep a log of received messages:

```python
from eventspype.subscribers import TrackingEventSubscriber

tracker = TrackingEventSubscriber(
    name="message_tracker",
    publication=dispatcher.incoming_publication,
)
tracker.subscribe(dispatcher.incoming_publisher)

# Later, inspect received messages
for event in tracker.events:
    print(event.data.text)
```

### QueueEventSubscriber

Use `QueueEventSubscriber` to bridge synchronous event delivery to async processing:

```python
from eventspype.subscribers import QueueEventSubscriber

queue_sub = QueueEventSubscriber(
    name="message_queue",
    publication=dispatcher.incoming_publication,
)
queue_sub.subscribe(dispatcher.incoming_publisher)

# Consume from the queue in an async task
async def process_messages():
    while True:
        event = await queue_sub.get()
        await handle(event.data)
```

This is the recommended pattern when your handler performs async I/O, since the dispatcher's event delivery is synchronous.

## Built-in Backends

### Telegram

The Telegram backend uses Telethon and supports both sending and receiving. Install it with:

```bash
pip install processpype[telegram]
```

#### Configuration

```yaml
backends:
  my_telegram:
    type: telegram
    api_id: ${TELEGRAM_API_ID}
    api_hash: ${TELEGRAM_API_HASH}
    token: ${TELEGRAM_BOT_TOKEN}
    session_string: ""
    listen_to_commands: false
    labels:
      - default
    chats:
      default:
        chat_id: "-1001234567890"
        active: true
      alerts:
        chat_id: "-1001234567890"
        topic_id: 42
        command_authorized: true
        active: true
```

| Field | Default | Description |
|-------|---------|-------------|
| `api_id` | --- | Telegram API ID |
| `api_hash` | --- | Telegram API hash |
| `token` | --- | Bot token |
| `session_string` | `""` | Persistent session string for authentication |
| `listen_to_commands` | `false` | Enable incoming message handling |
| `chats` | `{}` | Chat configurations keyed by label |

Each chat entry (`TelegramChatConfig`):

| Field | Default | Description |
|-------|---------|-------------|
| `chat_id` | --- | Chat or channel identifier |
| `topic_id` | `None` | Forum topic ID (for supergroup topics) |
| `command_authorized` | `false` | Accept incoming commands from this chat |
| `active` | `true` | Whether this chat destination is active |

#### Sending behavior

Outgoing messages are queued internally and drained by a background task. Long messages are automatically split into chunks of 30 lines. Failed sends are retried up to 3 times with exponential backoff.

#### Receiving behavior

When `listen_to_commands` is `true`, the backend listens for all new messages on Telegram. Only messages from chats with `command_authorized: true` are forwarded to the dispatcher. The `topic_id` field narrows authorization to a specific forum topic within a supergroup.

### Email

The Email backend uses aiosmtplib and is send-only. Install it with:

```bash
pip install processpype[email]
```

#### Configuration

```yaml
backends:
  my_email:
    type: email
    host: smtp.example.com
    port: 587
    username: ${SMTP_USER}
    password: ${SMTP_PASS}
    from_address: noreply@example.com
    use_tls: true
    start_tls: false
    default_recipients:
      - ops@example.com
    labels:
      - alerts
```

| Field | Default | Description |
|-------|---------|-------------|
| `host` | `"localhost"` | SMTP server hostname |
| `port` | `587` | SMTP port |
| `username` | `""` | SMTP username |
| `password` | `""` | SMTP password |
| `from_address` | --- | Sender email address |
| `use_tls` | `true` | Connect with TLS |
| `start_tls` | `false` | Upgrade to TLS via STARTTLS after connecting (for port 587) |
| `default_recipients` | `[]` | Default recipient addresses |

#### Sending behavior

Recipients can be set per-message via `metadata["recipients"]`, or fall back to `default_recipients` from the config. The `subject` field of `OutgoingMessage` sets the email subject; if omitted, a default subject is generated from the severity level.

```python
await emit_message(OutgoingMessage(
    message="Disk usage at 95%",
    label="alerts",
    severity="warning",
    subject="Disk Alert",
    metadata={"recipients": ["admin@example.com"]},
))
```

The backend automatically reconnects if the SMTP connection is lost.

## Custom Backends

Implement the `Communicator` abstract base class to create a custom backend:

```python
from processpype.communications.base import Communicator
from processpype.communications.models import OutgoingMessage
from processpype.config.models import CommunicatorBackendConfig


class SlackCommunicator(Communicator):
    def __init__(self, name: str, config: CommunicatorBackendConfig) -> None:
        super().__init__(name, config)
        self._webhook_url = config.extra_fields.get("webhook_url", "")

    async def start(self) -> None:
        # Initialize client, open connections
        self._started = True

    async def stop(self) -> None:
        # Clean up resources
        self._started = False

    async def send(self, message: OutgoingMessage) -> None:
        # Send message via Slack webhook
        ...
```

To support receiving, override `supports_receiving` and call `self._on_incoming()` when a message arrives:

```python
    @property
    def supports_receiving(self) -> bool:
        return True

    async def start(self) -> None:
        self._started = True
        # Start listening for messages, then for each:
        # self._on_incoming(IncomingMessage(text=..., backend_name=self._name))
```

### Registering a custom backend

Register your backend so it can be referenced by type name in configuration:

```python
from processpype.communications.backends import register_backend

register_backend("slack", lambda name, config: SlackCommunicator(name, config))
```

Then use it in YAML:

```yaml
communications:
  enabled: true
  backends:
    my_slack:
      type: slack
      labels:
        - default
      webhook_url: ${SLACK_WEBHOOK_URL}
```

## Initialization

The communications system is initialized automatically by `Application.create()` when `communications.enabled` is `true`. You can also initialize it manually:

```python
from processpype.communications import init_communications

await init_communications(config.communications)
```

This creates backends from configuration, registers them with the dispatcher, and starts all backends.

## Next Steps

- [Configuration](configuration.md) --- Environment variable substitution and YAML config details
- [Services](services.md) --- Integrate communications into your service lifecycle
