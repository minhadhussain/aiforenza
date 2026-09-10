# Usage visibility and pricing-limit repair

## User steps

1. Open `/dashboard/usage` and check **Signed in as** and **Account ID**.
   OpenCode's key and the dashboard must belong to the same account. Accounts are
   never merged or made mutually visible to solve this problem.
2. Filter by model, API-key name/ID, and status. Key IDs are identifiers, not secret
   API keys. UTC timestamps include time; request IDs identify individual attempts.
3. **Refresh usage** returns to the newest page. The visible page refreshes every
   15 seconds and on focus; hidden tabs pause, errors back off to two minutes,
   overlapping requests are prevented, and stale responses are discarded.
4. Page through older history using Previous/Next and 10/25/50/100 rows. The
   `as_of` anchor excludes newer requests while paging; it is not a frozen MVCC
   snapshot across calls. In-flight status transitions can still move a row.
5. The overview remains a four-row billed-usage preview, with a refresh control;
   use the full Usage page for rejected and unsettled requests.

## Status meanings and coverage

| Status | Source | Billing meaning |
| --- | --- | --- |
| Completed · billed | `usage_records` | Authoritative measured usage and charge |
| In progress / unsettled | outstanding reservation or noncompleted usage | Held capacity, not proof of final consumption |
| Released · not billed | audited reservation release | No debit for that released request |
| Rejected · no inference | new authenticated preflight rejection audit | No inference/charge for this attempt |

Rejected/released/unsettled rows do not invent token counts. Old unrecorded
rejections cannot be reconstructed. Invalid keys, malformed bodies and transport
413 responses before authentication are intentionally not attributed to an account.
Rejection auditing is best-effort: an audit failure is logged by request ID but
does not turn a safe rejection into a retryable billing error. Current hold and
settled-usage records override lower-priority operational records for the same ID.

The new table contains IDs, model relation, status code and controlled error code
only—no prompt, response body, key hash, plaintext key, headers or arbitrary error
message. The history RPC and table are service-role-only with RLS. Every branch
of the history query scopes to the authenticated owner; key-name joins also check
ownership. Filter values cannot change the target account.

## Deployment

- Install updated backend requirements (`tiktoken==0.12.0` added).
- Apply `202609110001_request_activity.sql` after the existing wallet migrations.
  It adds operational storage and read-only reporting; it does not modify wallet,
  usage, ledger or historical reservation rows.
- This workstation's migration has been applied and schema cache refreshed.
- Restart the backend and frontend. Local `API_MAX_REQUEST_BYTES` was updated to
  1,000,000; configure reverse-proxy body limits accordingly when deploying.
- Restart OpenCode after updating JSON. The desktop config and template now have
  `limit.input=90000`, auto/prune compaction and a 16,000-token reserved buffer.
  Existing key/default model choices and lower custom limits are preserved.

## Pricing fix and limits

Previously, the full serialized UTF-8 byte count was compared to a token pricing
limit, rejecting valid long conversations. The HTTP cap of 200,000 bytes also
conflicted with the advertised client context.

Admission now counts the serialized request with `o200k_base` and `cl100k_base`,
takes the larger count, adds 25% plus message overhead, and compares that estimate
to the unchanged model pricing limits. It includes tool definitions/results and
extra request fields. These are **surrogate encodings** for deployments without
a published exact tokenizer, not exact counts or promises of full context capacity.
Unknown models or tokenizer-loading failures fall back to the conservative byte
budget. Encodings download on first use; warm/cache them in deployment environments.

Crucially, **reservation pricing still uses the larger of the old UTF-8 budget
and the new estimate**. The guard does not reserve less money based on a heuristic.
Actual provider usage must still remain within the authorized tier, match the
reservation, and settle through the existing atomic RPC. Missing/out-of-tier usage
requires reconciliation, never fabricated charges or automatic release.

The separate default HTTP body cap is now 1 MB, still enforced before JSON parsing.
The 100-message bound remains. There is no universal bytes/token ratio, so the
client input target reduces common false rejections but cannot guarantee every
Unicode/tool-heavy request fits. Error messages now report the input estimate,
output allowance and limits, without content. `/compact` or `/new` may still be
needed; existing long sessions are not retroactively compacted by editing JSON.

## Real end-to-end evidence

- Sol streaming request: `req_3471295bf90a4226b599baf887676a12`.
- Old byte-based input budget: **216,590**, which exceeded 190,000.
- New conservative token admission estimate: **67,966**.
- Upfront reference/customer maximum: **87 / 53 cents** (unchanged conservative
  capacity methodology, not the final debit).
- Actual Azure usage: **54,024 input / 5 output**; one **13-cent** debit.
- Browser already open on Usage displayed the completed request via polling,
  with correct model, key ID, measured usage and billed status.
- Output-oversized request `req_eecec967398a43fdb38b1c19fd26c773` rejected with 400,
  appeared as rejected/not billed, and created no usage debit.
- Browser model/key/status filters, pagination, manual refresh, simulated hidden
  visibility pause and focus/visibility refresh all passed. No key secret rendered.
- Authenticated API attempt to filter by the original account's key returned no
  foreign records or key identity. Database tests verify service-role-only access.
- Test wallet: **1,413 → 1,400 cents** cash. Its **pre-existing 126-cent hold**
  `req_0c4667a644b044c3bc46e11e9f38e656` remains untouched: available **1,274 cents**.
  No new hold leaked. This existing hold is unresolved and is now visible as such.
- Original account unchanged: **492 total / 480 reserved / 12 available cents**,
  with all 14 historical reservation rows preserved.

No Stripe, FX, Azure configuration, model prices or 40% discount changes were made
in this repair. The pricing repair does not resolve historical uncertain inference.

## Final validation

- **162 backend tests passed** with real PostgreSQL isolated-schema tests and
  Redis integration enabled; six existing HTTPX deprecation warnings remain.
- Frontend production build and TypeScript checks passed.
- Additional read-only Chromium checks verified the existing $1.26 unsettled
  hold, released/not-billed rows, last-good-data preservation during a simulated
  HTTP 503, recovery, and clearing results on a simulated HTTP 401. These error
  responses were browser-test interceptions, not a claimed actual auth outage.
- Authenticated dashboard/usage/key pages returned 200; dashboard independently
  displayed **$12.74 available / $14.00 total / $1.26 reserved**.
- No secrets were rendered; local credentials/config backups remain Git-ignored.
- No commit or push was made for this repair.
