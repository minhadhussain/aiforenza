from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import OpenAIAPIError
from app.core.errors import openai_error_payload


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(OpenAIAPIError)
    async def openai_api_error_handler(_: Request, exc: OpenAIAPIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=openai_error_payload(exc.message, exc.error_type, exc.code),
        )
