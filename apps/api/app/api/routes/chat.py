from fastapi import APIRouter
from fastapi import Header
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from app.models.openai import ChatCompletionRequest
from app.services.access_control import authorize_api_request
from app.services.access_control import release_authorized_request
from app.services.chat_completions import bill_non_streaming_response
from app.services.chat_completions import bill_streaming_response
from app.services.chat_completions import forward_chat_completion
from app.services.chat_completions import forward_chat_completion_stream
from app.services.observability import capture_event


router = APIRouter()


@router.post("/chat/completions")
async def post_chat_completions(
    request: ChatCompletionRequest,
    raw_request: Request,
    authorization: str | None = Header(default=None),
):
    raw_body = await raw_request.body()
    authz = await authorize_api_request(authorization=authorization, request=request, raw_body=raw_body)

    try:
        if request.stream:
            source = await forward_chat_completion_stream(request, authz.model, authz.request_id)
            iterator = await bill_streaming_response(
                source=source,
                request=request,
                user_id=authz.api_key["user_id"],
                api_key_id=authz.api_key["id"],
                model=authz.model,
                request_id=authz.request_id,
            )
            capture_event(authz.api_key["user_id"], "first_api_request", {"request_id": authz.request_id, "model": request.model, "stream": True})
            return StreamingResponse(
                iterator,
                media_type="text/event-stream",
                headers={"x-request-id": authz.request_id},
            )

        payload = await forward_chat_completion(request, authz.model, authz.request_id)
        payload = await bill_non_streaming_response(
            request=request,
            response_payload=payload,
            user_id=authz.api_key["user_id"],
            api_key_id=authz.api_key["id"],
            model=authz.model,
            request_id=authz.request_id,
        )
        capture_event(authz.api_key["user_id"], "first_api_request", {"request_id": authz.request_id, "model": request.model, "stream": False})
        return JSONResponse(payload, headers={"x-request-id": authz.request_id})
    finally:
        release_authorized_request(authz)
