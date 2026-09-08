from app.repositories.supabase_rest import rest_select


async def fetch_profile(user_id: str) -> dict | None:
    payload = await rest_select(
        path="/rest/v1/profiles",
        params={
            "id": f"eq.{user_id}",
            "select": "id,email,created_at,updated_at",
            "limit": "1",
        },
    )
    return payload[0] if payload else None
