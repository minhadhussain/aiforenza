"""Apply the reviewed forward migration with Supabase migration history tracking."""

from pathlib import Path
import psycopg2
import sys
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
env = dotenv_values(root / ".env")
filename = sys.argv[1] if len(sys.argv) > 1 else "202609090001_wallet_reservations.sql"
if filename not in {
    "202609090001_wallet_reservations.sql",
    "202609090002_payment_credit_safety.sql",
    "202609090003_catalog_reference_prices.sql",
    "202609100001_wallet_availability.sql",
}:
    raise SystemExit("Unsupported migration")
version = filename.split("_", 1)[0]
name = filename.split("_", 1)[1].removesuffix(".sql")
sql = (root / "supabase/migrations" / filename).read_text()
try:
    with psycopg2.connect(
        env["DATABASE_URL"], sslmode="require", connect_timeout=10
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("set lock_timeout='5s'; set statement_timeout='30s'")
            cursor.execute(
                "select version from supabase_migrations.schema_migrations where version=%s",
                (version,),
            )
            if cursor.fetchone():
                print("Migration already applied:", name)
            else:
                cursor.execute(sql.replace("commit;", ""))
                cursor.execute(
                    "insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)",
                    (version, name, [sql]),
                )
                if "--validate-only" in sys.argv:
                    connection.rollback()
                    print("Migration validated and rolled back:", name)
                else:
                    print("Migration applied atomically:", name)
except psycopg2.Error as error:
    print("Migration failed; PostgreSQL code:", error.pgcode)
    raise SystemExit(1)
