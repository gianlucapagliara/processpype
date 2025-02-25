"""Tests for notification templates."""

import pytest

from processpype.services.notification import NotificationLevel, NotificationTemplate


def test_notification_template_creation():
    """Test creating a notification template."""
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.INFO,
    )

    assert template.name == "test_template"
    assert template.template == "Hello, {name}!"
    assert template.default_level == NotificationLevel.INFO


def test_notification_template_render():
    """Test rendering a notification template."""
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.INFO,
    )

    rendered = template.render({"name": "World"})
    assert rendered == "Hello, World!"


def test_notification_template_render_multiple_variables():
    """Test rendering a template with multiple variables."""
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}! Your score is {score}.",
        default_level=NotificationLevel.INFO,
    )

    rendered = template.render({"name": "World", "score": 100})
    assert rendered == "Hello, World! Your score is 100."


def test_notification_template_render_missing_variable():
    """Test rendering a template with a missing variable."""
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.INFO,
    )

    with pytest.raises(KeyError):
        template.render({})


def test_notification_template_render_extra_variable():
    """Test rendering a template with an extra variable."""
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.INFO,
    )

    rendered = template.render({"name": "World", "extra": "value"})
    assert rendered == "Hello, World!"
    # Extra variables are ignored


def test_notification_template_repr():
    """Test the string representation of a notification template."""
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.INFO,
    )

    assert repr(template) == "NotificationTemplate(name=test_template)"


def test_notification_template_default_level():
    """Test the default level of a notification template."""
    # Default level is INFO if not specified
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
    )

    assert template.default_level == NotificationLevel.INFO

    # Custom default level
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.WARNING,
    )

    assert template.default_level == NotificationLevel.WARNING


def test_notification_template_complex_formatting():
    """Test rendering a template with complex formatting."""
    template = NotificationTemplate(
        name="test_template",
        template="User {user_id}: {name} ({email}) - Status: {status}",
        default_level=NotificationLevel.INFO,
    )

    rendered = template.render(
        {
            "user_id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active",
        }
    )

    assert rendered == "User 123: John Doe (john@example.com) - Status: active"
