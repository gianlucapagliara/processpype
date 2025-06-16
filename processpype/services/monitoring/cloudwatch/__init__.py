"""CloudWatch monitoring service.

This module exports the CloudWatchService class which allows ProcessPype
applications to send metrics to AWS CloudWatch.
"""

from .service import CloudWatchService

__all__ = ["CloudWatchService"]
