# OpenCode customer setup and effort selection

The customer-facing guide is available at `/docs/opencode` and `/dashboard/docs/opencode`. It includes a live model/effort table, copyable configuration, a download button, and troubleshooting instructions.

## Customer steps

1. Sign up/sign in to AI Forenza. Generate a personal API key in **API Keys**, or claim your organizer-issued Team ID in **Hackathon** and save the shared promotional key. A teammate with an existing shared key can use that credential directly.
2. Install OpenCode (`npm install -g opencode-ai`) and run `opencode`.
3. Enter `/connect`, select **Other**, enter **aiforenza** as the provider ID, and paste the key. This stores the credential in OpenCode's native auth store.
4. Open the OpenCode guide in AI Forenza's Docs and download `opencode.json`. Save it at `%USERPROFILE%\.config\opencode\opencode.json` on Windows, or `~/.config/opencode/opencode.json` on macOS/Linux. For an existing configuration, merge the provider and review defaults rather than replacing unrelated settings.
5. Quit and restart OpenCode, then use `/models` to select **AI Forenza → GPT-6 Astra** (or another listed model).
6. Use the effort selector / default **Ctrl+T** shortcut. The selected effort is shown beside the model in the prompt footer. GPT-5.4 offers **none, low, medium, high, xhigh** (default **none**); Sol adds **max** (default **medium**); Astra offers **low, medium, high, xhigh, max** (default **medium**). Grok currently has no advertised effort variants.
7. Send a short prompt, then ask OpenCode to read a project file. Inspect **Dashboard → Usage** for its request/charge. A hackathon key spends only its promotional grant.

The download intentionally contains no `options.apiKey`. An old literal key or environment placeholder can override `/connect` credentials; remove that override when using native credential storage. Project configuration can override the global file, so inspect the actual project directory if models/efforts differ after restart.

## Existing installation: selector missing

The missing GPT-5 selectors were caused by absent `reasoning`/variant metadata for GPT-5.4 and Sol. Migration `202609230001_opencode_gpt5_efforts.sql` adds verified capabilities, preserves the provider defaults, and routes Sol max to the existing Responses bridge. Astra's five-level contract is unchanged. The configured Azure deployments were probed: GPT-5.4 rejects max, while Sol accepts max through Responses.

For an existing local installation, run `python tools/refresh_opencode_configs.py` with the API available. It refreshes the existing global/Desktop AI Forenza model definitions, preserving keys, base URLs, unrelated providers, smaller limits, and valid user-selected default efforts. It does not start or restart services.

Then **fully quit and reopen OpenCode**, use `/models` to select a model under **AI Forenza**, and press **Ctrl+T**. A running terminal, desktop app, or OpenCode server retains its old model definitions until restarted. Identically named models under another provider use that provider's configuration.

## Astra starts on Low instead of the Medium default

OpenCode keeps two separate settings: the configured default (`options.reasoningEffort`, Medium for Astra) and the last explicitly selected variant, stored in its state directory's `model.json`. A remembered Low selection wins over the configured default when switching away and back.

The earlier picker verification cycled variants in the normal user profile and could leave Low saved. The verifier now always uses a temporary `XDG_STATE_HOME`, explicitly selects the real Default option, and checks the saved selection rather than merely searching the menu for labels.

In the current OpenCode UI, choose Medium with Ctrl+T, or cycle back to Default to use the registry default. To repair the stale remembered Low from a terminal, **close OpenCode first**, then from this repository run:

```powershell
python tools/reset_astra_effort.py
```

Reopen OpenCode afterward. The command changes only a saved `aiforenza/gpt-6-astra: low` entry to `default`; it preserves other models and explicit non-Low choices. A still-running client can write its cached Low choice back, so editing the state while that client remains open is not a reliable reset. Low remains available when intentionally selected; the API never silently upgrades it to Medium.

### Default and model smoke verification

`python tools/verify_model_defaults.py` creates one temporary key and a short-lived local test API in the verification process. It uses the real Supabase, Redis, provider, usage, and ledger implementations without restarting the developer's API/web stack. The key is revoked in `finally`, and a subsequent authenticated model-list request must return 401.

The final live run passed non-streaming and streaming requests for **GPT-5.4, GPT-5.6 Sol, GPT-6 Astra, and Grok 4.6**. A fresh OpenCode TUI selected Default for Astra and sent Medium (`req_fd88595fd24d4176b7926fa01a37ae51`); explicitly selecting Low sent Low (`req_9bd2973429454466aaab9f0bbe053ca7`) and remained selected after switching models. Ten requests settled for 16 cents, with matching ledger/wallet deltas and no new holds. The temporary key was revoked and rejected with 401.

Regression checks for this repair: **353 backend tests passed**, including PostgreSQL and Redis; the frontend production build/type-check and targeted Ruff checks passed.

An initial Grok non-streaming attempt returned 502. Both the focused retry and the final whole-model run passed. The initial request's one-cent hold (`req_268c4c11d4b846a18d3e5b270a43a6ad`) remains for reconciliation under the existing uncertain-outcome policy; no usage or refund was invented to clear it. Its test key was also revoked.

## Server configuration

`GET /v1/public/opencode-config` is public and returns an OpenCode configuration attachment with `Cache-Control: no-store`. It uses the same enabled, verified-price model repository as model discovery/inference. It does not contain secrets, dashboard sessions, wallet IDs, or Azure deployment identifiers.

`NEXT_PUBLIC_API_BASE_URL` configures the advertised API URL. Set it consistently in the API and web environments. Production exports require HTTPS and reject loopback URLs; URLs with embedded credentials, query parameters, or fragments are rejected. The service never builds the advertised URL from the request's Host header or client query parameters.

The local development endpoint is not usable by remote customers. Deploy the API behind a reachable HTTPS URL ending in `/v1` before distributing customer configuration. The UI explicitly identifies a local development configuration.

`app/services/opencode_config.py` is shared by the public export and the existing local model-sync tool. Supported variants/defaults come from `models.capabilities`; the frontend does not maintain a second effort list or assume native built-in OpenCode registration. Existing conservative token limits and reasoning timeout recommendations are preserved.

The public API remains Chat Completions with the existing model-specific provider bridge. Actual provider usage still determines paid/promotional charges, and existing reservation safety applies. This setup work changes neither pricing nor financial RPCs.

## Verification

Verified with **OpenCode 1.18.32**:

- Fresh isolated XDG config/data/cache/state directories and an initially empty native credential store.
- A newly created test API key entered through the real TUI `/connect → Other → aiforenza` prompt.
- Downloaded configuration installed without `apiKey` or provider environment overrides.
- Restarted model discovery, actual model picker, and all five Astra effort labels.
- Actual streamed read-tool round trips using the saved credential, with matching API-key IDs, provider effort/status logs, actual usage prices, and ledger/wallet reconciliation.

| Model / effort | Final request | Whole flow paid charge |
| --- | --- | ---: |
| Astra low | `req_8fb3010f756748b18d15999ceed4b011` | 3 cents |
| Astra medium | `req_b4abc2937e4b4d95bacea976bf489f25` | 3 cents |
| Astra high | `req_446f08c9c86a4310bcec30640ca5b8f5` | 3 cents |
| Astra xhigh | `req_c5269d4f64314bcabee42d8bb5da41e6` | 4 cents |
| Astra max | `req_531e0c8ed3c2482f855f912723c8a05b` | 4 cents |
| GPT-5.4 | `req_4c420d4e358c4f9e9453739dccafdc54` | 3 cents |
| GPT-5.6 Sol | `req_cd082ea0c94c41e8981e6b6510acc44a` | 3 cents |

Every flow received provider 200 responses and preserved the pre-existing holds. Test keys were revoked. An earlier run interrupted by local infrastructure loss was stopped; its orphaned test key was revoked with no related holds. A full-file fingerprint check also detected an original profile change during one run; the verifier now separately checks that the test credential never escapes its isolated profile and reports concurrent original-file changes without overwriting them. The final setup-only isolation rerun reported no original-file changes.

After the GPT-5 metadata fix, all five GPT-5.4 efforts and all six Sol efforts completed real streamed OpenCode read-tool round trips using a newly saved native credential. Each request had provider status 200, matching effort diagnostics, correct actual-token charges, and preserved holds. The terminal selector was independently verified for GPT-5.4, Sol, and Astra in the installed configuration.

Representative final requests: GPT-5.4 xhigh `req_e34dffce4fc4422ba43917be052d2414`; Sol max `req_8308569af9e24f86861d3caa17e5f885`.

Final backend checks: **308 tests passed** (including PostgreSQL/Redis). The **11 frontend auth tests**, TypeScript no-emit check, production frontend build, and targeted Ruff/diff checks also passed. Public and authenticated docs, downloaded/clipboard JSON equality, advertised efforts, and unavailable-config recovery passed in a real browser.

Reproduce from the repository root:

```powershell
python tools/verify_opencode_docs.py
python tools/verify_opencode_onboarding.py
python tools/verify_opencode_onboarding.py --requests --logs "<safe API stderr log>"
```

The request verifier uses the existing funded test identity and creates its own revocable key. It does not print keys, user prompts, or raw terminal transcripts containing the key. It can clean up only its own orphaned test keys with `--cleanup`; that operation never releases financial holds.
