import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """GET /health returns 200 and expected fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "groq_configured" in data

def test_pollinations_image_proxy():
    """GET /api/pollinations-image?prompt=... returns JPEG bytes."""
    response = client.get("/api/pollinations-image", params={"prompt": "a red apple"})
    assert response.status_code == 200
    assert response.headers["content-type"] in ("image/jpeg", "image/png")

def test_chat_stream_smoke():
    """POST /api/chat/stream with streaming returns SSE events."""
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set")
    with client.stream("POST", "/chat/stream", json={
        "message": "hello"
    }) as response:
        chunks = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                chunks.append(line)
        assert len(chunks) >= 1  # At least one SSE event fired
