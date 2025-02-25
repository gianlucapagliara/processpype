"""Tests for the notification model."""

from processpype.services.notification import Notification, NotificationLevel


def test_notification_creation():
    """Test creating a notification."""
    notification = Notification(
        message="Test notification",
        level=NotificationLevel.INFO,
        metadata={"key": "value"},
        timestamp="2023-01-01T12:00:00",
    )

    assert notification.message == "Test notification"
    assert notification.level == NotificationLevel.INFO
    assert notification.metadata == {"key": "value"}
    assert notification.timestamp == "2023-01-01T12:00:00"


def test_notification_default_values():
    """Test the default values of a notification."""
    notification = Notification(
        message="Test notification",
    )

    assert notification.message == "Test notification"
    assert notification.level == NotificationLevel.INFO
    assert notification.metadata == {}
    assert notification.timestamp is None


def test_notification_custom_level():
    """Test creating a notification with a custom level."""
    notification = Notification(
        message="Test notification",
        level=NotificationLevel.WARNING,
    )

    assert notification.message == "Test notification"
    assert notification.level == NotificationLevel.WARNING


def test_notification_metadata():
    """Test notification metadata."""
    notification = Notification(
        message="Test notification",
        metadata={"key1": "value1", "key2": "value2"},
    )

    assert notification.metadata == {"key1": "value1", "key2": "value2"}


def test_notification_repr():
    """Test the string representation of a notification."""
    notification = Notification(
        message="Test notification",
        level=NotificationLevel.INFO,
    )

    assert (
        repr(notification)
        == f"Notification(level={NotificationLevel.INFO}, message=Test notification)"
    )


def test_notification_empty_metadata():
    """Test a notification with empty metadata."""
    notification = Notification(
        message="Test notification",
        metadata={},
    )

    assert notification.metadata == {}


def test_notification_none_metadata():
    """Test a notification with None metadata."""
    notification = Notification(
        message="Test notification",
        metadata=None,
    )

    assert notification.metadata == {}


def test_notification_complex_metadata():
    """Test a notification with complex metadata."""
    metadata = {
        "user_id": 123,
        "name": "John Doe",
        "email": "john@example.com",
        "status": "active",
        "scores": [10, 20, 30],
        "details": {
            "address": "123 Main St",
            "city": "Anytown",
        },
    }

    notification = Notification(
        message="Test notification",
        metadata=metadata,
    )

    assert notification.metadata == metadata
