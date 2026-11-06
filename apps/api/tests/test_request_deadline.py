import asyncio
import json

from app.core.config import Settings, settings
from app.middleware.request_deadline import RequestDeadlineMiddleware


def test_vercel_deadline_defaults_and_override(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    configuration = Settings(_env_file=None)
    assert configuration.request_timeout_seconds is None
    monkeypatch.setenv("VERCEL", "1")
    assert configuration.request_timeout_seconds == 240
    configuration.api_request_timeout_seconds = 750
    assert configuration.request_timeout_seconds == 750


def test_deadline_returns_504_after_app_cleanup(monkeypatch):
    monkeypatch.setattr(settings, "api_request_timeout_seconds", 0.01)
    messages = []
    cleaned = []

    async def app(scope, receive, send):
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.append(True)

    async def send(message):
        assert cleaned == [True]
        messages.append(message)

    asyncio.run(RequestDeadlineMiddleware(app)({"type": "http"}, None, send))
    assert messages[0]["status"] == 504
    assert json.loads(messages[1]["body"])["error"]["code"] == "request_timeout"


def test_deadline_preserves_successful_responses(monkeypatch):
    monkeypatch.setattr(settings, "api_request_timeout_seconds", 5)
    messages = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b"ready"})

    async def send(message):
        messages.append(message)

    asyncio.run(RequestDeadlineMiddleware(app)({"type": "http"}, None, send))
    assert [message.get("status", message.get("body")) for message in messages] == [201, b"ready"]
