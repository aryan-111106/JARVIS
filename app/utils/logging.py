"""Structured logging utility for request-scoped logging."""
import json
import uuid
from datetime import datetime, timezone


def get_request_id() -> str:
    """Returns a UUID string (length 36)."""
    return str(uuid.uuid4())


def structured_log(level: str, event: str, **kwargs) -> str:
    """Returns a JSON string with ts, level, event, and any extra kwargs merged in."""
    log_data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **kwargs,
    }
    return json.dumps(log_data)
