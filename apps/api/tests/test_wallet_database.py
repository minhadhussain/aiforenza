"""Opt-in integration tests; only an isolated randomly named schema is committed."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest


class RedactedDatabaseURL(str):
    """Keep pytest's fixture argument display from exposing database credentials."""

    def __repr__(self):
        return "'<redacted database URL>'"


def test_database_url_fixture_representation_is_redacted():
    value = RedactedDatabaseURL(
        "postgresql://fixture:PRIVATE_PASSWORD@example.invalid/db"
    )
    assert "PRIVATE_PASSWORD" not in repr((value, "isolated_schema"))
    assert str(value).startswith("postgresql://fixture:")


@pytest.fixture(scope="module")
def database():
    if os.getenv("RUN_DATABASE_TESTS") != "1":
        pytest.skip(
            "Set RUN_DATABASE_TESTS=1 to test the configured database in an isolated schema"
        )
    psycopg2 = pytest.importorskip("psycopg2")
    from dotenv import dotenv_values

    env = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
    url = env.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not configured")
    schema = "verify_" + uuid4().hex
    conn = psycopg2.connect(url, connect_timeout=10, sslmode="require")
    sql = (
        Path(__file__).resolve().parents[3]
        / "supabase/migrations/202609090001_wallet_reservations.sql"
    ).read_text()
    try:
        # Validate real migration DDL, then roll it back without altering the live schema.
        with conn.cursor() as cur:
            cur.execute("set lock_timeout='3s'; set statement_timeout='20s'")
            cur.execute("select to_regclass('public.wallet_reservations')")
            applied = cur.fetchone()[0] is not None
            if not applied:
                cur.execute(sql.replace("commit;", ""))
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(f"create schema {schema}")
            for table in (
                "profiles",
                "wallets",
                "api_keys",
                "models",
                "transactions",
                "usage_records",
                "topups",
                "stripe_events",
            ):
                cur.execute(
                    f"create table {schema}.{table} (like public.{table} including all)"
                )
            for signature in (
                "public.record_usage_charge(uuid,uuid,uuid,text,integer,integer,integer,integer,bigint,bigint,bigint,bigint,text,text)",
                "public.record_usage_charge(uuid,uuid,uuid,text,integer,integer,integer,bigint,text,text)",
            ):
                source_signature = (
                    signature.replace(
                        "record_usage_charge(", "record_usage_charge_unreserved("
                    )
                    if applied and "integer,integer,integer,integer," in signature
                    else signature
                )
                cur.execute(
                    "select pg_get_functiondef(%s::regprocedure)", (source_signature,)
                )
                definition = cur.fetchone()[0].replace(
                    "record_usage_charge_unreserved", "record_usage_charge"
                )
                cur.execute(definition.replace("public.", schema + "."))
            isolated = sql.replace("public.", schema + ".")
            isolated = "\n".join(
                line
                for line in isolated.splitlines()
                if "bootstrap_user_account" not in line and "complete_topup" not in line
            )
            cur.execute(isolated)
            availability_sql = (
                Path(__file__).resolve().parents[3]
                / "supabase/migrations/202609100001_wallet_availability.sql"
            ).read_text()
            cur.execute(availability_sql.replace("public.", schema + "."))
            payment_sql = (
                Path(__file__).resolve().parents[3]
                / "supabase/migrations/202609090002_payment_credit_safety.sql"
            ).read_text()
            cur.execute(payment_sql.replace("public.", schema + "."))
        conn.commit()
        yield RedactedDatabaseURL(url), schema
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {schema} cascade")
        conn.commit()
        conn.close()


def test_concurrent_reservations_exact_balance_idempotency(database):
    import psycopg2

    url, schema = database
    user, key, model, wallet = [str(uuid4()) for _ in range(4)]
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"insert into {schema}.profiles(id,email) values(%s,%s)",
                (user, "isolated-test@example.invalid"),
            )
            cur.execute(
                f"insert into {schema}.wallets(id,user_id,balance_cents) values(%s,%s,50)",
                (wallet, user),
            )
            cur.execute(
                f"insert into {schema}.transactions(user_id,wallet_id,type,amount_cents,balance_after_cents,reference_id,description) values(%s,%s,'ADJUSTMENT',50,50,%s,'Isolated test fixture')",
                (user, wallet, uuid4().hex),
            )
            cur.execute(
                f"insert into {schema}.api_keys(id,user_id,name,key_prefix,key_hash) values(%s,%s,'test','test','test')",
                (key, user),
            )
            cur.execute(
                f"insert into {schema}.models(id,slug,display_name,provider,provider_model_id,enabled,input_price_per_million,output_price_per_million,cached_input_price_per_million,discount_percent,customer_input_price_per_million,customer_output_price_per_million,customer_cached_input_price_per_million,pricing_verified,reference_price_source,reference_price_checked_at,reference_price_valid_until,pricing_max_input_tokens,pricing_max_output_tokens) "
                f"values(%s,'test','Test','test','test',true,1,1,0,40,0.6,0.6,0,true,'fixture',now(),now()+interval '1 day',1000,1000)",
                (model,),
            )

    def reserve(request_id, amount):
        try:
            with psycopg2.connect(url, sslmode="require") as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"select {schema}.reserve_usage(%s,%s,%s,%s,%s)",
                        (request_id, user, key, model, amount),
                    )
                    cur.fetchone()
            return request_id
        except psycopg2.Error as exc:
            assert exc.diag.message_primary == "insufficient_balance"
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda request_id: reserve(request_id, 40), [uuid4().hex, uuid4().hex]
            )
        )
    assert sum(item is not None for item in results) == 1
    winner = next(item for item in results if item)
    rejected = uuid4().hex
    assert reserve(rejected, 5) == rejected
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"select {schema}.release_unconsumed_usage(%s,%s,%s,'provider_rejected')",
                (rejected, user, key),
            )
            assert cur.fetchone()[0]["released_cents"] == 5
            cur.execute(
                f"select {schema}.release_unconsumed_usage(%s,%s,%s,'provider_rejected')",
                (rejected, user, key),
            )
            assert cur.fetchone()[0]["already_released"] is True
    with pytest.raises(psycopg2.Error):
        with psycopg2.connect(url, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"select {schema}.release_unconsumed_usage(%s,%s,%s,'provider_rejected')",
                    (rejected, user, str(uuid4())),
                )
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(f"select {schema}.wallet_availability(%s)", (user,))
            snapshot = cur.fetchone()[0]
            assert snapshot["balance_cents"] == 50
            assert snapshot["reserved_cents"] == 40
    assert snapshot["available_balance_cents"] == 10

    def settle(request_id, charge):
        with psycopg2.connect(url, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"select * from {schema}.record_usage_charge(%s,%s,%s,%s,10,10,0,20,%s,%s,0,null,'test','completed')",
                    (user, key, model, request_id, charge, charge),
                )
                return cur.fetchone()

    with ThreadPoolExecutor(max_workers=2) as pool:
        settled = list(pool.map(lambda _: settle(winner, 40), range(2)))
    assert settled[0] == settled[1]
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"select {schema}.release_unconsumed_usage(%s,%s,%s,'provider_rejected')",
                (winner, user, key),
            )
            assert cur.fetchone()[0]["already_settled"] is True
    exact = uuid4().hex
    assert reserve(exact, 10) == exact
    settle(exact, 10)
    assert reserve(uuid4().hex, 1) is None
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"select balance_cents from {schema}.wallets where id=%s", (wallet,)
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                f"select count(*) from {schema}.usage_records where user_id=%s", (user,)
            )
            assert cur.fetchone()[0] == 2
            cur.execute(
                f"select sum(amount_cents) from {schema}.transactions where user_id=%s",
                (user,),
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                f"select count(*) from {schema}.wallet_reservations where user_id=%s",
                (user,),
            )
            assert cur.fetchone()[0] == 0


def test_duplicate_topup_credits_exactly_payment_amount(database):
    import psycopg2

    url, schema = database
    user, wallet = str(uuid4()), str(uuid4())
    session, event, intent = [uuid4().hex for _ in range(3)]
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"insert into {schema}.profiles(id,email) values(%s,%s)",
                (user, uuid4().hex + "@example.invalid"),
            )
            cur.execute(
                f"insert into {schema}.wallets(id,user_id,balance_cents) values(%s,%s,0)",
                (wallet, user),
            )
            cur.execute(
                f"insert into {schema}.topups(user_id,stripe_checkout_session_id,amount_cents,currency,status) values(%s,%s,1000,'USD','PENDING')",
                (user, session),
            )

    def complete(_):
        with psycopg2.connect(url, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"select * from {schema}.complete_topup(%s,%s,%s,%s,1000,'USD')",
                    (event, session, intent, user),
                )
                return cur.fetchone()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(complete, range(2)))
    assert sum(not row[4] for row in results) == 1
    with psycopg2.connect(url, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"select balance_cents from {schema}.wallets where id=%s", (wallet,)
            )
            assert cur.fetchone()[0] == 1000
            cur.execute(
                f"select count(*),sum(amount_cents) from {schema}.transactions where user_id=%s and type='TOPUP'",
                (user,),
            )
            assert cur.fetchone() == (1, 1000)
