"""Tests for structured logging utility."""
import json


def test_get_request_id():
    """Assert return is string of length 36."""
    from app.utils.logging import get_request_id
    request_id = get_request_id()
    assert isinstance(request_id, str), f"Expected str, got {type(request_id)}"
    assert len(request_id) == 36, f"Expected length 36, got {len(request_id)}"


def test_structured_log():
    """Assert returned JSON contains the passed request_id and session_id values and the event name."""
    from app.utils.logging import structured_log
    result = structured_log("INFO", "chat_start", request_id="abc123", session_id="sess456")
    data = json.loads(result)
    assert data["request_id"] == "abc123", f"Missing request_id, got {data}"
    assert data["session_id"] == "sess456", f"Missing session_id, got {data}"
    assert data["event"] == "chat_start", f"Missing event, got {data}"
    assert data["level"] == "INFO"
