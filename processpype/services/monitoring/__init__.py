"""Monitoring services for ProcessPype.

This package contains monitoring services for ProcessPype applications.
"""

# Import services to ensure they get registered
try:
    from processpype.services.monitoring.system import SystemMonitoringService  # noqa
except ImportError:
    pass

try:
    from processpype.services.monitoring.cronitor import CronitorService  # noqa
except ImportError:
    pass

try:
    from processpype.services.monitoring.cloudwatch import CloudWatchService  # noqa
except ImportError:
    pass

__all__ = ["SystemMonitoringService", "CronitorService", "CloudWatchService"]
