
import os
import sys
import time

from pytz import timezone

default_timezone = timezone("UTC").zone

def setup_timezone(tz: str | None = default_timezone):
    if tz is None:
        return

    os.environ["TZ"] = tz
    if sys.platform != "win32":
        time.tzset()
    else:
        print("Windows does not support timezone setting.")
