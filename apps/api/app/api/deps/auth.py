from fastapi import Header, HTTPException, status

from app.services.supabase_auth import SupabaseAuthError, fetch_user_for_token


async def get_current_dashboard_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    access_token = authorization.removeprefix("Bearer ").strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        user = await fetch_user_for_token(access_token)
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    # Supabase owns this confirmation timestamp. User-editable metadata such as
    # user_metadata.email_verified must never authorize credits or key creation.
    if not user.get("id") or not user.get("email"):
        raise HTTPException(status_code=400, detail="Authenticated user is missing required account data.")
    if not user.get("email_confirmed_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "email_not_verified", "message": "Verify your email before creating API keys or claiming credits."},
        )
    return user
