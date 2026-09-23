"""SQL-shaped data against real financial RPCs in the existing isolated schema."""

import importlib
from pathlib import Path
from uuid import uuid4

import test_wallet_database
from test_hackathon_database import fixtures, query, reserve, settle

database = test_wallet_database.database


def test_financial_rpc_parameters_cannot_execute_sql(database):
    _, user, other, model = fixtures(database)
    key = str(uuid4())
    query(database, "insert into SCHEMA.api_keys(id,user_id,name,key_prefix,key_hash) values(%s,%s,'sql-test','fixture',%s)", (key, user, uuid4().hex))
    # Were this interpolated as SQL, it would target only this disposable schema.
    payload = "req_" + uuid4().hex + "'; DROP TABLE " + database[1] + ".wallets CASCADE; --"
    reserve(database, user, key, model, 100, payload)
    result = settle(database, user, key, model, payload, 100, 60)
    assert result[1] == 99940
    assert query(database, "select request_id,customer_charge_cents from SCHEMA.usage_records where request_id=%s", (payload,)) == [(payload, 60)]
    assert query(database, "select reference_id,amount_cents from SCHEMA.transactions where reference_id=%s", ("usage:" + payload,)) == [("usage:" + payload, -60)]
    assert query(database, "select balance_cents from SCHEMA.wallets where user_id=%s", (other,)) == [(100000,)]
    history = query(database, "select SCHEMA.dashboard_activity(%s,25,1,%s)", (user, "' OR TRUE; --"))[0][0]
    assert history["data"] == [] and history["total"] == 0
    assert query(database, "select count(*) from SCHEMA.wallet_reservations where request_id=%s", (payload,)) == [(0,)]


def test_organizer_campaign_name_is_bound_data_not_sql(database, monkeypatch):
    import psycopg2

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    admin = importlib.import_module("hackathon_admin")
    url, schema = database
    payload = "Test'; DROP TABLE " + schema + ".wallets CASCADE; --"
    before = query(database, "select count(*) from SCHEMA.wallets")[0][0]

    class ScopedCursor(psycopg2.extensions.cursor):
        def execute(self, statement, args=None):
            # Redirect only the trusted SQL source to the isolated test schema.
            return super().execute(statement.replace("public.", schema + "."), args)

    with psycopg2.connect(url, sslmode="require", cursor_factory=ScopedCursor) as connection:
        assert admin.setup_campaign(connection, payload, ["SQL-001"]) == 1
    assert query(database, "select name from SCHEMA.hackathon_campaigns where name=%s", (payload,)) == [(payload,)]
    assert query(database, "select count(*) from SCHEMA.wallets")[0][0] == before
