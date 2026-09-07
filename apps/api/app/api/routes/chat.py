from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from app.api.deps.api_keys import get_current_api_key
from app.models.openai import ChatCompletionRequest
from app.services.chat_completions import bill_non_streaming_response
from app.services.chat_completions import bill_streaming_response
from app.services.chat_completions import ensure_preflight_balance
from app.services.chat_completions import forward_chat_completion
from app.services.chat_completions import forward_chat_completion_stream
from app.services.chat_completions import validate_model_and_wallet


router = APIRouter()


@router.post("/chat/completions")
async def post_chat_completions(request: ChatCompletionRequest, api_key: dict = Depends(get_current_api_key)):
    model, wallet, request_id = await validate_model_and_wallet(api_key["user_id"], request.model)
    ensure_preflight_balance(request, model, wallet)

    if request.stream:
        source = await forward_chat_completion_stream(request, model, request_id)
        iterator = await bill_streaming_response(
            source=source,
            request=request,
            user_id=api_key["user_id"],
            api_key_id=api_key["id"],
            model=model,
            request_id=request_id,
        )
        return StreamingResponse(
            iterator,
            media_type="text/event-stream",
            headers={"x-request-id": request_id},
        )

    payload = await forward_chat_completion(request, model, request_id)
    payload = await bill_non_streaming_response(
        request=request,
        response_payload=payload,
        user_id=api_key["user_id"],
        api_key_id=api_key["id"],
        model=model,
        request_id=request_id,
    )
    return JSONResponse(payload, headers={"x-request-id": request_id})
