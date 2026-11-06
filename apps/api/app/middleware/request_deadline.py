import asyncio
import json

from app.core.config import settings
from app.core.errors import openai_error_payload


class RequestDeadlineMiddleware:
    """Cancel long requests early enough for cleanup on bounded function runtimes."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        timeout = settings.request_timeout_seconds
        if scope["type"] != "http" or timeout is None:
            return await self.app(scope, receive, send)
        started = False
        complete = False
        event_stream = False

        async def tracked_send(message):
            nonlocal started, complete, event_stream
            if message["type"] == "http.response.start":
                started = True
                event_stream = any(
                    key.lower() == b"content-type" and value.lower().startswith(b"text/event-stream")
                    for key, value in message.get("headers", [])
                )
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                complete = True
            await send(message)

        deadline = asyncio.timeout(timeout)
        try:
            async with deadline:
                await self.app(scope, receive, tracked_send)
        except TimeoutError:
            if not deadline.expired():
                raise
            scope.setdefault("state", {}).setdefault("audit", {})["code"] = "request_timeout"
            # Cancellation unwinds the provider/stream finally blocks. Financial
            # holds remain for reconciliation if inference may have started.
            error = json.dumps(openai_error_payload(
                "The request reached its execution time limit. Check usage before retrying.",
                "api_error", "request_timeout",
            )).encode()
            if not started:
                await send({
                    "type": "http.response.start", "status": 504,
                    "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store")],
                })
                await send({"type": "http.response.body", "body": error})
            elif not complete:
                body = b"data: " + error + b"\n\n" if event_stream else b""
                await send({"type": "http.response.body", "body": body, "more_body": False})
