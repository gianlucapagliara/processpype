# Communications API Reference

`processpype.communications`

## OutgoingMessage

```python
class OutgoingMessage(BaseModel):
    """A message to send via a communicator backend."""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | `str` | (required) | The message body |
| `label` | `str` | `"default"` | Routing label (min length 1) |
| `source` | `str \| None` | `None` | Identifier of the component that produced the message |
| `severity` | `MessageSeverity` | `MessageSeverity.INFO` | Severity level |
| `metadata` | `dict[str, Any]` | `{}` | Arbitrary key-value metadata |
| `subject` | `str \| None` | `None` | Optional subject line (used by email backend) |

### Example

```python
from processpype.communications.models import OutgoingMessage, MessageSeverity

msg = OutgoingMessage(
    message="Deployment complete",
    label="alerts",
    source="deploy-service",
    severity=MessageSeverity.WARNING,
)
```

## IncomingMessage

```python
class IncomingMessage(BaseModel):
    """A message received from a communicator backend (published as event)."""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | `str` | (required) | Message text |
| `sender` | `str \| None` | `None` | Human-readable sender name |
| `sender_id` | `str \| None` | `None` | Backend-specific sender identifier |
| `chat_label` | `str` | `"default"` | Label of the chat that received the message |
| `backend_name` | `str` | `""` | Name of the communicator that received it |
| `timestamp` | `datetime \| None` | `None` | Message timestamp |
| `metadata` | `dict[str, Any]` | `{}` | Arbitrary key-value metadata |
| `raw_event` | `Any` | `None` | Backend-specific raw event object (excluded from serialization) |

## MessageSeverity

```python
class MessageSeverity(StrEnum):
```

A `StrEnum` representing message severity levels.

| Member | Value |
|--------|-------|
| `DEBUG` | `"debug"` |
| `INFO` | `"info"` |
| `WARNING` | `"warning"` |
| `ERROR` | `"error"` |
| `CRITICAL` | `"critical"` |

## MessageHandler

```python
MessageHandler = Callable[[IncomingMessage], Awaitable[None]]
```

Type alias for async functions that handle incoming messages.

## Communicator

`processpype.communications.base.Communicator`

```python
class Communicator(ABC):
    """Abstract base for communication backends."""
```

### Constructor

```python
def __init__(self, name: str, config: CommunicatorBackendConfig) -> None
```

**Parameters:**

- `name` --- Unique name for this communicator instance
- `config` --- Backend configuration

### Properties

#### `name`

```python
@property
def name(self) -> str
```

The communicator instance name.

---

#### `is_started`

```python
@property
def is_started(self) -> bool
```

`True` after `start()` has completed successfully.

---

#### `supports_receiving`

```python
@property
def supports_receiving(self) -> bool
```

`False` by default. Backends that can receive messages should override this to return `True`.

### Methods

#### `set_incoming_handler`

```python
def set_incoming_handler(self, handler: Callable[[IncomingMessage], None]) -> None
```

Set by the dispatcher to route incoming messages to the event publisher. The handler is synchronous --- eventspype's `EventPublisher.publish()` dispatches synchronously. For async processing, use eventspype's `QueueEventSubscriber` to bridge to an async consumer.

### Abstract Methods

#### `start`

```python
async def start(self) -> None
```

Initialize and connect the backend. Must set `self._started = True` on success.

---

#### `stop`

```python
async def stop(self) -> None
```

Disconnect and clean up resources. Must set `self._started = False`.

---

#### `send`

```python
async def send(self, message: OutgoingMessage) -> None
```

Send an outgoing message through the backend.

## NoOpCommunicator

`processpype.communications.base.NoOpCommunicator`

```python
class NoOpCommunicator(Communicator):
    """Silent fallback when a backend is unavailable."""
```

A no-operation communicator returned when a backend dependency is missing or the backend type is unknown. All methods are no-ops. Always reports `is_started = True` and `supports_receiving = False`.

## CommunicationDispatcher

`processpype.communications.dispatcher.CommunicationDispatcher`

```python
class CommunicationDispatcher:
    """Routes OutgoingMessage to registered Communicator backends by label."""
```

Outgoing messages are routed by their `label` field to all communicators registered for that label. Incoming messages from backends are published as eventspype events.

### Constructor

```python
def __init__(self) -> None
```

Creates an empty dispatcher with no registered communicators.

### Properties

#### `incoming_publisher`

```python
@property
def incoming_publisher(self) -> EventPublisher
```

The eventspype `EventPublisher` for incoming messages. Subscribe to this publisher to receive `IncomingMessage` events from all backends.

### Methods

#### `register`

```python
def register(
    self, communicator: Communicator, labels: list[str] | None = None
) -> None
```

Register a communicator backend for the given labels. If `labels` is `None`, defaults to `["default"]`. If the communicator supports receiving, its incoming handler is automatically wired to the event publisher.

**Parameters:**

- `communicator` --- The communicator instance to register
- `labels` --- Labels this communicator handles

---

#### `unregister`

```python
def unregister(self, name: str) -> None
```

Remove a communicator backend by name. Cleans up all label mappings.

---

#### `emit`

```python
async def emit(self, message: OutgoingMessage) -> None
```

Send a message to all communicators registered for `message.label`. Backends that are not started are skipped. Exceptions from individual backends are logged but do not prevent delivery to remaining backends.

---

#### `start_all`

```python
async def start_all(self) -> None
```

Start all registered communicators. Exceptions from individual backends are logged but do not prevent starting remaining backends.

---

#### `stop_all`

```python
async def stop_all(self) -> None
```

Stop all registered communicators. Exceptions from individual backends are logged but do not prevent stopping remaining backends.

## Module Functions

`processpype.communications.dispatcher`

### `get_dispatcher`

```python
def get_dispatcher() -> CommunicationDispatcher
```

Get or create the global `CommunicationDispatcher` singleton. Thread-safe.

---

### `emit_message`

```python
async def emit_message(message: OutgoingMessage) -> None
```

Convenience function that emits a message via the global dispatcher.

```python
from processpype.communications.dispatcher import emit_message
from processpype.communications.models import OutgoingMessage

await emit_message(OutgoingMessage(message="Hello", label="alerts"))
```

---

### `init_communications`

`processpype.communications.setup.init_communications`

```python
async def init_communications(config: CommunicationsConfig) -> None
```

Initialize the communication subsystem from application configuration. For each enabled backend in `config.backends`, creates a communicator via `create_communicator()`, registers it with the global dispatcher, and starts all communicators.

Does nothing if `config.enabled` is `False`.

## Backend Factory

`processpype.communications.backends`

### `create_communicator`

```python
def create_communicator(name: str, config: CommunicatorBackendConfig) -> Communicator
```

Create a `Communicator` instance from a backend configuration. Checks the plugin registry first, then falls back to built-in types (`"telegram"`, `"email"`). Returns a `NoOpCommunicator` if the required dependency is not installed or the type is unknown.

**Parameters:**

- `name` --- Instance name for the communicator
- `config` --- Backend configuration (must include a `type` field)

**Returns:** A `Communicator` instance

---

### `register_backend`

```python
def register_backend(type_name: str, factory: Callable[..., Communicator]) -> None
```

Register a custom communicator backend factory. The factory must accept `(name: str, config: CommunicatorBackendConfig)` and return a `Communicator`.

```python
from processpype.communications.backends import register_backend

def my_factory(name, config):
    return MyCustomCommunicator(name, config)

register_backend("my_backend", my_factory)
```

## TelegramCommunicator

`processpype.communications.backends.telegram.TelegramCommunicator`

```python
class TelegramCommunicator(Communicator):
    """Telegram bot communicator with send and optional receive support."""
```

Requires the `telethon` package (`pip install processpype[telegram]`).

### Constructor

```python
def __init__(self, name: str, config: TelegramCommunicatorConfig) -> None
```

**Parameters:**

- `name` --- Communicator instance name
- `config` --- Telegram-specific configuration

### Configuration

`TelegramCommunicatorConfig` extends `CommunicatorBackendConfig`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_id` | `int` | (required) | Telegram API ID |
| `api_hash` | `str` | (required) | Telegram API hash |
| `token` | `str` | (required) | Bot token |
| `session_string` | `str` | `""` | Session string for auth persistence |
| `listen_to_commands` | `bool` | `False` | Enable incoming message handling |
| `chats` | `dict[str, TelegramChatConfig]` | `{}` | Chat configurations keyed by label |

`TelegramChatConfig`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `chat_id` | `str` | (required) | Chat/channel identifier |
| `topic_id` | `int \| None` | `None` | Forum topic ID |
| `command_authorized` | `bool` | `False` | Accept commands from this chat |
| `active` | `bool` | `True` | Whether this chat is active |

### Behavior

- **Sending:** Messages are queued internally and drained by a background task to respect Telegram rate limits. Long messages are split into chunks of 30 lines. Failed sends are retried up to 3 times with exponential backoff. Messages are routed to the chat configured for the message's label, falling back to the `"default"` chat.
- **Receiving:** When `listen_to_commands` is `True`, `supports_receiving` returns `True` and a persistent file session is used. Incoming messages are filtered by authorization (`command_authorized` on the matching chat config) and published as `IncomingMessage` events via the dispatcher.
- **Sessions:** Uses `StringSession` (ephemeral) for send-only mode. If `session_string` is provided, uses it for auth persistence. If `listen_to_commands` is enabled without a session string, uses a persistent file session.

## EmailCommunicator

`processpype.communications.backends.email.EmailCommunicator`

```python
class EmailCommunicator(Communicator):
    """Async email communicator (send-only)."""
```

Requires the `aiosmtplib` package (`pip install processpype[email]`).

### Constructor

```python
def __init__(self, name: str, config: EmailCommunicatorConfig) -> None
```

**Parameters:**

- `name` --- Communicator instance name
- `config` --- Email-specific configuration

### Configuration

`EmailCommunicatorConfig` extends `CommunicatorBackendConfig`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | `str` | `"localhost"` | SMTP host |
| `port` | `int` | `587` | SMTP port |
| `username` | `str` | `""` | SMTP username |
| `password` | `str` | `""` | SMTP password |
| `from_address` | `str` | (required) | Sender email address |
| `use_tls` | `bool` | `True` | Use TLS |
| `start_tls` | `bool` | `False` | Use STARTTLS after connecting (for port 587) |
| `default_recipients` | `list[str]` | `[]` | Default recipient addresses |

### Behavior

- **Send-only:** `supports_receiving` always returns `False`.
- **Recipients:** Determined by `message.metadata["recipients"]` if present, otherwise falls back to `config.default_recipients`. If neither is set, the message is skipped with a warning.
- **Subject:** Uses `message.subject` if set, otherwise generates `[SEVERITY] Notification`.
- **Reconnection:** Automatically reconnects on `SMTPServerDisconnected` or `ConnectionError` and retries the send.

## CommunicationsConfig

`processpype.config.models.CommunicationsConfig`

```python
class CommunicationsConfig(ConfigurationModel):
    """Top-level communications configuration."""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable the communication system |
| `backends` | `dict[str, CommunicatorBackendConfig]` | `{}` | Named communicator backends (auto-discriminated by `type` field) |

The `backends` dict values are automatically discriminated into `TelegramCommunicatorConfig`, `EmailCommunicatorConfig`, or the base `CommunicatorBackendConfig` based on the `type` field.

## CommunicatorBackendConfig

`processpype.config.models.CommunicatorBackendConfig`

```python
class CommunicatorBackendConfig(ConfigurationModel):
    """Base configuration for a communicator backend instance."""
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | (required) | Backend type: `"telegram"`, `"email"`, or a custom type |
| `enabled` | `bool` | `True` | Whether this backend is active |
| `labels` | `list[str]` | `["default"]` | Labels this backend handles (cannot be empty) |
