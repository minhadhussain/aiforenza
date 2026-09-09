import json
import logging
import time
from uuid import uuid4

from app.core.config import settings


logger = logging.getLogger("aiforenza.requests")


class RequestSafetyMiddleware:
    """Bound bodies before parsing; log metadata only, never headers or content."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = time.monotonic()
        request_id = "req_" + uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        status = 500
        sent = False

        async def tracked_send(message):
            nonlocal status, sent
            if message["type"] == "http.response.start":
                sent = True
                status = message["status"]
                message["headers"] = [(k,v) for k,v in message.get("headers",[]) if k.lower() != b"x-request-id"] + [(b"x-request-id",request_id.encode())]
            await send(message)

        async def reject(code, message, response_status):
            body = json.dumps({"error":{"message":message,"type":"api_error","code":code}}).encode()
            await tracked_send({"type":"http.response.start","status":response_status,"headers":[(b"content-type",b"application/json")]})
            await tracked_send({"type":"http.response.body","body":body})

        try:
            if scope.get("method") in {"POST","PUT","PATCH"}:
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body",b""))
                    if len(body) > settings.api_max_request_bytes:
                        await reject("request_too_large","Request body is too large.",413)
                        return
                    if not message.get("more_body",False):
                        break
                delivered = False
                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type":"http.request","body":bytes(body),"more_body":False}
                    return await receive()
                await self.app(scope,replay,tracked_send)
            else:
                await self.app(scope,receive,tracked_send)
        except Exception:
            if not sent:
                await reject("internal_error","Internal server error.",500)
            else:
                raise
        finally:
            logger.info(json.dumps({"request_id":request_id,"method":scope.get("method"),
                "status":status,"latency_ms":round((time.monotonic()-started)*1000),
                **scope.get("state",{}).get("audit",{})}))
