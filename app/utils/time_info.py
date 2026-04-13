from datetime import datetime
from zoneinfo import ZoneInfo


def local_time_string(tz_name: str | None = None) -> str:
    """Human-readable local time for system prompts."""
    try:
        if tz_name:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
        else:
            now = datetime.now().astimezone()
    except Exception:
        now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def time_context_block() -> str:
    return f"\n[Current local time]: {local_time_string()}\n"
