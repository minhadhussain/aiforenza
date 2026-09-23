import re

import httpx

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.api.deps.auth import get_current_dashboard_user
from app.repositories.hackathon import claim_team, grant_status
from app.repositories.profiles import fetch_profile
from app.repositories.wallets import bootstrap_user_account
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.services.api_keys import generate_api_key, hash_api_key, key_prefix_for
from app.services.rate_limit import check_api_rate_limit

router = APIRouter()


class ClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_id: str = Field(min_length=3, max_length=64)

    @field_validator("team_id")
    @classmethod
    def normalized(cls, value):
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,63}", value):
            raise ValueError("Enter a valid Team ID")
        return value


def safe_error(exc):
    for code, status, message in (
        (
            "team_already_claimed",
            409,
            "This Team ID has already claimed its hackathon credit. Only one $100 promotional grant is allowed per Team ID.",
        ),
        (
            "invalid_team_id",
            404,
            "This Team ID is not eligible for the active hackathon.",
        ),
        ("campaign_inactive", 409, "There is no active hackathon campaign."),
    ):
        if code in str(exc):
            return HTTPException(
                status_code=status,
                detail={"code": code, "message": message},
                headers={"Cache-Control": "no-store"},
            )
    return HTTPException(
        status_code=503,
        headers={"Cache-Control": "no-store"},
        detail={
            "code": "hackathon_unavailable",
            "message": "Hackathon credits are temporarily unavailable. Check your grant status before retrying.",
        },
    )


@router.post("/hackathon/claim", status_code=201)
async def claim(
    payload: ClaimRequest,
    response: Response,
    user: dict = Depends(get_current_dashboard_user),
):
    response.headers["Cache-Control"] = "no-store"
    # Per-account limit reduces guessing. Team IDs are organizer-issued claim codes,
    # not credentials for subsequent API calls.
    check_api_rate_limit(user_id=user["id"], api_key_id="hackathon-claim:" + user["id"])
    secret = generate_api_key(billing_source="PROMOTIONAL")
    try:
        if await fetch_profile(user["id"]) is None:
            await bootstrap_user_account(user["id"], user.get("email", ""))
        grant = await claim_team(
            user["id"], payload.team_id, hash_api_key(secret), key_prefix_for(secret)
        )
    except (SupabaseRepositoryError, httpx.HTTPError) as exc:
        raise safe_error(exc) from None
    return {"grant": grant, "plaintext_key": secret}


@router.get("/hackathon/status")
async def status(response: Response, user: dict = Depends(get_current_dashboard_user)):
    response.headers["Cache-Control"] = "no-store"
    try:
        return await grant_status(user["id"])
    except (SupabaseRepositoryError, httpx.HTTPError) as exc:
        raise safe_error(exc) from None
