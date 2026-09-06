from fastapi import APIRouter

from app.api.routes import account
from app.api.routes import api_keys
from app.api.routes import health
from app.api.routes import models


api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1", tags=["platform"])
api_router.include_router(account.router, prefix="/v1", tags=["dashboard"])
api_router.include_router(api_keys.router, prefix="/v1", tags=["dashboard"])
api_router.include_router(models.router, prefix="/v1", tags=["models"])
