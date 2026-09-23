# GPT-6 Astra reasoning / OpenCode compatibility

## Root cause, traced rather than inferred

The installed OpenCode version is **1.18.30**, using the existing custom `aiforenza` provider and `@ai-sdk/openai-compatible`.

`tools/trace_astra_compat.py` captures the real SDK-generated HTTP request at a loopback diagnostic endpoint. It returns a deliberate 400 without calling a model or logging headers, credentials, or prompts. The trace showed:

- Existing configuration: `reasoning: false`, `options.reasoningEffort: "none"`, no variants.
- An explicitly selected variant serializes to **`reasoning_effort`**, not `reasoning.effort` or camelCase, in the actual Chat request.
- The SDK also sends `stream: true`, `max_tokens: 32000`, and function tools even for a text-only question.
- Low, medium, high, xhigh, and max all survive SDK serialization unchanged.

The break is in AI Forenza's previous integration: it suppressed reasoning to work around a provider restriction and then forwarded effort-enabled tool requests to Azure Chat Completions without capability-aware routing. The SDK's effort spelling is correct.

## Verified deployment behavior

The authoritative database row remains a single mapping:

```text
gpt-6-astra → Azure deployment gpt-6-astra
```

The configured Azure resource lists this model. Real responses report **`gpt-6-astra-2026-09-03`**. The adapter uses the resource's **`/openai/v1`** API, with no dated `api-version` query parameter.

Live probes established a distinction that matters for this deployment:

| Request | Azure result |
| --- | --- |
| Astra `medium`, no tools, Chat Completions | 200 |
| Astra `medium` with function tools, Chat Completions | 400, directs the caller to Responses |
| Astra `max`, no tools, Chat Completions | 400 `unsupported_value` |
| Astra `medium` or `max` with tools, Responses | 200, requested effort accepted |

The deployed Chat endpoint also accepted `none` in a diagnostic probe, despite the current documented Astra support set. AI Forenza intentionally rejects `none` and `minimal` according to the product contract; it does not depend on that undocumented compatibility behavior.

References:

- [Azure reasoning models and tool-calling requirements](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning)
- [OpenCode 1.18.30 provider transforms](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/provider/transform.ts)
- [OpenCode configuration schema](https://opencode.ai/config.json)

## Request path

```text
OpenCode selected variant
  → AI Forenza POST /v1/chat/completions
  → normal central API-key authentication
  → catalog capability validation, before reservation
  → existing wallet reservation
  → provider transport selected from catalog capabilities
  → Chat-compatible response/stream
  → existing actual-usage settlement and immutable ledger
```

The public API and provider configuration stay OpenAI-compatible. Clients keep their AI Forenza bearer key and base URL; Azure credentials remain server-side.

### Provider translation

- Tool-free Astra **low/medium/high/xhigh** uses Azure Chat Completions with unchanged `reasoning_effort`.
- Astra requests with tools/tool history, and **max** requests, use a narrowly scoped provider-only Responses bridge with the same value in `reasoning.effort`.
- GPT-5.6 Sol's latest OpenCode default (`medium` with tools) hits the same Azure restriction. That combination uses the shared bridge. Explicit Sol `none` and tool-free Sol requests retain Chat Completions routing.
- GPT-5.4 retains Chat Completions routing.
- The server chooses the transport before calling the provider. It never retries a rejected effort at a lower level.
- The bridge translates text messages, function definitions/choices, tool calls/results, token caps, and streaming events. It converts actual provider usage back into the existing Chat usage representation.

This is a stateless **text and function-tool subset**, verified by real OpenCode read-tool round trips. It is not a public Responses API or a claim of every Responses capability. Private/encrypted reasoning items are neither returned nor stored for replay. Cross-turn encrypted reasoning continuity, custom tools, images/audio, and legacy `functions` syntax are outside this adapter's supported subset.

### Validation and normalization

- Accepted effort representations: `reasoning_effort`, `reasoningEffort`, and `reasoning: { "effort": ... }`.
- Conflicting aliases and unsupported values receive a clean **400**, before any hold/provider request.
- Astra accepts exactly **low, medium, high, xhigh, max** and defaults to **medium**.
- Astra sampling controls `temperature` and `top_p` are omitted. Other arbitrary SDK extras are not blindly forwarded.
- Legacy `max_tokens` becomes `max_completion_tokens`, retaining existing precedence and limits; the bridge maps it to `max_output_tokens`.
- Function tool IDs, arguments, tool results, schemas, and tool choice remain associated across the round trip.
- Unsupported provider reasoning requests receive `provider_reasoning_unavailable`, without raw upstream error text or a silent downgrade.

## Authoritative registry and OpenCode configuration

Two forward migrations add/configure `models.capabilities`:

1. `202609130001_astra_capabilities.sql`
2. `202609130002_reasoning_transport.sql`

They have been applied to the configured development database. No model/deployment duplicates are created, and pricing, wallet data, and token limits are not rewritten.

The registry supplies Astra's five efforts, medium default, sampling support, provider transport requirements, and client timeout recommendation. `GET /v1/models` and the existing catalog serializers expose public capability metadata. Internal transport flags are excluded. Unspecified capabilities of other models are not advertised as false.

Limits retain the existing settings:

- OpenCode context: **128,000** tokens; input safety limit **90,000**; output cap **32,000**.
- Backend pricing-tier input/output limits: **190,000 / 32,768** tokens.

`tools/sync_opencode_models.py` generates Astra variants from the registry rather than maintaining its own effort list. The example in `docs/opencode.example.json` shows the resulting shape. The installed Desktop and global OpenCode configurations have been updated, retaining the existing provider, API key, base URL, and default model choices.

Long-horizon MAX calls exceeded the client's original timeout during verification. The registry therefore recommends **900,000 ms (15 minutes)** for OpenCode's request/chunk timeouts. Sync raises shorter timeouts to this value while preserving explicit unlimited (`false`) or longer settings. This does not change token reservations or pricing.

For other environments, apply both migrations, then with the API running:

```powershell
python tools/sync_opencode_models.py sync
python tools/configure_opencode_global.py install
```

**Quit and restart OpenCode** after changing configuration. Running sessions retain their previously loaded model definitions.

## Billing, reasoning tokens, and reservations

Pricing remains the existing centralized calculation using provider-reported input/output/cached tokens. Provider output totals already include reasoning tokens; the bridge does not add them twice or infer token costs from effort.

- **PAID:** existing 40% discount, before existing per-request cent rounding.
- **PROMOTIONAL:** reference charge, no discount.
- Reservation size remains based on input estimation and the requested maximum output, with no effort multiplier.
- Known pre-inference provider rejection releases its reservation.
- Timeouts, disconnects, missing usage, and uncertain streams retain holds.
- Stream completion is not emitted to the client before settlement succeeds.
- A response stopped by its output cap is translated as `finish_reason: "length"`; all reported output tokens are accounted for, even if reasoning consumed the cap before visible text.

## Safe diagnostics

The `aiforenza.provider` logger emits allowlisted metadata only:

```json
{
  "event": "provider_response",
  "request_id": "req_...",
  "model": "gpt-6-astra",
  "reasoning_effort": "xhigh",
  "provider_api": "responses",
  "provider": "azure",
  "provider_status": 200,
  "error_code": null
}
```

Settlement diagnostics include numeric usage, source, reference charge, and actual charge. They exclude headers, API keys, Azure credentials, arbitrary extra fields, raw provider errors, prompts, and reasoning text. Private reasoning fields/events are filtered from client responses too.

## Verification evidence

### Automated checks

The full backend suite passed **251 tests**, including real PostgreSQL and Redis integrations, with no skips. Six existing HTTPX deprecation warnings remain in Stripe tests.

The frontend TypeScript no-emit check and Next.js production build passed. Targeted Ruff checks and `git diff --check` also passed.

`test_astra_efforts.py` covers all five efforts, aliases, invalid values, conflicts, provider transport/payloads, defaults, sampling removal, streaming/tool fragmentation, private-reasoning filtering, provider rejection/timeout safety, output-cap exhaustion, actual-usage billing, both billing sources, safe diagnostics, and Sol/GPT-5.4 compatibility. Existing registry, chooser, and wallet tests are also exercised.

Commands from `apps/api`:

```powershell
$env:RUN_DATABASE_TESTS='1'
$env:RUN_REDIS_TESTS='1'
python -m pytest -q --tb=short
```

Frontend verification from the root:

```powershell
npx --workspace apps/web tsc --noEmit --incremental false
npm --workspace apps/web run build
```

### Actual OpenCode sessions

Each session selected `aiforenza/gpt-6-astra` with the real `--variant` option, read the synthetic code fixture through OpenCode's actual read tool, and produced a final answer. The provider logs confirmed the same effort and Azure **200** for both turns. Usage/debits and wallet deltas reconciled.

| Effort | Final request ID | Final output tokens | Final reference / paid cents | Whole session paid cents |
| --- | --- | ---: | ---: | ---: |
| low | `req_829301cac35c4031b4fafab1dc96fe36` | 37 | 1 / 1 | 3 |
| medium | `req_0bc47b9b426f4136ab3219bef8c98805` | 175 | 2 / 1 | 3 |
| high | `req_55139593a82d4b17a7f4c4e51bfe303f` | 333 | 3 / 2 | 4 |
| xhigh | `req_083353d9a36149b09e58d9bcfd62d3cd` | 709 | 5 / 3 | 5 |
| max | `req_55bf53f89cb04120beb3021df0e846e7` | 5,242 | 27 / 17 | 19 |

Discount calculations use unrounded price totals, then integer-cent rounding; rounded reference cents multiplied by 0.60 need not equal rounded paid cents.

The MAX long-horizon fixture needed more than the test's initial 4,096-token allowance. Its successful run used a 16,384-token test allowance, below the existing production output cap. No effort was reduced.

Real tool-free streaming also passed for all five efforts:

- low: `req_2e666b812afc40468663d166fef19705` — Chat Completions.
- medium: `req_b0458f52ca1a41ee9778cfd353040b64` — Chat Completions.
- high: `req_7028ee7287a0485cb1af72012679c5d2` — Chat Completions.
- xhigh: `req_ea6a672fb8164e1183977694c5eb6fb7` — Chat Completions.
- max: `req_f2330cb10a984e4e83ba4a07e1ddf6c5` — Responses bridge.

The Windows OpenCode TUI picker was opened, AI Forenza Astra selected, and Ctrl+T cycled through exactly **low/medium/high/xhigh/max**. Real GPT-5.4 and GPT-5.6 Sol read-tool sessions subsequently completed, with final requests `req_20dd7a22f00745559e38aa8f45f7cbfb` and `req_93125b7200c8489f8cea05a4e5753011` respectively.

Reproduction tools:

```powershell
python tools/trace_astra_compat.py
python tools/trace_astra_compat.py --probe
python tools/verify_opencode_picker.py --variants
python tools/verify_astra_efforts.py --logs "<API stderr log path>"
python tools/verify_astra_efforts.py --logs "<API stderr log path>" --efforts max --timeout 900 --output-tokens 16384
python tools/verify_astra_efforts.py --logs "<API stderr log path>" --plain
```

The CLI verifier uses read-only synthetic fixtures and the existing funded test account. Successful sessions preserve existing holds and reconcile actual debits. The `--probe` command makes small direct provider calls and prints only safe diagnostic metadata.

### Remaining reconciliation from verification

Two earlier MAX attempts lost their client connection before usage was available. Their **22-cent holds each (44 cents total)** remain deliberately retained:

- `req_539c5b602c114d8b96cfc09a32351dd6`
- `req_4e18a86e2781484387f8cd6820c055b3`

No inferred usage, manual credit, or unsafe release was used to conceal these uncertain outcomes. They require the existing operator/provider reconciliation process. The pre-existing 126-cent hold was untouched. The later successful MAX run and all subsequent verification runs added no unresolved holds.

## Exact files changed for this fix

Application:

- `apps/api/app/main.py`
- `apps/api/app/models/catalog.py`
- `apps/api/app/repositories/models.py`
- `apps/api/app/api/routes/chat.py`
- `apps/api/app/services/access_control.py`
- `apps/api/app/services/chat_completions.py`
- `apps/api/app/services/model_capabilities.py` (new)
- `apps/api/app/services/models.py`
- `apps/api/app/services/observability.py`
- `apps/api/app/services/provider_gateway.py`
- `apps/api/app/services/responses_compat.py` (new)
- `apps/api/app/services/usage_records.py`

Migrations:

- `supabase/migrations/202609130001_astra_capabilities.sql` (new)
- `supabase/migrations/202609130002_reasoning_transport.sql` (new)

Tests:

- `apps/api/tests/test_astra_efforts.py` (new)
- `apps/api/tests/test_astra_catalog.py`
- `apps/api/tests/test_account.py`
- `apps/api/tests/test_balance_decisions.py`
- `apps/api/tests/test_model_chooser.py`
- `apps/api/tests/test_opencode_payload.py`
- `apps/api/tests/test_wallet_database.py`

Tools and documentation:

- `tools/apply_reservations.py`
- `tools/sync_opencode_models.py`
- `tools/trace_astra_compat.py` (new)
- `tools/verify_astra_efforts.py` (new)
- `tools/verify_opencode_picker.py`
- `tools/fixtures/astra_effort_check.py` (new)
- `docs/opencode.example.json`
- `docs/astra-reasoning.md` (new)
- `README.md`

Local OpenCode configuration updated through the existing configuration tools:

- `C:\Users\minha\.config\opencode\opencode.json`
- `C:\Users\minha\OneDrive\Desktop\opencode.json`

The earlier Hackathon changes remain in the working tree and are not part of this Astra changed-file list.
