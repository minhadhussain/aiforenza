from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title="AI Model API Credit Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "environment": settings.api_env}


app.include_router(api_router)
