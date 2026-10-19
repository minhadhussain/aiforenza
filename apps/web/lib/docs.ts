export type DocSection = {
  heading: string;
  body: string;
  bullets?: string[];
  code?: string;
  widget?: "opencode-setup" | "opencode-quickstart";
  links?: ({ label: string; href: string } | { label: string; slug: string })[];
};

export type DocPage = {
  slug: string;
  title: string;
  summary: string;
  sections: DocSection[];
};

export const docsPages: DocPage[] = [
  {
    slug: "introduction",
    title: "Introduction",
    summary:
      "AI Forenza gives developers one OpenAI-compatible API for multiple frontier models through a prepaid balance and simple API key flow.",
    sections: [
      {
        heading: "What AI Forenza is",
        body:
          "AI Forenza is a developer-facing AI API platform. Instead of integrating separate providers one by one, you use one OpenAI-compatible endpoint, one API key, and a prepaid wallet balance to access multiple models.",
      },
      {
        heading: "Who this is for",
        body:
          "The platform is designed for developers and researchers who already understand how to work with OpenAI-compatible APIs and want a simpler path to multiple frontier models.",
        bullets: [
          "Coding assistants and agent workflows",
          "Python and JavaScript applications",
          "OpenCode and compatible Chat Completions clients; native Claude Code requires an adapter",
          "Research scripts and developer prototypes",
        ],
      },
      {
        heading: "Core workflow",
        body:
           "Start with your account and key, then connect your preferred client. Quickstart provides a copyable command that creates your OpenCode configuration automatically, followed by key connection and a first request.",
        bullets: [
          "Create an account",
          "Receive $5 in free API credit",
          "Generate an API key",
          "Choose a model in your client or API request—no dashboard activation",
          "Send OpenAI-compatible requests",
          "Top up balance when usage becomes real",
        ],
      },
      {
        heading: "Base URL",
        body:
          "All OpenAI-compatible model requests use the same API base URL.",
        code: `http://localhost:8000/v1`,
      },
      {
        heading: "What stays consistent",
        body:
          "The point of AI Forenza is to keep the application-side contract stable while model choice, routing, and pricing stay controlled by the platform. Your SDK usage pattern does not need to be reinvented just because the model behind the request changes.",
      },
    ],
  },
  {
    slug: "quickstart",
    title: "Quickstart",
    summary:
      "Generate an API key, paste one setup command, and connect OpenCode. Your models and reasoning settings are configured for you.",
    sections: [
      {
        heading: "1. Generate your API key",
        body:
          "Open API Keys and generate a personal key, or open BUILD 2026 and claim your organizer-issued Team ID for your project's shared promotional key. Copy and save the full key when it appears; it is shown only once. Already have a key? Continue to step 2.",
        links: [
          { label: "Generate an API key", href: "/dashboard/api-keys" },
          { label: "Claim BUILD 2026 credits", href: "/dashboard/build-2026" },
        ],
      },
      {
        heading: "2. Set up OpenCode with one paste",
        body:
          "Choose your terminal below, click Copy setup command, and paste the whole block. It downloads the current configuration and creates opencode.json in the right folder. If OpenCode is already running, quit it before setup and reopen afterward. Existing configurations can use the assistant merge prompt below.",
        widget: "opencode-quickstart",
      },
      {
        heading: "3. Connect your key and choose a model",
        body:
          "Run opencode in your terminal. Inside OpenCode, enter /connect, select AI Forenza, and paste your full API key. Then enter /models and select an AI Forenza model. Use Ctrl+T to choose a supported reasoning effort. The same key works across the available models.",
        code: "/connect\nSelect: AI Forenza → paste your full API key\n\n/models\nSelect: AI Forenza → GPT-6 Astra",
        links: [{ label: "Full OpenCode setup and troubleshooting", slug: "opencode" }],
      },
      {
        heading: "4. Send your first request",
        body:
          "Paste this short prompt into OpenCode. A reply containing OK confirms your configuration, key, and selected model work together. Then ask it to read a file in your project. Requests use the balance associated with your key; see Usage for the recorded tokens and charge.",
        code: "Reply with exactly OK.",
        links: [{ label: "View usage", href: "/dashboard/usage" }],
      },
      {
        heading: "Building an application? Use the same key",
        body:
          "AI Forenza also works with OpenAI-compatible SDKs and direct HTTP requests. Use your API key, the API base URL shown above, and a model ID from the catalog. Choose a guide for copyable request examples.",
        links: [
          { label: "Python SDK", slug: "python" },
          { label: "JavaScript SDK", slug: "javascript" },
          { label: "curl and Chat Completions", slug: "chat-completions" },
          { label: "Available models", slug: "models" },
        ],
      },
    ],
  },
  {
    slug: "authentication",
    title: "Authentication",
    summary:
      "The dashboard uses Supabase Auth sessions. The model API uses AI Forenza API keys.",
    sections: [
      {
        heading: "Dashboard authentication",
        body:
          "Log in with your account to access the dashboard. Dashboard routes are authenticated with your Supabase-backed session and are separate from the model API itself.",
      },
      {
        heading: "API authentication",
        body:
          "The model API uses bearer authentication with an AI Forenza API key.",
        code: `Authorization: Bearer sk_live_xxxxxxxxxxxxxxxx`,
      },
      {
        heading: "Example request headers",
        body:
          "A typical API request includes your bearer token and JSON content type.",
        code: `POST /v1/chat/completions\nAuthorization: Bearer sk_live_xxxxxxxxxxxxxxxx\nContent-Type: application/json`,
      },
      {
        heading: "Key lifecycle",
        body:
          "API keys are created inside the dashboard, can be named for different applications or tools, and can be revoked at any time. Revoked keys cannot call the model API.",
      },
      {
        heading: "Key storage",
        body:
          "Store your API key as you would any production secret. The dashboard shows the full secret only once when it is created. AI Forenza stores only a secure hash and a non-sensitive prefix for display.",
      },
    ],
  },
  {
    slug: "models",
    title: "Models",
    summary:
      "AI Forenza exposes enabled models through one consistent API surface.",
    sections: [
      {
        heading: "List available models",
        body:
          "Use GET /v1/models to retrieve the currently enabled model set in an OpenAI-compatible shape.",
        code: `GET http://localhost:8000/v1/models`,
      },
      {
        heading: "Example response",
        body:
          "Model listing follows the OpenAI-compatible list structure.",
        code: `{\n  "object": "list",\n  "data": [\n    {\n      "id": "gpt-5.6-sol",\n      "object": "model",\n      "owned_by": "your-platform"\n    }\n  ]\n}`,
      },
      {
        heading: "What the response means",
        body:
          "The response is designed for compatibility. Model IDs are the public slugs you use in requests, while AI Forenza handles internal provider and deployment mapping behind the scenes.",
      },
      {
        heading: "Current catalog",
        body:
          "The catalog is configuration-driven. Only enabled models with verified inference and reference pricing are returned by GET /v1/models. A planned model is not necessarily available; check the endpoint before selecting it. Luna is not an alias for Sol.",
        bullets: [
          "GPT-6 Astra",
          "GPT-5.6 Sol",
          "Grok 4.6",
          "GPT-5.4",
        ],
      },
      {
        heading: "Pricing note",
        body:
          "Customer pricing is model-driven and can differ across the catalog. The dashboard model views are designed to reflect backend-configured pricing rather than a single global rate.",
      },
    ],
  },
  {
    slug: "chat-completions",
    title: "Chat Completions",
    summary:
      "Send standard OpenAI-compatible chat completion requests through the AI Forenza API.",
    sections: [
      {
        heading: "Endpoint",
        body:
          "Use the standard chat completions path for synchronous and streaming requests.",
        code: `POST http://localhost:8000/v1/chat/completions`,
      },
      {
        heading: "Supported request fields",
        body:
          "Request options are normalized according to the selected model's backend capabilities.",
        bullets: ["model", "messages with text content", "max_completion_tokens (recommended) or max_tokens", "stream and stream_options.include_usage", "reasoning_effort for models advertising reasoning support", "tools and tool_choice where supported by the model"],
      },
      {
        heading: "Sample request body",
        body:
          "A minimal request body looks like this.",
        code: `{\n  "model": "gpt-5.6-sol",\n  "messages": [\n    {"role": "user", "content": "Hello"}\n  ],\n  "stream": false\n}`,
      },
      {
        heading: "What happens during a request",
        body:
          "AI Forenza validates the key and model, reserves a conservative maximum customer charge against available USD funds, calls the configured provider, captures authoritative usage, and atomically writes one usage record and ledger debit while removing the hold. Unused reserved capacity becomes available. Without an explicit output limit, 1,024 tokens are enforced. Text-only and one completion per request are currently supported; optional provider parameters vary by model.",
      },
      {
        heading: "Example request",
        body:
          "A minimal cURL example looks like this.",
        code: `curl http://localhost:8000/v1/chat/completions \\\n+  -H "Authorization: Bearer YOUR_API_KEY" \\\n+  -H "Content-Type: application/json" \\\n+  -d '{\n+    "model": "gpt-5.6-sol",\n+    "messages": [{"role": "user", "content": "Hello"}]\n+  }'`,
      },
      {
        heading: "Example response",
        body:
          "A successful response keeps the familiar OpenAI-compatible completion structure.",
        code: `{\n  "id": "chatcmpl_...",\n  "object": "chat.completion",\n  "choices": [\n    {\n      "index": 0,\n      "message": {\n        "role": "assistant",\n        "content": "Hello from AI Forenza"\n      },\n      "finish_reason": "stop"\n    }\n  ],\n  "usage": {\n    "prompt_tokens": 12,\n    "completion_tokens": 8,\n    "total_tokens": 20\n  }\n}`,
      },
    ],
  },
  {
    slug: "streaming",
    title: "Streaming",
    summary:
      "AI Forenza supports streaming because coding agents and developer tools often rely on incremental responses.",
    sections: [
      {
        heading: "Enable streaming",
        body:
          "Set stream: true in your chat completion request to receive an event-stream response compatible with common OpenAI tooling behavior.",
      },
      {
        heading: "Streaming request example",
        body:
          "A streaming request body differs only by the stream flag.",
        code: `{\n  "model": "gpt-5.6-sol",\n  "messages": [\n    {"role": "user", "content": "Hello"}\n  ],\n  "stream": true\n}`,
      },
      {
        heading: "Why streaming matters",
        body:
          "Developer tools and coding assistants often depend on streamed tokens for responsiveness, partial rendering, and tool-loop ergonomics.",
      },
      {
        heading: "Billing note",
        body:
          "Final provider usage is required for settlement. Missing or interrupted usage produces an error, not invented token counts or a successful zero charge. The wallet reservation remains held for operator reconciliation. The final DONE event is emitted only after settlement succeeds.",
      },
      {
        heading: "Example event stream lines",
        body:
          "A streamed response follows an SSE-style data sequence.",
        code: `data: {"id":"chatcmpl_...","choices":[{"delta":{"content":"Hello"},"index":0}]}\n\ndata: {"id":"chatcmpl_...","choices":[{"delta":{},"index":0,"finish_reason":"stop"}]}\n\ndata: [DONE]`,
      },
    ],
  },
  {
    slug: "claude-code",
    title: "Claude Code",
    summary:
      "Use AI Forenza as an OpenAI-compatible backend where your tooling accepts a base URL, API key, and model.",
    sections: [
      {
        heading: "Configuration values",
        body:
          "Native Claude Code uses the Anthropic Messages protocol, which this Chat Completions API does not implement. Do not point Claude Code directly at this endpoint or assume OPENAI_BASE_URL enables it. An explicitly supported protocol adapter is required; direct Claude Code compatibility is not yet verified.",
        code: `BASE URL\nhttp://localhost:8000/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-sol`,
      },
      {
        heading: "Recommended workflow",
        body:
          "Start with one model and confirm your prompt loop works, then switch models as needed without changing the rest of your integration pattern.",
      },
      {
        heading: "Practical setup notes",
        body:
          "Keep your key in an environment variable, pin one model first, and verify streamed completions if your coding flow depends on token-by-token output.",
      },
    ],
  },
  {
    slug: "opencode",
    title: "OpenCode setup and reasoning efforts",
    summary:
      "Generate a key, paste one setup command to create opencode.json, and connect AI Forenza. No manual JSON editing needed for a new installation.",
    sections: [
      {
        heading: "1. Get your AI Forenza key",
        body:
          "Sign up or log in to AI Forenza. Open API Keys and generate a personal key, or open BUILD 2026 and claim your organizer-issued Team ID to receive your project's shared promotional key. Save the full secret when it is first shown. If your team already shared its key with you, you can use that credential directly. No dashboard model activation is required.",
      },
      {
        heading: "2. Install OpenCode",
        body:
          "Install OpenCode with Node.js/npm if it is not already installed. If OpenCode is running, quit it before the next step so it loads the new configuration when reopened. Customers connect to the hosted AI Forenza API; the Local Setup guide is for developers running this service.",
        code: "npm install -g @opencode/cli",
      },
      {
        heading: "3. Create your configuration with one paste",
        body: "Choose Windows PowerShell or macOS / Linux, click Copy setup command, and paste it into your terminal. It finds OpenCode's configuration folder, downloads the current models and reasoning settings, and creates opencode.json. For an existing configuration, use Copy setup prompt to have a file-editing coding assistant merge the settings. Download and manual-copy options are also available below.",
        widget: "opencode-setup",
      },
      {
        heading: "4. Open OpenCode and paste your key",
        body: "Run opencode in your terminal. Enter /connect, select AI Forenza, and paste the full key you saved in step 1. OpenCode stores it in its native credential store. Older clients offer Other: enter the provider ID aiforenza exactly, then paste your key. If OpenCode was running during setup, fully quit and reopen it to load the provider.",
        code: "/connect\n\nProvider: AI Forenza\nAPI key: paste your full AI Forenza key at the secure prompt",
      },
      {
        heading: "5. Choose your model and reasoning effort",
        body: "Enter /models and select a model under AI Forenza. In the terminal UI, Ctrl+T cycles the effort shown beside the selected model in the prompt footer; it is not a separate model entry. GPT-5.4 offers none/low/medium/high/xhigh, Sol additionally offers max, and Astra offers low/medium/high/xhigh/max. Defaults follow the backend registry: GPT-5.4 none, Sol medium, Astra medium. Astra rejects none and minimal. Grok currently has no advertised effort variants. The live table above is authoritative.",
        code: "/models\n\nSelect: AI Forenza → GPT-6 Astra\nCtrl+T: cycle reasoning effort",
      },
      {
        heading: "6. Make a request and verify your setup",
        body: "Ask a short coding question first, then ask OpenCode to read a file in your project to check a tool-use round trip. The commands below are for OpenCode V2: --standalone starts a private server using this project's configuration, and #high selects the effort. V1 uses opencode models aiforenza and --variant high instead. Use a model and variant shown in your downloaded configuration. These requests use the credential stored through /connect.",
        code: 'opencode models --standalone\nopencode run --standalone --model aiforenza/gpt-6-astra "Reply with exactly OK."\nopencode run --standalone --model "aiforenza/gpt-6-astra#high" "Read README.md and summarize this project."',
      },
      {
        heading: "7. Understand effort, output limits, and billing",
        body: "The selected effort reaches the provider unchanged. AI Forenza accepts OpenCode's reasoning_effort and performs any model-specific provider translation behind the same public Chat Completions API. Higher effort can take longer and consume more reasoning/output tokens. Actual provider usage sets the bill; there is no fixed price per effort. Paid keys retain the 40% discount; BUILD 2026 shared keys spend promotional credit at reference price and never fall back to a personal wallet. Check the corresponding account's Usage page and the BUILD 2026 balance for shared-key usage.",
        bullets: [
          "Preflight reserves against the requested maximum output; choosing high or max does not add an effort multiplier.",
          "Reasoning tokens are already included in provider output usage. A small output cap can be consumed by reasoning before visible text; finish_reason=length indicates the cap was reached.",
          "Long MAX requests need sufficient output allowance and client timeout. The downloaded config includes the registry's timeout recommendation.",
          "Known provider rejections release holds. Timeouts or interrupted responses retain holds for reconciliation; inspect usage before retrying.",
        ],
      },
      {
        heading: "8. Troubleshoot connection and effort selection",
        body: "A model appearing in /models proves the configuration loaded, not that an API call succeeded. Diagnose the exact error and keep the request ID for support.",
        bullets: [
          "AI Forenza missing: confirm the provider ID is aiforenza in both /connect and provider.aiforenza, save the file in the correct scope, and restart OpenCode.",
          "Effort selector missing: choose an AI Forenza GPT model using /models, replace its stale definition with the current download, fully quit/restart OpenCode, then press Ctrl+T. Already running terminal/desktop/server instances cache model definitions. Project files and OPENCODE_CONFIG/OPENCODE_CONFIG_CONTENT can override global settings. Astra must not offer none/minimal; none is valid for GPT-5.4 and Sol.",
          "Astra keeps starting on Low: OpenCode remembers the last explicit effort per provider/model, and that choice overrides the configuration's Medium default. Choose Medium with Ctrl+T, or cycle back to Default to use the configured value. Selecting another model and returning preserves an explicit choice; downloading a config alone does not clear it.",
          "401: re-enter the correct AI Forenza key through /connect. Remove an old options.apiKey entry when using the saved credential; an environment placeholder or literal key can override it.",
          "402: check available funds for that key, including outstanding holds and its output allowance. A BUILD 2026 shared key can spend only its grant.",
          "Connection refused: localhost refers to your own computer. A remote customer needs the administrator's public HTTPS API URL ending in /v1, not the website's login URL or an Azure endpoint.",
          "400 unsupported_reasoning_effort: use an advertised variant. provider_reasoning_unavailable means the configured deployment rejected it; the server does not silently downgrade.",
          "429: back off. 502/503 or interrupted streams: inspect Usage before retrying because inference may have started.",
        ],
      },
    ],
  },
  {
    slug: "python",
    title: "Python",
    summary:
      "Use the OpenAI Python SDK with a custom base URL to send requests through AI Forenza.",
    sections: [
      {
        heading: "Python example",
        body:
          "Use the standard OpenAI SDK and override the base URL.",
        code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="http://localhost:8000/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-sol",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)`,
      },
      {
        heading: "Streaming example",
        body:
          "If you need incremental output, request a streamed response and iterate through events.",
        code: `stream = client.chat.completions.create(\n    model="gpt-5.6-sol",\n    messages=[{"role": "user", "content": "Hello"}],\n    stream=True,\n)\n\nfor event in stream:\n    print(event)`,
      },
      {
        heading: "Keep the client shape the same",
        body:
          "The goal is to avoid rewriting your application architecture. Your Python integration should continue to look like a normal OpenAI client configuration with only the endpoint and model choice changing.",
      },
    ],
  },
  {
    slug: "javascript",
    title: "JavaScript",
    summary:
      "Use the OpenAI JavaScript SDK with the AI Forenza base URL in Node or server-side JavaScript apps.",
    sections: [
      {
        heading: "JavaScript example",
        body:
          "Use the OpenAI JavaScript SDK with a custom baseURL.",
        code: `import OpenAI from "openai"\n\nconst client = new OpenAI({\n  apiKey: process.env.AI_FORENZA_API_KEY,\n  baseURL: "http://localhost:8000/v1",\n})\n\nconst response = await client.chat.completions.create({\n  model: "gpt-5.6-sol",\n  messages: [{ role: "user", content: "Hello" }],\n})`,
      },
      {
        heading: "Streaming example",
        body:
          "Streaming works through the same request surface.",
        code: `const stream = await client.chat.completions.create({\n  model: "gpt-5.6-sol",\n  messages: [{ role: "user", content: "Hello" }],\n  stream: true,\n})\n\nfor await (const chunk of stream) {\n  console.log(chunk)\n}`,
      },
      {
        heading: "Server-side recommendation",
        body:
          "Keep your API key on the server side where possible. AI Forenza should be integrated the same way you would treat any sensitive third-party API credential.",
      },
    ],
  },
  {
    slug: "errors",
    title: "Errors",
    summary:
      "AI Forenza normalizes common failures into OpenAI-compatible error responses where practical.",
    sections: [
      {
        heading: "Common errors",
        body:
          "The MVP uses a small set of predictable error responses so developer tooling can handle failures cleanly.",
        bullets: [
          "401 invalid API key",
          "402 insufficient balance",
          "404 model not found",
          "429 rate limited",
          "502/503 provider unavailable",
        ],
      },
      {
        heading: "Insufficient balance example",
        body:
          "When AVAILABLE balance is below the conservative maximum customer charge, AI Forenza rejects before provider forwarding. Check key ownership, reserved funds and output-token allowance. Creating a fresh key does not create a fresh wallet; funds on another account do not apply.",
        code: `{\n  "error": {\n    "message": "Insufficient balance. Please add funds to continue.",\n    "type": "insufficient_balance",\n    "code": "insufficient_balance"\n  }\n}`,
      },
      {
        heading: "Model not found example",
        body:
          "If a requested model slug is not enabled, the API returns a model lookup error.",
        code: `{\n  "error": {\n    "message": "Model 'not-a-real-model' not found.",\n    "type": "invalid_request_error",\n    "code": "model_not_found"\n  }\n}`,
      },
      {
        heading: "Error handling guidance",
        body:
          "401: check/revoke/replace the key as appropriate. 402: verify available funds on its owner account; do not retry blindly. 429: back off. 502/503: retain the request ID and inspect usage before retrying because uncertain provider outcomes may retain holds. Browser Failed to fetch can indicate CORS or an offline backend. SUPABASE_URL errors require checking the root environment and stopping stale dev processes, not adding funds.",
      },
    ],
  },
  {
    slug: "usage-billing",
    title: "Usage & Billing",
    summary:
      "AI Forenza uses a prepaid wallet and immutable transactions to track balance and billable usage.",
    sections: [
      {
        heading: "Wallet model",
        body:
          "Personal API keys share their owner's paid USD-cent wallet. Each BUILD 2026 shared key resolves only to its promotional grant wallet. Total is the ledger balance; reserved is outstanding request capacity; available is total minus reserved. API authorization and dashboard balances use the same database logic. Never release an uncertain hold merely because it is old.",
      },
      {
        heading: "Ledger and usage records",
        body:
          "Every balance change creates a transaction entry, and every billable request creates a usage record. Those records allow debugging, reconciliation, and a consistent customer-facing usage history.",
      },
      {
        heading: "Find your requests",
        body: "Open Dashboard → Usage. The page shows the signed-in email/account ID, each request ID, API-key name/ID (never the secret), model, UTC timestamp, measured tokens and charges. Filter by model/key/status and page through history. Refresh usage returns to the latest page; visible tabs poll every 15 seconds with backoff on errors, and refresh on focus. The overview shows only four recent billed requests. If a model is missing, confirm the dashboard account owns the key used in OpenCode.",
      },
      {
        heading: "Billed versus operational activity",
        body: "Completed · billed comes from settled usage. In progress / unsettled comes from an outstanding reservation and may need reconciliation; a hold is not a charge. Rejected · no inference records authenticated preflight rejections from the activity rollout onward. Released · not billed comes from the existing audited release records. Unknown tokens/charges are shown as not recorded/not billed, never fabricated as zero usage. Anonymous, malformed, oversized pre-authentication requests and older unrecorded failures are not a complete activity history.",
      },
      {
        heading: "Request-size and pricing limits",
        body: "HTTP transport size is capped separately at 1,000,000 bytes by default. Pricing admission uses the larger of two tokenizer estimates, plus 25% and framing overhead; this is a surrogate, not a guaranteed exact model tokenizer. The reservation still uses at least the prior UTF-8 upper budget, so estimates do not reduce concurrency-spending protection. Actual provider usage alone determines the charge. A limit rejection reports input/output estimates and limits; compact or start a new session rather than top up to fix a size error. The OpenCode template uses a 90,000-token input target and early compaction; unusual Unicode or tool-heavy requests can still need manual compaction.",
      },
      {
        heading: "Usage record shape",
        body:
          "A recorded usage entry includes the request identifier, token counts, final customer charge, and status.",
        code: `{\n  "request_id": "req_01abc...",\n  "input_tokens": 1200,\n  "output_tokens": 800,\n  "cached_input_tokens": 200,\n  "customer_charge_cents": 11,\n  "status": "completed"\n}`,
      },
      {
        heading: "Pricing",
        body:
          "Paid usage applies the current 40% discount: customer = reference × 0.60 before rounding. BUILD 2026 promotional usage is charged at reference price, with no discount or paid-wallet fallback. Input, output and cached-input rates are model-specific; cached input is a subset of total input and billed once. Totals round upward once per request to integer cents. The upfront hold is not the final bill, and effort selection never replaces actual-token billing.",
      },
      {
        heading: "Top-ups",
        body:
          "Choose $10, $25, $50, $100, $500 or $1,000 in Billing. Stripe collects domestic INR using a live server FX quote; the wallet receives the chosen USD package value. Complete Checkout and 3DS, then wait for the signed paid webhook. A success URL never credits funds by itself. Confirm COMPLETED plus one TOPUP transaction and the updated available balance. Use Refresh balance and top-ups rather than paying twice.",
      },
    ],
  },
  {
    slug: "local-setup",
    title: "Local Setup",
    summary: "Start the app and the payment listener separately, using one consistent account and origin.",
    sections: [
      { heading: "1. Configure dependencies and environment", body: "Use the repository docs/SETUP-AND-TOPUPS.md for installation and migrations. Backend secrets live only in root .env. Next uses apps/web/.env.local with NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/v1 and public Supabase settings. Never expose Azure, Stripe or service-role keys in NEXT_PUBLIC variables." },
      { heading: "2. Start Docker and the application", body: "Start Docker Desktop first. From the repository root run the command below. It starts local Next/FastAPI and Docker Redis, rejects duplicate ports and validates backend configuration. Keep this terminal open.", code: "npm run dev" },
      { heading: "3. Start Stripe forwarding", body: "In a second terminal run the payment listener below. It requires the Stripe CLI, the backend test key and the matching webhook signing secret. It validates the match without printing secrets. This separate listener must remain running for local top-ups to credit. Production instead needs a registered HTTPS webhook endpoint.", code: "npm run dev:payments" },
      { heading: "4. Use one origin", body: "Open http://127.0.0.1:3000 and configure NEXT_PUBLIC_APP_URL/Supabase redirect URLs consistently. localhost and 127.0.0.1 have different browser cookies. Do not run duplicate Next processes on 3001 or an old API on 8001. A health 200 or login redirect is not proof an authenticated dashboard works." },
    ],
  },
  {
    slug: "topup-troubleshooting",
    title: "Top-up Troubleshooting",
    summary: "A Checkout URL is not a payment. Follow the payment, webhook, ledger and account identity to locate missing funds.",
    sections: [
      { heading: "Exact customer steps", body: "Log in to the account that owns the API key → Billing → choose a USD package → Add funds → finish Stripe Checkout and required authentication → return to Billing → wait for Payment verified → confirm COMPLETED and one TOPUP transaction → continue using the same key. No key regeneration is required." },
      { heading: "Creating Checkout through the API", body: "POST /v1/billing/create-checkout-session takes a dashboard session bearer token and a package ID. The response contains checkout_url, session_id, USD package value and INR collection amount. Open checkout_url and finish payment. This endpoint does not charge a card or credit funds by itself.", code: '{ "package_id": "starter_10" }' },
      { heading: "Payment pending", body: "If Stripe says open/unpaid, finish Checkout; no credit is due yet. If Stripe says paid but AI Forenza says PENDING, support must check the signed webhook delivery, secret, backend/migrations and original event, then resend it. Do not create a second payment merely to make the first appear." },
      { heading: "Different account or reservations", body: "A top-up credits its signed-in owner account, not every API key on your machine. Compare dashboard identity and API-key owner. Total may increase while available remains lower because of reserved funds. New keys on the same account share those holds; uncertain holds require authoritative reconciliation." },
      { heading: "Local test card only", body: "In Stripe test mode, use Indian Visa 4000003560000008, a future expiry and test CVC, then complete test 3DS. Keep the webhook listener running. Never test with a real card or a live Stripe secret. Test-mode payments move no real money." },
      { heading: "Verified checkpoint and limits", body: "On 2026-09-10 a real hosted test checkout collected INR 950.90 for USD 10.00 credit, wallet 4.93 → 14.93; original and repeated signed webhook deliveries returned 200 with exactly one credit. Subsequent streaming/non-streaming API calls left 14.91 and no holds. Browser confirmation/refresh/cancel checks passed. Rates and balances are snapshots, not promises. Live production payments and refund automation are not certified by this test." },
    ],
  },
];

// Examples follow the public API endpoint configured for this environment.
const exampleBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1";
for (const page of docsPages) {
  for (const section of page.sections) {
    if (section.code) section.code = section.code.replaceAll("http://localhost:8000/v1", exampleBaseUrl).replace(/\n\+/g, "\n");
  }
}
export const docsPageMap = Object.fromEntries(docsPages.map((page) => [page.slug, page])) as Record<string, DocPage>;
