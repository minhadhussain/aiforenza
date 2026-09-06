from fastapi import APIRouter

from app.api.routes import account
from app.api.routes import health


api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1", tags=["platform"])
api_router.include_router(account.router, prefix="/v1", tags=["dashboard"])
