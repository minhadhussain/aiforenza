# SQL and database-filter injection prevention

## Scope and conclusion

Reviewed the FastAPI database repositories, financial/usage RPCs, organizer SQL, and the frontend data-access boundary. The application uses Supabase/PostgREST and JSON RPC arguments; the organizer tool uses psycopg2 bound parameters. No remotely exploitable raw-SQL injection was demonstrated in these reviewed paths.

The changes harden query construction and validation against SQL/filter injection and reduce database error disclosure. They do not replace the existing financial architecture or introduce a SQL-keyword blacklist.

## Changes

### Database endpoint and mutation boundaries

`apps/api/app/repositories/supabase_rest.py:16–26` accepts only fixed-shape table/RPC resource paths. Embedded query strings, fragments, encoded path tricks, SQL punctuation, and absolute URLs are rejected before database HTTP I/O.

`supabase_rest.py:52–67` passes mutation filters through HTTPX's encoded `params` mapping. PATCH operations require an explicit nonempty `id=eq.…` target; unfiltered/broad-operator PATCH calls fail closed. The supported mutation methods are the POST/PATCH methods used by current repositories.

API-key revocation, key last-used updates, and top-up attachment now use this structured interface in `repositories/api_keys.py` and `repositories/topups.py`. They previously interpolated IDs into URL query strings. Existing public UUID validation and trusted database IDs limited the reachability of this weakness, but a raw fragment such as `#` at an internal call site could truncate subsequent query parameters. Structured encoding keeps the entire ID as a value and preserves the separate owner filter.

**URL encoding protects the PostgREST query structure. SQL parameter binding protects SQL execution.** These are separate controls; encoding is not a substitute for SQL parameterization.

### Input validation

- `apps/api/app/models/openai.py:17–19` bounds model IDs to 1–160 characters using the same identifier character set already supported by dashboard model filters.
- `apps/api/app/repositories/profiles.py:9–21` validates/canonicalizes the UUID before querying the profile table or constructing the Auth administration path.
- Existing UUID route parameters, Team ID validation, and typed PostgreSQL RPC parameters remain in effect.

SQL text in prompts and names is deliberately permitted. An API-key name containing an apostrophe or a coding prompt containing `SELECT`/`DROP` remains data; it is not stripped or treated as executable SQL.

### Database error disclosure

`supabase_rest.py:94–107` no longer forwards arbitrary database messages, details, or hints through public error paths. Exact allowlisted PostgreSQL business errors are retained for existing insufficient-balance and hackathon claim handling. SQL syntax errors, schema details, and constraint values receive a fixed repository error message instead.

### Existing SQL controls retained

- Financial and activity RPCs compare/insert typed parameters using static SQL. JSON RPC values are not interpolated into SQL text.
- Organizer campaign names use psycopg2 `%s` binding (`tools/hackathon_admin.py:32–44`).
- Migration-time dynamic SQL uses application-owned identifiers and PostgreSQL `%I` formatting. It is not constructed from public request data.
- Local read-only reconciliation tools restrict table/column choices to fixed internal names and bind data values.
- RLS, ownership checks, privileged-RPC grants, immutable ledger constraints, and reservation/idempotency behavior are preserved.

## Verification

`apps/api/tests/test_query_safety.py` covers:

- Encoded `&`, `#`, logical-filter strings, percent-encoded separators, quotes, and SQL-shaped values.
- Preservation of the owner filter during API-key revocation.
- Rejection of unsafe resource paths and unfiltered/broad PATCH requests before I/O.
- JSON-only RPC arguments and SQL-looking insert values.
- Early rejection of malformed model/profile identifiers.
- Preservation of legitimate SQL coding prompts.
- Database-error redaction and unchanged insufficient-balance/claim error codes.

`apps/api/tests/test_query_safety_database.py` executes SQL-shaped request IDs, filters, and campaign names against the real application SQL/RPC implementations in a random isolated PostgreSQL schema. It verifies exact literal storage, one usage debit, correct wallet deltas, unchanged other-user balances, consumed reservations, no filter broadening, and intact tables.

The complete backend suite passed **350 tests**, including PostgreSQL and Redis integrations. One earlier isolated test setup hit a transient Supabase SSL connection failure; its retry and the subsequent full suite passed. No production injection payloads or live financial changes were used for these tests.

## Rules for future database access

1. Keep table names, RPC names, selected columns, ordering, and filter operators application-owned. Never forward an entire client query dictionary to the service-role database client.
2. Put PostgREST filter values in `params` and RPC arguments in JSON. Do not concatenate values into endpoint paths.
3. Bind SQL values with the driver's parameter mechanism. If identifiers must vary, select them from a closed allowlist and use the driver's identifier-quoting API or PostgreSQL `%I`.
4. Keep authorization/tenant ownership explicit. Injection prevention does not replace RLS or ownership checks.
5. Do not use ad-hoc quote replacement, keyword rejection, or disabled validation as an injection defense.

This is a focused query-boundary review, not a certification of every security property of the system. The installed `/security-review` workflow can be used for a broader assessment.
