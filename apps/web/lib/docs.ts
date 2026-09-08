export type DocSection = {
  heading: string;
  body: string;
  bullets?: string[];
  code?: string;
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
          "OpenCode, Claude Code, and Cline-style tooling",
          "Research scripts and developer prototypes",
        ],
      },
      {
        heading: "Core workflow",
        body:
          "The MVP intentionally focuses on the shortest route from account creation to real API usage.",
        bullets: [
          "Create an account",
          "Receive $5 in free API credit",
          "Generate an API key",
          "Choose a model",
          "Send OpenAI-compatible requests",
          "Top up balance when usage becomes real",
        ],
      },
      {
        heading: "Base URL",
        body:
          "All OpenAI-compatible model requests use the same API base URL.",
        code: `https://api.YOURDOMAIN.com/v1`,
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
      "Go from signup to first request in minutes using one API key and one OpenAI-compatible base URL.",
    sections: [
      {
        heading: "1. Create an account",
        body:
          "Sign up for AI Forenza and log in to the dashboard. New accounts receive starter API credit automatically.",
      },
      {
        heading: "2. Generate an API key",
        body:
          "Open the dashboard and create an API key. The full key is shown only once, so store it immediately in your local environment or secret manager.",
      },
      {
        heading: "3. Set the base URL",
        body:
          "Point your existing OpenAI-compatible tooling to the AI Forenza endpoint.",
        code: `https://api.YOURDOMAIN.com/v1`,
      },
      {
        heading: "4. Choose a model",
        body:
          "Start with one of the enabled models such as gpt-5.6-luna or another model from the catalog.",
      },
      {
        heading: "5. Make your first request",
        body:
          "A minimal Python example using the OpenAI SDK looks like this.",
        code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.YOURDOMAIN.com/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)\n\nprint(response.choices[0].message.content)`,
      },
      {
        heading: "6. Expected response shape",
        body:
          "Responses follow the OpenAI chat completion structure where practical.",
        code: `{\n  "id": "chatcmpl_...",\n  "object": "chat.completion",\n  "choices": [\n    {\n      "index": 0,\n      "message": {\n        "role": "assistant",\n        "content": "Hello"\n      },\n      "finish_reason": "stop"\n    }\n  ],\n  "usage": {\n    "prompt_tokens": 12,\n    "completion_tokens": 8,\n    "total_tokens": 20\n  }\n}`,
      },
      {
        heading: "7. Watch your balance",
        body:
          "Successful requests consume wallet balance. When your balance runs low, use the dashboard to add prepaid funds and continue using the same API key and endpoint.",
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
        code: `GET https://api.YOURDOMAIN.com/v1/models`,
      },
      {
        heading: "Example response",
        body:
          "Model listing follows the OpenAI-compatible list structure.",
        code: `{\n  "object": "list",\n  "data": [\n    {\n      "id": "gpt-5.6-luna",\n      "object": "model",\n      "owned_by": "your-platform"\n    }\n  ]\n}`,
      },
      {
        heading: "What the response means",
        body:
          "The response is designed for compatibility. Model IDs are the public slugs you use in requests, while AI Forenza handles internal provider and deployment mapping behind the scenes.",
      },
      {
        heading: "Current catalog",
        body:
          "The initial catalog includes GPT, Grok, DeepSeek, and Kimi variants while preserving a single request interface across models.",
        bullets: [
          "GPT-6 Astra",
          "GPT-5.6 Sol",
          "GPT-5.6 Luna",
          "Grok 4.6",
          "DeepSeek V4 Pro",
          "DeepSeek V4 Flash",
          "Kimi K2.7 Code",
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
        code: `POST https://api.YOURDOMAIN.com/v1/chat/completions`,
      },
      {
        heading: "Supported request fields",
        body:
          "The MVP supports the fields most existing developer tooling expects.",
        bullets: ["model", "messages", "temperature", "max_tokens or max_completion_tokens", "stream"],
      },
      {
        heading: "Sample request body",
        body:
          "A minimal request body looks like this.",
        code: `{\n  "model": "gpt-5.6-luna",\n  "messages": [\n    {"role": "user", "content": "Hello"}\n  ],\n  "stream": false\n}`,
      },
      {
        heading: "What happens during a request",
        body:
          "AI Forenza validates your API key, checks the requested model, confirms balance, creates an internal request ID, forwards the request to the provider path, captures usage, calculates the charge, deducts the wallet, records usage, and returns the response.",
      },
      {
        heading: "Example request",
        body:
          "A minimal cURL example looks like this.",
        code: `curl https://api.YOURDOMAIN.com/v1/chat/completions \\\n+  -H "Authorization: Bearer YOUR_API_KEY" \\\n+  -H "Content-Type: application/json" \\\n+  -d '{\n+    "model": "gpt-5.6-luna",\n+    "messages": [{"role": "user", "content": "Hello"}]\n+  }'`,
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
        code: `{\n  "model": "gpt-5.6-luna",\n  "messages": [\n    {"role": "user", "content": "Hello"}\n  ],\n  "stream": true\n}`,
      },
      {
        heading: "Why streaming matters",
        body:
          "Developer tools and coding assistants often depend on streamed tokens for responsiveness, partial rendering, and tool-loop ergonomics.",
      },
      {
        heading: "Billing note",
        body:
          "Usage is captured after final provider usage information becomes available. If a streaming configuration does not return reliable usage, AI Forenza uses a safe fallback estimate rather than silently charging zero.",
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
          "Where Claude Code or an OpenAI-compatible configuration surface is available, set the AI Forenza base URL, API key, and chosen model.",
        code: `BASE URL\nhttps://api.YOURDOMAIN.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
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
    title: "OpenCode",
    summary:
      "Use AI Forenza with OpenCode through the same OpenAI-compatible interface pattern.",
    sections: [
      {
        heading: "Configuration values",
        body:
          "Set the base URL, key, and model exactly as you would for an OpenAI-compatible endpoint.",
        code: `BASE URL\nhttps://api.YOURDOMAIN.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
      },
      {
        heading: "Why this works",
        body:
          "AI Forenza is designed around OpenAI-compatible request and response behavior, so existing tooling can connect without learning a custom application protocol.",
      },
      {
        heading: "Integration pattern",
        body:
          "Treat AI Forenza as the API layer between your tool and the enabled model catalog. The important configuration surface remains base URL, bearer key, and model slug.",
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
        code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.YOURDOMAIN.com/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)`,
      },
      {
        heading: "Streaming example",
        body:
          "If you need incremental output, request a streamed response and iterate through events.",
        code: `stream = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[{"role": "user", "content": "Hello"}],\n    stream=True,\n)\n\nfor event in stream:\n    print(event)`,
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
        code: `import OpenAI from "openai"\n\nconst client = new OpenAI({\n  apiKey: process.env.AI_FORENZA_API_KEY,\n  baseURL: "https://api.YOURDOMAIN.com/v1",\n})\n\nconst response = await client.chat.completions.create({\n  model: "gpt-5.6-luna",\n  messages: [{ role: "user", content: "Hello" }],\n})`,
      },
      {
        heading: "Streaming example",
        body:
          "Streaming works through the same request surface.",
        code: `const stream = await client.chat.completions.create({\n  model: "gpt-5.6-luna",\n  messages: [{ role: "user", content: "Hello" }],\n  stream: true,\n})\n\nfor await (const chunk of stream) {\n  console.log(chunk)\n}`,
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
          "When the wallet balance is too low, AI Forenza rejects the request before sending it to the model provider.",
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
          "Treat insufficient balance and invalid API keys as account-state issues. Treat provider-unavailable errors as upstream or transient failures that may merit retry handling depending on your application.",
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
          "Every developer account has one wallet. Usage charges are deducted from that wallet after requests are measured and recorded. Balance is represented in integer cents, not floating-point values.",
      },
      {
        heading: "Ledger and usage records",
        body:
          "Every balance change creates a transaction entry, and every billable request creates a usage record. Those records allow debugging, reconciliation, and a consistent customer-facing usage history.",
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
          "Customer-facing pricing is model-driven rather than hard-coded globally. Different models can have different input and output rates while still sharing the same API contract.",
      },
      {
        heading: "Top-ups",
        body:
          "Prepaid top-ups are handled through Stripe Checkout and the wallet is credited only after verified webhook processing. Frontend redirect alone is not treated as payment confirmation.",
      },
    ],
  },
];

export const docsPageMap = Object.fromEntries(docsPages.map((page) => [page.slug, page])) as Record<string, DocPage>;
