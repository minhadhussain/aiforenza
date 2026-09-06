from fastapi import APIRouter, Depends

from app.api.deps.auth import get_current_dashboard_user


router = APIRouter()


@router.get("/account/me")
async def get_current_account(user: dict = Depends(get_current_dashboard_user)) -> dict:
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "app_metadata": user.get("app_metadata", {}),
        "user_metadata": user.get("user_metadata", {}),
    }
