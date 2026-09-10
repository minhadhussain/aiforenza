import asyncio
import json

import pytest
from app.middleware.request_safety import RequestSafetyMiddleware
from app.core.config import settings


@pytest.mark.parametrize("size,status", [(1024, 200), (1025, 413)])
def test_streamed_body_limit_exact_boundary(monkeypatch, size, status):
    monkeypatch.setattr(settings, "api_max_request_bytes", 1024)
    forwarded, replies = [], []
    chunks = [
        {"type": "http.request", "body": b"x" * 512, "more_body": True},
        {"type": "http.request", "body": b"x" * (size - 512), "more_body": False},
    ]

    async def receive():
        return chunks.pop(0)

    async def send(message):
        replies.append(message)

    async def app(scope, receive, send):
        forwarded.append(await receive())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    asyncio.run(
        RequestSafetyMiddleware(app)({"type": "http", "method": "POST"}, receive, send)
    )
    assert replies[0]["status"] == status
    assert bool(forwarded) == (status == 200)
    if status == 413:
        error = json.loads(replies[1]["body"])["error"]
        assert error["code"] == "request_too_large" and "1024 bytes" in error["message"]
