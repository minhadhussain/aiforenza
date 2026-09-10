# $1.26 hold investigation — unresolved pending provider evidence

Request: `req_0c4667a644b044c3bc46e11e9f38e656`.
Created: **2026-09-10 20:26:59.522969 UTC**.
Owner: `3b229039-478e-48c9-9152-8eef348288ae`.
API key ID: `c3cddda7-d907-4191-82bb-a4b8129d1c86`.
Model ID: `766c75d2-93dd-4d55-95e4-eede0a1efcb9`.

## Findings

- The exact 126-cent reservation remains present.
- No `usage_records` row or `usage:<request_id>` transaction matches it.
- The general audit scanned 157 log/storage files plus OpenCode's SQLite
  message/part tables. Additional inspection included tools/*.log and overlapping
  original client messages from 20:26:40–20:28:40 UTC.
- Exact-ID matches in the local database are subsequent investigation references,
  not original upstream outcome evidence.
- A nearby original assistant message has `MessageAbortedError` and zero local
  counters, but no internal request ID. Client abortion and default zero counters
  do not establish that inference never consumed tokens.
- Nearby completed assistant messages have token counts but no reliable mapping
  to this held request. Do not attach those counts based only on timestamps.

## Decision

**No release, settlement, credit, or financial mutation performed.** The missing
provider outcome prevents evidence-backed reconciliation. The inspected wallet
is unchanged: **1,400 total / 126 reserved / 1,274 available USD cents**.
The original account retains its 14 holds totaling 480 cents.

## Evidence required

Provide a sanitized gateway/provider log export covering approximately
**2026-09-10 20:26:40–20:28:40 UTC**, with trustworthy correlation to this internal
request (or its upstream ID), terminal upstream status, and authoritative input,
cached-input and output usage if consumed. The current gateway did not retain an
upstream-ID mapping for this incident, so timestamps alone are insufficient.

If no inference occurred, use the existing owner-scoped audited release RPC with
the evidenced reason. If inference occurred, settle with the verified usage and
applicable price snapshot through the existing atomic charge path. If no matching
historical records exist, the hold cannot be resolved under the current
evidence-only policy; a new operator policy decision would be required, not an
invented provider rejection or fabricated wallet balance.

Azure resource logs only exist if diagnostic collection was configured at the
time. Enabling it now cannot reconstruct the missing outcome. An inference key
is not Azure Monitor workspace read authorization.

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/monitor-openai

`python tools/inspect_single_hold.py` performs only read-only inspection and
prints allowlisted metadata, fingerprints and IDs. It never prints message text,
credentials, full error messages, or raw OpenCode configuration.
