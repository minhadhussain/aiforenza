from app.repositories.supabase_rest import execute_rest_rpc, rest_select


async def claim_team(user_id, team_id, key_hash, key_prefix):
    return await execute_rest_rpc(
        "/rest/v1/rpc/claim_hackathon_team",
        {
            "target_user_id": user_id,
            "target_team_id": team_id,
            "target_key_hash": key_hash,
            "target_key_prefix": key_prefix,
        },
    )


async def grant_status(user_id):
    return await execute_rest_rpc(
        "/rest/v1/rpc/hackathon_status", {"target_user_id": user_id}
    )


async def fetch_active_key_grant(key_id, grant_id, user_id):
    rows = await rest_select(
        "/rest/v1/hackathon_team_grants",
        {
            "id": "eq." + grant_id,
            "api_key_id": "eq." + key_id,
            "claimed_by_user_id": "eq." + user_id,
            "status": "eq.ACTIVE",
            "select": "id",
            "limit": "1",
        },
    )
    return rows[0] if rows else None
