"""Service naming utilities."""


def derive_service_name(cls: type) -> str:
    """Derive a short service name from a class by lowercasing and stripping 'service'."""
    return cls.__name__.lower().replace("service", "")
