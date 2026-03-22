"""Test that importing from processpype.services triggers a DeprecationWarning."""

import importlib
import sys
import warnings


def test_services_import_deprecation_warning() -> None:
    """Importing processpype.services should emit a DeprecationWarning."""
    # Remove from cache so the module-level warning fires again
    mod_name = "processpype.services"
    sys.modules.pop(mod_name, None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module(mod_name)

    dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(dep_warnings) >= 1
    assert "processpype.services" in str(dep_warnings[0].message)
    assert "processpype.service.registry" in str(dep_warnings[0].message)


def test_services_reexports() -> None:
    """The compat shim should re-export all public names from the registry."""
    mod_name = "processpype.services"
    sys.modules.pop(mod_name, None)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mod = importlib.import_module(mod_name)

    assert hasattr(mod, "AVAILABLE_SERVICES")
    assert hasattr(mod, "register_service_class")
    assert hasattr(mod, "get_available_services")
    assert hasattr(mod, "get_service_class")
