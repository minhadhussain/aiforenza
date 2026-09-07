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
    summary: "AI Forenza gives developers one OpenAI-compatible API for multiple frontier models through a prepaid balance and simple API key flow.",
    sections: [
      {
        heading: "What it is",
        body: "AI Forenza is a developer-facing API platform. You sign up, receive starter credit, generate an API key, choose a model, and send OpenAI-compatible requests through one endpoint.",
      },
      {
        heading: "Core workflow",
        body: "The MVP is intentionally simple and optimized for developers who already understand AI APIs.",
        bullets: [
          "Create an account",
          "Receive $5 in free API credit",
          "Generate an API key",
          "Choose a model",
          "Send requests through one API",
          "Top up balance when usage becomes real",
        ],
      },
    ],
  },
  {
    slug: "quickstart",
    title: "Quickstart",
    summary: "Go from signup to first request in minutes using one API key and one OpenAI-compatible base URL.",
    sections: [
      {
        heading: "1. Create an account",
        body: "Sign up for AI Forenza and log in to your dashboard.",
      },
      {
        heading: "2. Generate an API key",
        body: "Create an API key from the dashboard. The full secret is shown only once.",
      },
      {
        heading: "3. Use the OpenAI-compatible endpoint",
        body: "Point your existing tooling at the AI Forenza base URL.",
        code: `https://api.YOURDOMAIN.com/v1`,
      },
      {
        heading: "4. Make your first request",
        body: "Choose a model such as `gpt-5.6-luna` and send a standard chat completion request.",
        code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.YOURDOMAIN.com/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)\n\nprint(response.choices[0].message.content)`,
      },
    ],
  },
  {
    slug: "authentication",
    title: "Authentication",
    summary: "The dashboard uses Supabase Auth sessions. The model API uses AI Forenza API keys.",
    sections: [
      {
        heading: "Dashboard authentication",
        body: "Log in with your account to access the developer dashboard, wallet, transactions, usage, and API key management.",
      },
      {
        heading: "API authentication",
        body: "Use an AI Forenza API key in the Authorization header when calling model endpoints.",
        code: `Authorization: Bearer sk_live_xxxxxxxxxxxxxxxx`,
      },
      {
        heading: "Key handling",
        body: "API keys are shown in full only once when created. Store them securely on your side. AI Forenza stores only a hash and a displayable prefix.",
      },
    ],
  },
  {
    slug: "models",
    title: "Models",
    summary: "AI Forenza exposes enabled models through one consistent API surface.",
    sections: [
      {
        heading: "Model listing",
        body: "Use `GET /v1/models` to see currently enabled models in an OpenAI-compatible format.",
        code: `GET https://api.YOURDOMAIN.com/v1/models`,
      },
      {
        heading: "Current catalog",
        body: "The initial catalog includes GPT, Grok, DeepSeek, and Kimi variants while preserving a consistent request format across models.",
      },
    ],
  },
  {
    slug: "chat-completions",
    title: "Chat Completions",
    summary: "Send standard OpenAI-compatible chat completion requests through the AI Forenza API.",
    sections: [
      {
        heading: "Endpoint",
        body: "Use the OpenAI-compatible chat completions endpoint.",
        code: `POST https://api.YOURDOMAIN.com/v1/chat/completions`,
      },
      {
        heading: "Supported request fields",
        body: "The MVP supports standard request fields including model, messages, temperature, max_tokens or max_completion_tokens, and stream.",
      },
      {
        heading: "Example",
        body: "A minimal request looks like this.",
        code: `curl https://api.YOURDOMAIN.com/v1/chat/completions \\\n+  -H "Authorization: Bearer YOUR_API_KEY" \\\n+  -H "Content-Type: application/json" \\\n+  -d '{\n+    "model": "gpt-5.6-luna",\n+    "messages": [{"role": "user", "content": "Hello"}]\n+  }'`,
      },
    ],
  },
  {
    slug: "streaming",
    title: "Streaming",
    summary: "AI Forenza supports streaming because coding agents and developer tools often rely on incremental responses.",
    sections: [
      {
        heading: "Enable streaming",
        body: "Set `stream: true` in your chat completion request to receive a streamed response.",
      },
      {
        heading: "Billing note",
        body: "Usage is captured after final provider usage information becomes available. When full usage is not returned, AI Forenza uses a safe fallback estimate rather than silently charging zero.",
      },
    ],
  },
  {
    slug: "claude-code",
    title: "Claude Code",
    summary: "Use AI Forenza as an OpenAI-compatible backend where your tooling accepts a base URL, API key, and model.",
    sections: [
      {
        heading: "Configuration",
        body: "Point Claude Code-compatible OpenAI settings to AI Forenza.",
        code: `BASE URL\nhttps://api.YOURDOMAIN.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
      },
    ],
  },
  {
    slug: "opencode",
    title: "OpenCode",
    summary: "Use AI Forenza with OpenCode through the same OpenAI-compatible interface pattern.",
    sections: [
      {
        heading: "Configuration",
        body: "Set the base URL, key, and model exactly as you would for an OpenAI-compatible endpoint.",
        code: `BASE URL\nhttps://api.YOURDOMAIN.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
      },
    ],
  },
  {
    slug: "python",
    title: "Python",
    summary: "Use the OpenAI Python SDK with a custom base URL to send requests through AI Forenza.",
    sections: [
      {
        heading: "Python example",
        body: "Example using the standard OpenAI SDK.",
        code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.YOURDOMAIN.com/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)`,
      },
    ],
  },
  {
    slug: "javascript",
    title: "JavaScript",
    summary: "Use the OpenAI JavaScript SDK with the AI Forenza base URL in Node or server-side JavaScript apps.",
    sections: [
      {
        heading: "JavaScript example",
        body: "Use the same request shape as a normal OpenAI-compatible client.",
        code: `import OpenAI from "openai"\n\nconst client = new OpenAI({\n  apiKey: process.env.AI_FORENZA_API_KEY,\n  baseURL: "https://api.YOURDOMAIN.com/v1",\n})\n\nconst response = await client.chat.completions.create({\n  model: "gpt-5.6-luna",\n  messages: [{ role: "user", content: "Hello" }],\n})`,
      },
    ],
  },
  {
    slug: "errors",
    title: "Errors",
    summary: "AI Forenza normalizes common failures into OpenAI-compatible error responses where practical.",
    sections: [
      {
        heading: "Common errors",
        body: "The MVP uses a small set of predictable error responses.",
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
        body: "When the wallet balance is too low, the request is rejected before provider forwarding.",
        code: `{\n  "error": {\n    "message": "Insufficient balance. Please add funds to continue.",\n    "type": "insufficient_balance",\n    "code": "insufficient_balance"\n  }\n}`,
      },
    ],
  },
  {
    slug: "usage-billing",
    title: "Usage & Billing",
    summary: "AI Forenza uses a prepaid wallet and immutable transactions to track balance and billable usage.",
    sections: [
      {
        heading: "Wallet model",
        body: "Every developer account has one wallet. Usage charges are deducted from the wallet after requests are measured and recorded.",
      },
      {
        heading: "Ledger and usage records",
        body: "Every balance change has a corresponding transaction, and every billable request creates a usage record.",
      },
      {
        heading: "Top-ups",
        body: "Prepaid top-ups use Stripe Checkout and are credited only after verified webhook processing.",
      },
    ],
  },
];

export const docsPageMap = Object.fromEntries(docsPages.map((page) => [page.slug, page])) as Record<string, DocPage>;
