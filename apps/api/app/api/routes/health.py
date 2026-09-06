from fastapi import APIRouter


router = APIRouter()


@router.get("/status")
def api_status() -> dict[str, str]:
    return {"service": "api", "status": "ok"}
