from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.middleware.error_handlers import register_error_handlers
from app.services.observability import init_posthog
from app.services.observability import init_sentry
from app.services.observability import init_provider_logging
from app.middleware.request_safety import RequestSafetyMiddleware
from app.services.supabase_http import supabase_http_lifespan


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with supabase_http_lifespan():
        yield


app = FastAPI(
    title="AI Model API Credit Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(RequestSafetyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_sentry()
init_provider_logging()
init_posthog()

register_error_handlers(app)


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "environment": settings.api_env}


app.include_router(api_router)
