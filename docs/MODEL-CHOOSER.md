# AI Forenza model chooser

The desktop OpenCode configuration and `opencode.example.json` now expose:

| OpenCode selector | Display name |
| --- | --- |
| `aiforenza/gpt-5.4` | GPT-5.4 (unchanged default) |
| `aiforenza/gpt-5.6-sol` | GPT-5.6 Sol |
| `aiforenza/gpt-6-astra` | GPT-6 Astra |
| `aiforenza/grok-4.6` | Grok 4.6 |

Restart OpenCode in the directory containing the updated `opencode.json`, enter
`/models`, and choose one of those entries. `opencode models aiforenza` lists all
four. The existing API key, base URL, default model and small-model choice were
preserved. The previous config is backed up in the Git-ignored private test state.

## What was actually added

The three additional models were already enabled and priced in AI Forenza's
database; they were missing from the desktop chooser. No catalog prices or Azure
settings were changed. Both `/v1/models` and OpenCode's actual model listing now
agree on these four entries. The public `/docs/opencode` example was updated too.

Azure's `/models` returned 432 identifiers, including model versions, image/audio/
embedding models, and models that previously failed inference. This is **not**
proof that all 432 are usable or priced through this Chat Completions service.
Luna, DeepSeek and Kimi were not silently enabled. Additional deployments require
verified routing, supported request/usage behavior and reviewed reference pricing.

## Compatibility

- Sol and Astra require `max_completion_tokens`, like GPT-5.4. The backend now
  translates legacy `max_tokens` for those three models, preserving the same
  allowance/precedence used by wallet preflight. Grok's behavior is unchanged.
- Astra rejects function tools with reasoning enabled. Its OpenCode entry sets
  `reasoning: false` and `options.reasoningEffort: "none"`. The AI SDK converts
  that option to the upstream `reasoning_effort` field. Keep this setting when
  using tools; do not infer that every reasoning variant supports tool calls.
- Client limits now include a 90,000 input target with 128,000 context / 32,000 output,
  plus auto/prune compaction and a 16,000-token buffer. See [USAGE-ACTIVITY.md](USAGE-ACTIVITY.md)
  for the admission-estimator limitations and the later verified long-request fix.
  These limits are
  constrained to the backend's current verified pricing bands. They are not
  claims about each provider's full maximum capacity.

## Verification checkpoint

- Sol, Astra and Grok: real streaming API HTTP 200 with a tool definition,
  authoritative usage, one usage record and charge each, no leaked reservations.
- Actual OpenCode Astra run: exit 0; `step_start`, `text`, `step_finish`; stop.
  Request `req_980fa727aa5144779dc6ae43468b1899`, debit 6 cents.
- Test wallet after the checks: 1,446 cents available, no holds. This is a snapshot;
  ongoing requests will change it. No manual wallet adjustments were made.
- Original account's historical wallet and holds stayed unchanged during checks.
- Earlier client verification attempts timed out without recorded usage or holds;
  only the final successful run is claimed as real OpenCode completion evidence.

`python tools/sync_opencode_models.py check` is a read-only chooser check.
`sync` updates this workstation's desktop config from the enabled/priced backend
catalog and preserves a private backup. The helper is workstation-specific, not
a general Azure deployment importer. `smoke`, `diagnose`, and `client_check` make
real inference calls and must not be used as free health checks.

References: [OpenCode models](https://opencode.ai/docs/models/),
[AI SDK compatible-provider options](https://ai-sdk.dev/providers/openai-compatible-providers).
