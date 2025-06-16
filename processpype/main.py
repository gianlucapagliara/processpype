"""Main application entry point with service management."""

from processpype.creator import ApplicationCreator

app = ApplicationCreator.get_application()
