from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import hashlib

import pytest
import test_wallet_database

# Reuse the isolated-schema fixture without importing its name into test arguments.
database = test_wallet_database.database


def query(database, sql, args=()):
    import psycopg2

    url, schema = database
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(sql.replace("SCHEMA", schema), args)
            return cur.fetchall() if cur.description else None


def fixtures(database):
    campaign, user, other, model = [str(uuid4()) for _ in range(4)]
    query(database, "update SCHEMA.hackathon_campaigns set status='INACTIVE'")
    query(
        database,
        "insert into SCHEMA.hackathon_campaigns(id,name,status) values(%s,%s,'ACTIVE')",
        (campaign, uuid4().hex),
    )
    for owner in (user, other):
        query(
            database,
            "insert into SCHEMA.profiles(id,email) values(%s,%s)",
            (owner, owner + "@example.invalid"),
        )
        query(
            database,
            "insert into SCHEMA.wallets(user_id,balance_cents) values(%s,100000)",
            (owner,),
        )
    query(
        database,
        "insert into SCHEMA.hackathon_team_grants(campaign_id,team_id) values(%s,'HACK-001'),(%s,'HACK-002')",
        (campaign, campaign),
    )
    query(
        database,
        "insert into SCHEMA.models(id,slug,display_name,provider,provider_model_id,enabled,input_price_per_million,output_price_per_million,pricing_verified,reference_price_source,reference_price_checked_at,reference_price_valid_until) values(%s,%s,'Fixture','fixture','fixture',true,1,1,true,'fixture',now(),now()+interval '1 day')",
        (model, uuid4().hex),
    )
    return campaign, user, other, model


def claim(database, user, team="HACK-001"):
    return query(
        database,
        "select SCHEMA.claim_hackathon_team(%s,%s,%s,'sk_af_hackathon_')",
        (user, team, hashlib.sha256(uuid4().bytes).hexdigest()),
    )[0][0]


def grant(database, user):
    return query(
        database,
        "select id,api_key_id,wallet_id from SCHEMA.hackathon_team_grants where claimed_by_user_id=%s",
        (user,),
    )[0]


def reserve(database, user, key, model, amount, rid=None):
    rid = rid or "req_" + uuid4().hex
    query(
        database,
        "select SCHEMA.reserve_usage(%s,%s,%s,%s,%s)",
        (rid, user, key, model, amount),
    )
    return rid


def settle(database, user, key, model, rid, reference, actual=None):
    actual = reference if actual is None else actual
    return query(
        database,
        "select * from SCHEMA.record_usage_charge(%s,%s,%s,%s,10,10,0,20,%s,%s,%s,null,'fixture','completed')",
        (user, key, model, rid, reference, actual, reference - actual),
    )[0]


def test_atomic_claim_and_one_key_wallet_ledger(database):
    import psycopg2

    campaign, user, other, model = fixtures(database)

    def attempt(owner):
        try:
            return owner, claim(database, owner)
        except psycopg2.Error as exc:
            return owner, exc.diag.message_primary

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [user, other]))
    assert sum(isinstance(result, dict) for _, result in results) == 1
    assert [result for _, result in results if isinstance(result, str)] == [
        "team_already_claimed"
    ]
    owner, result = next((u, r) for u, r in results if isinstance(r, dict))
    assert result["promo_balance_cents"] == result["available_balance_cents"] == 10000
    gid, key, wallet = grant(database, owner)
    assert (
        query(
            database,
            "select count(*) from SCHEMA.wallets where hackathon_grant_id=%s",
            (gid,),
        )[0][0]
        == 1
    )
    assert (
        query(
            database,
            "select count(*) from SCHEMA.api_keys where hackathon_grant_id=%s",
            (gid,),
        )[0][0]
        == 1
    )
    assert query(
        database,
        "select amount_cents,billing_source from SCHEMA.transactions where hackathon_grant_id=%s",
        (gid,),
    ) == [(10000, "PROMOTIONAL")]
    assert (
        query(
            database,
            "select balance_cents from SCHEMA.wallets where user_id=%s",
            (owner,),
        )[0][0]
        == 100000
    )
    status = query(database, "select SCHEMA.hackathon_status(%s)", (owner,))[0][0]
    assert status["grants"][0]["team_id"] == "HACK-001"
    assert not any(
        secret in str(status)
        for secret in (
            "key_hash",
            "key_prefix",
            "plaintext_key",
            "wallet_id",
            "api_key_id",
        )
    )
    for team in ("HACK-001", "INVALID-001"):
        with pytest.raises(psycopg2.Error) as exc:
            claim(database, other, team)
        assert exc.value.diag.message_primary == (
            "team_already_claimed" if team == "HACK-001" else "invalid_team_id"
        )
    for command in (
        "insert into SCHEMA.api_keys(user_id,name,key_prefix,key_hash,billing_source,hackathon_grant_id) values(%s,'other','x','another','PROMOTIONAL',%s)",
        "insert into SCHEMA.wallets(user_id,billing_source,hackathon_grant_id) values(null,'PROMOTIONAL',%s)",
    ):
        with pytest.raises(psycopg2.Error):
            query(database, command, (owner, gid) if "api_keys" in command else (gid,))
    with pytest.raises(psycopg2.Error):
        query(
            database,
            "update SCHEMA.api_keys set hackathon_grant_id=null,billing_source='PAID' where id=%s",
            (key,),
        )
    with pytest.raises(psycopg2.Error):
        query(
            database,
            "update SCHEMA.hackathon_team_grants set status='UNCLAIMED',claimed_by_user_id=null,claimed_at=null,wallet_id=null,api_key_id=null where id=%s",
            (gid,),
        )


def test_promo_reservation_settlement_release_and_no_paid_fallback(database):
    import psycopg2

    campaign, user, other, model = fixtures(database)
    claim(database, user)
    gid, key, wallet = grant(database, user)
    rid = reserve(database, user, key, model, 1000)
    personal = query(database, "select SCHEMA.wallet_availability(%s)", (user,))[0][0]
    promotional = query(database, "select SCHEMA.api_key_wallet(%s,%s)", (user, key))[
        0
    ][0]
    assert (
        personal["reserved_cents"] == 0
        and personal["available_balance_cents"] == 100000
    )
    assert (
        promotional["reserved_cents"] == 1000
        and promotional["available_balance_cents"] == 9000
    )
    with pytest.raises(psycopg2.Error) as exc:
        settle(database, user, key, model, rid, 1000, 600)
    assert exc.value.diag.message_primary == "promotional_discount_forbidden"
    with ThreadPoolExecutor(max_workers=2) as pool:
        settled = list(
            pool.map(lambda _: settle(database, user, key, model, rid, 700), range(2))
        )
    assert settled[0] == settled[1]
    assert (
        query(
            database, "select balance_cents from SCHEMA.wallets where id=%s", (wallet,)
        )[0][0]
        == 9300
    )
    assert (
        query(
            database,
            "select count(*) from SCHEMA.wallet_reservations where request_id=%s",
            (rid,),
        )[0][0]
        == 0
    )
    assert query(
        database,
        "select billing_source,hackathon_grant_id,reference_charge_cents,customer_charge_cents,customer_savings_cents from SCHEMA.usage_records where request_id=%s",
        (rid,),
    ) == [("PROMOTIONAL", gid, 700, 700, 0)]
    assert query(
        database,
        "select reserved_amount_cents,reservation_created_at is not null from SCHEMA.usage_records where request_id=%s",
        (rid,),
    ) == [(1000, True)]
    assert query(
        database,
        "select billing_source,hackathon_grant_id,amount_cents from SCHEMA.transactions where reference_id=%s",
        ("usage:" + rid,),
    ) == [("PROMOTIONAL", gid, -700)]
    history = query(database, "select SCHEMA.dashboard_activity(%s)", (user,))[0][0]
    assert (
        history["data"][0]["billing_source"] == "PROMOTIONAL"
        and history["data"][0]["hackathon_team_id"] == "HACK-001"
    )
    rid = reserve(database, user, key, model, 500)
    released = query(
        database,
        "select SCHEMA.release_unconsumed_usage(%s,%s,%s,'provider_rejected')",
        (rid, user, key),
    )[0][0]
    assert released["released_cents"] == 500
    assert query(
        database,
        "select billing_source,hackathon_grant_id from SCHEMA.wallet_reservation_releases where request_id=%s",
        (rid,),
    ) == [("PROMOTIONAL", gid)]
    with pytest.raises(psycopg2.Error):
        reserve(database, other, key, model, 1)
    pending = reserve(database, user, key, model, 9300)
    with pytest.raises(psycopg2.Error) as exc:
        reserve(database, user, key, model, 1)
    assert exc.value.diag.message_primary == "insufficient_balance"
    settle(database, user, key, model, pending, 9300)
    with pytest.raises(psycopg2.Error) as exc:
        reserve(database, user, key, model, 1)
    assert exc.value.diag.message_primary == "insufficient_balance"
    assert (
        query(
            database,
            "select balance_cents from SCHEMA.wallets where user_id=%s",
            (user,),
        )[0][0]
        == 100000
    )
    assert (
        query(
            database, "select balance_cents from SCHEMA.wallets where id=%s", (wallet,)
        )[0][0]
        == 0
    )
    assert (
        query(
            database,
            "select sum(amount_cents) from SCHEMA.transactions where wallet_id=%s",
            (wallet,),
        )[0][0]
        == 0
    )


def test_concurrent_promo_spending_cannot_overdraw_and_disabled_keys_settle(database):
    import psycopg2

    campaign, user, other, model = fixtures(database)
    claim(database, user)
    gid, key, wallet = grant(database, user)

    def attempt(_):
        try:
            return reserve(database, user, key, model, 6000)
        except psycopg2.Error as exc:
            assert exc.diag.message_primary == "insufficient_balance"
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sum(r is not None for r in results) == 1
    query(database, "update SCHEMA.api_keys set revoked_at=now() where id=%s", (key,))
    with pytest.raises(psycopg2.Error):
        reserve(database, user, key, model, 1)
    settle(database, user, key, model, next(r for r in results if r), 6000)
    assert (
        query(
            database, "select balance_cents from SCHEMA.wallets where id=%s", (wallet,)
        )[0][0]
        == 4000
    )
    with pytest.raises(psycopg2.Error):
        claim(database, user)


def test_inactive_campaign_invalid_claims_and_privileges(database):
    import psycopg2

    campaign, user, other, model = fixtures(database)
    query(
        database,
        "update SCHEMA.hackathon_campaigns set status='INACTIVE' where id=%s",
        (campaign,),
    )
    with pytest.raises(psycopg2.Error) as exc:
        claim(database, user)
    assert exc.value.diag.message_primary == "campaign_inactive"
    assert (
        query(
            database,
            "select count(*) from SCHEMA.wallets where billing_source='PROMOTIONAL' and hackathon_grant_id in (select id from SCHEMA.hackathon_team_grants where campaign_id=%s)",
            (campaign,),
        )[0][0]
        == 0
    )
    _, schema = database
    for role in ("anon", "authenticated"):
        flags = query(
            database,
            "select has_function_privilege(%s,%s,'EXECUTE'),has_table_privilege(%s,%s,'SELECT')",
            (
                role,
                f"{schema}.claim_hackathon_team(uuid,text,text,text)",
                role,
                f"{schema}.hackathon_team_grants",
            ),
        )
        assert flags == [(False, False)]


def test_orphan_wallet_key_and_cross_grant_writes_rejected(database):
    import psycopg2

    campaign, user, other, model = fixtures(database)
    unclaimed = query(database, "select id from SCHEMA.hackathon_team_grants where campaign_id=%s and team_id='HACK-002'", (campaign,))[0][0]
    for sql, args in [
        ("insert into SCHEMA.wallets(billing_source,hackathon_grant_id) values('PROMOTIONAL',%s)", (unclaimed,)),
        ("insert into SCHEMA.api_keys(user_id,name,key_prefix,key_hash,billing_source,hackathon_grant_id) values(%s,'orphan','fixture',%s,'PROMOTIONAL',%s)", (user, uuid4().hex, unclaimed)),
    ]:
        with pytest.raises(psycopg2.Error) as exc:
            query(database, sql, args)
        assert exc.value.diag.message_primary == "claim_integrity_violation"
    claim(database, user)
    claim(database, other, "HACK-002")
    _, key, wallet = grant(database, user)
    other_gid, other_key, _ = grant(database, other)
    with pytest.raises(psycopg2.Error):
        query(database, "update SCHEMA.api_keys set hackathon_grant_id=%s where id=%s", (other_gid, key))
    rid = reserve(database, user, key, model, 100)
    with pytest.raises(psycopg2.Error):
        settle(database, other, other_key, model, rid, 100)
    assert query(database, "select balance_cents from SCHEMA.wallets where id=%s", (wallet,)) == [(10000,)]


def test_campaign_seeding_is_idempotent_and_does_not_issue_credit(database):
    # Execute the real organizer tool against this test's isolated PostgreSQL schema.
    import importlib.util
    from pathlib import Path
    import psycopg2

    spec = importlib.util.spec_from_file_location("hackathon_admin", Path(__file__).resolve().parents[3] / "tools/hackathon_admin.py")
    admin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(admin)
    url, schema = database

    class ScopedCursor:
        def __enter__(self):
            self.cursor = connection.cursor()
            return self

        def __exit__(self, *args):
            self.cursor.close()

        def execute(self, sql, args=()):
            self.cursor.execute(sql.replace("public.", schema + "."), args)

        def fetchone(self):
            return self.cursor.fetchone()

    class ScopedConnection:
        def cursor(self):
            return ScopedCursor()

    name = "Seed " + uuid4().hex
    ids = [f"HACK-{i:03}" for i in range(1, 51)]
    query(database, "update SCHEMA.hackathon_campaigns set status='INACTIVE'")
    with psycopg2.connect(url, sslmode="require") as connection:
        assert admin.setup_campaign(ScopedConnection(), name, ids, activate=True) == 50
        assert admin.setup_campaign(ScopedConnection(), name, ids, activate=True) == 50
    assert query(database, "select count(*),count(wallet_id),count(api_key_id) from SCHEMA.hackathon_team_grants where campaign_id=(select id from SCHEMA.hackathon_campaigns where name=%s)", (name,)) == [(50, 0, 0)]


def test_claim_failure_rolls_back_every_financial_effect(database):
    import psycopg2

    campaign, user, other, model = fixtures(database)
    duplicate_hash = hashlib.sha256(b"fixture-conflict").hexdigest()
    query(
        database,
        "insert into SCHEMA.api_keys(user_id,name,key_prefix,key_hash) values(%s,'personal','fixture',%s)",
        (user, duplicate_hash),
    )
    with pytest.raises(psycopg2.Error):
        query(
            database,
            "select SCHEMA.claim_hackathon_team(%s,'HACK-001',%s,'sk_af_hackathon_')",
            (user, duplicate_hash),
        )
    assert query(
        database,
        "select status,wallet_id,api_key_id from SCHEMA.hackathon_team_grants where campaign_id=%s and team_id='HACK-001'",
        (campaign,),
    ) == [("UNCLAIMED", None, None)]
    assert (
        query(
            database,
            "select count(*) from SCHEMA.wallets where hackathon_grant_id in (select id from SCHEMA.hackathon_team_grants where campaign_id=%s)",
            (campaign,),
        )[0][0]
        == 0
    )
    claim(database, user)
    gid, key, wallet = grant(database, user)
    for sql, args in [
        (
            "update SCHEMA.transactions set amount_cents=9999 where hackathon_grant_id=%s",
            (gid,),
        ),
        ("delete from SCHEMA.transactions where hackathon_grant_id=%s", (gid,)),
        ("update SCHEMA.api_keys set key_hash='replacement' where id=%s", (key,)),
        ("update SCHEMA.wallets set balance_cents=-1 where id=%s", (wallet,)),
    ]:
        with pytest.raises(psycopg2.Error):
            query(database, sql, args)
    assert (
        query(
            database, "select balance_cents from SCHEMA.wallets where id=%s", (wallet,)
        )[0][0]
        == 10000
    )


def test_personal_key_and_stripe_topup_do_not_target_promo_wallet(database):
    campaign, user, other, model = fixtures(database)
    claim(database, user)
    gid, promo_key, promo_wallet = grant(database, user)
    paid_key = str(uuid4())
    query(
        database,
        "insert into SCHEMA.api_keys(id,user_id,name,key_prefix,key_hash) values(%s,%s,'paid','fixture',%s)",
        (paid_key, user, uuid4().hex),
    )
    rid = reserve(database, user, paid_key, model, 60)
    settle(database, user, paid_key, model, rid, 100, 60)
    assert (
        query(
            database,
            "select balance_cents from SCHEMA.wallets where user_id=%s",
            (user,),
        )[0][0]
        == 99940
    )
    assert (
        query(
            database,
            "select balance_cents from SCHEMA.wallets where id=%s",
            (promo_wallet,),
        )[0][0]
        == 10000
    )
    session, event, intent = [uuid4().hex for _ in range(3)]
    query(
        database,
        "insert into SCHEMA.topups(user_id,stripe_checkout_session_id,amount_cents,currency,status,package_id,package_value_usd_cents,stripe_amount_inr,stripe_currency,exchange_rate_used) values(%s,%s,1000,'USD','PENDING','starter_10',1000,83500,'INR',83.5)",
        (user, session),
    )
    query(
        database,
        "select * from SCHEMA.complete_topup(%s,%s,%s,%s,1000,'USD')",
        (event, session, intent, user),
    )
    assert (
        query(
            database,
            "select balance_cents from SCHEMA.wallets where user_id=%s",
            (user,),
        )[0][0]
        == 100940
    )
    assert (
        query(
            database,
            "select balance_cents from SCHEMA.wallets where id=%s",
            (promo_wallet,),
        )[0][0]
        == 10000
    )
