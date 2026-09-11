# AI Forenza model chooser

## One key, all enabled models — OpenCode scope repair

### If your JSON already lists Astra but the open terminal does not

The installed OpenCode 1.2.27 was checked through `debug config` with credentials
redacted in memory: the repository, Desktop and bug-bounty project all resolve
Astra with no whitelist/blacklist or provider exclusion. The saved model state
contains both direct `azure/gpt-6-astra` and `aiforenza/gpt-6-astra`; choose the
latter to use AI Forenza billing. `reasoning: false` controls capability, not
visibility. A GPT-5.4 default does not restrict the other available models.

A fresh **actual terminal picker** was opened using Windows ConPTY: `/models`
displayed GPT-6 Astra and AI Forenza before and after searching `astra`. No prompt
was submitted. The reported absence was not reproduced in a newly started client;
an existing session may have older loaded state or a different picker context.
Do not keep adding duplicate JSON entries or change pricing to address that.

To bypass old session state without deleting history, open a new terminal and run:

```powershell
opencode --model aiforenza/gpt-6-astra
```

This opens the interactive client with that model; it does not submit a paid
request. In an existing session, `/exit` then relaunch; `/new` alone is not a
process restart. Clear the `/models` search text and look under AI Forenza, not
the separate Azure provider. If it still differs, report the launch directory,
OpenCode version, and a cropped picker screenshot without prompts or credentials.

`tools/inspect_opencode_visibility.py` prints only allowlisted config diagnostics.
`tools/verify_opencode_picker.py` verifies the real Windows terminal picker using
optional `pywinpty==3.0.3`, makes no inference requests, and closes only its own test
process. No application runtime dependency or model JSON change was required.

**There is no dashboard model activation step.** Every active AI Forenza key can
request any enabled/priced backend model, subject to account balance and normal
request limits. Each request's `model` field determines routing. Dashboard usage
filters and public catalog selections are display-only, never authorization.

The actual OpenCode failure was reproduced from `D:\aiforenza`:
`opencode models aiforenza` returned **Provider not found**. The provider existed
only in `C:\Users\minha\OneDrive\Desktop\opencode.json`; the user-wide configuration
directory contained no `opencode.json`. A Desktop project config is not loaded
when starting from unrelated repositories.

The same existing provider/key and backend-enabled models are now configured in
`C:\Users\minha\.config\opencode\opencode.json`. Existing non-Forenza providers,
defaults and permissions are preserved. No backend model, key or wallet changes
were needed. The earlier overview selector was an incorrect UI fix and has been
removed entirely, along with its component and selection-dependent example.

Verification:
- `opencode models aiforenza` lists all four models from the repository, Desktop
  and home directories with no `OPENCODE_CONFIG` override.
- Actual OpenCode Astra request from a temporary empty directory, using only the
  global provider config: `req_3e771f0bbe1a4ae089a6d21a68c801b2`, normal text/stop,
  one 6-cent debit using the unchanged key ID. No dashboard visit or selection.
- Cash 1,399 → 1,393 cents; existing 126-cent hold unchanged; original account
  and its historical holds unchanged.
- Browser confirms no overview selector and shows all backend models in the
  read-only catalog. Same-key API tests switch across all four model IDs without
  loading any dashboard or storing any chosen model.

For other machines, merge `docs/opencode.example.json` into
`~/.config/opencode/opencode.json` (or `$XDG_CONFIG_HOME/opencode/opencode.json`),
set `AI_FORENZA_API_KEY` privately, and restart OpenCode. Do not overwrite unrelated
settings. Project configs and environment overrides can still override global
settings. This workstation uses its existing private key; no key is in Git.

`python tools/configure_opencode_global.py check` verifies the resolved model lists.
`install` is this workstation's guarded migration helper and preserves a private
backup; `run` performs a billable client check and must not be used as a free probe.

## Earlier dashboard/public visibility investigation (superseded UI approach)

Astra was **not missing from the authoritative registry** when this incident was
investigated: `/v1/models`, `/v1/dashboard/models`, Azure inventory and the desktop
OpenCode listing already contained it. No database insert, enable override, rate
change or duplicate entry was necessary.

Two presentation defects were fixed:
- Dashboard Get Started briefly gained a selector. This did not fix OpenCode
  provider loading and was removed in the scope repair above.
- Public `/models` offered Coding/Reasoning filters even though it assigned every
  model to General. Those fabricated categories hid all models when selected.
  They were removed; name/ID/provider search and backend prices are preserved.

Verified existing Astra row: `766c75d2-93dd-4d55-95e4-eede0a1efcb9`, public and
provider ID `gpt-6-astra`, provider `azure`, enabled and pricing-verified. Existing
reference input/output/cached rates remain **$10 / $50 / $1 per million tokens**,
with the unchanged 40% discount. Both public and authenticated catalog endpoints
use `fetch_enabled_models()` and its normal pricing-validity filter.

Chromium verified all four backend options, selected Astra, checked the generated
request's exact model ID, dashboard refresh, `/dashboard/models`, and public model
selection/search. The selected ID was used in one real API call through the
configured Azure gateway (no provider mock): request
`req_eab1b094877c439f980141f0f7ac1740`, HTTP 200, **10 input / 4 output tokens**,
one usage record and one **1-cent debit**. Wallet cash 1,400 → 1,399 cents; the
existing 126-cent hold and all original-account holds stayed unchanged.

Backend restart followed by API/browser/OpenCode listing checks passed. The full
registry was compared before/after and remained identical. **167 backend tests**
passed with PostgreSQL and Redis integration enabled; production frontend build
passed. No credential, Stripe, wallet, pricing or billing logic was modified.

Recheck read-only catalog visibility and absence of dashboard activation:
`python tools/verify_astra_chooser.py`.
Its `--request` option is explicitly side-effecting and guards against repeating
the recorded paid test. Restart OpenCode to load the repaired global provider.

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
