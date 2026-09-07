"use client";

import { useMemo, useState } from "react";

const examples = {
  OpenCode: {
    label: "OpenCode",
    snippet: `BASE URL\nhttps://api.yourdomain.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
    code: `provider = "openai"\nbase_url = "https://api.yourdomain.com/v1"\napi_key = "YOUR_API_KEY"\nmodel = "gpt-5.6-luna"`,
  },
  "Claude Code": {
    label: "Claude Code",
    snippet: `BASE URL\nhttps://api.yourdomain.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
    code: `export OPENAI_BASE_URL="https://api.yourdomain.com/v1"\nexport OPENAI_API_KEY="YOUR_API_KEY"\nexport OPENAI_MODEL="gpt-5.6-luna"`,
  },
  Python: {
    label: "Python",
    snippet: `BASE URL\nhttps://api.yourdomain.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
    code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.yourdomain.com/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)`,
  },
  JavaScript: {
    label: "JavaScript",
    snippet: `BASE URL\nhttps://api.yourdomain.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
    code: `import OpenAI from "openai"\n\nconst client = new OpenAI({\n  apiKey: process.env.AI_FORENZA_API_KEY,\n  baseURL: "https://api.yourdomain.com/v1",\n})\n\nconst response = await client.chat.completions.create({\n  model: "gpt-5.6-luna",\n  messages: [{ role: "user", content: "Hello" }],\n})`,
  },
  cURL: {
    label: "cURL",
    snippet: `BASE URL\nhttps://api.yourdomain.com/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-luna`,
    code: `curl https://api.yourdomain.com/v1/chat/completions \\\n+  -H "Authorization: Bearer YOUR_API_KEY" \\\n+  -H "Content-Type: application/json" \\\n+  -d '{\n+    "model": "gpt-5.6-luna",\n+    "messages": [{"role": "user", "content": "Hello"}]\n+  }'`,
  },
} as const;

const tabNames = Object.keys(examples) as Array<keyof typeof examples>;

export function DeveloperTabs() {
  const [active, setActive] = useState<keyof typeof examples>("Python");
  const current = useMemo(() => examples[active], [active]);

  return (
    <div className="rounded-[2rem] border border-[var(--border)] bg-[rgba(12,14,18,0.9)] p-3 shadow-[var(--shadow)] backdrop-blur">
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tabNames.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActive(tab)}
            className={`whitespace-nowrap rounded-full border px-4 py-2 text-sm transition ${
              active === tab
                ? "border-white/20 bg-white text-black"
                : "border-white/8 bg-white/[0.03] text-[var(--muted)] hover:border-white/16 hover:text-white"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="grid gap-4 p-3 lg:grid-cols-[0.92fr_1.08fr]">
        <div className="rounded-[1.5rem] border border-white/8 bg-[#0b0d10] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Configuration</p>
              <h3 className="mt-2 font-[family-name:var(--font-heading)] text-lg text-white">{current.label}</h3>
            </div>
            <button className="rounded-full border border-white/8 px-3 py-1 text-xs text-[var(--muted)] transition hover:border-white/16 hover:text-white">
              Copy
            </button>
          </div>
          <pre className="whitespace-pre-wrap text-sm leading-7 text-[#d8dde6]">{current.snippet}</pre>
        </div>

        <div className="rounded-[1.5rem] border border-white/8 bg-[#090b0d] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">OpenAI-Compatible Request</div>
            <button className="rounded-full border border-white/8 px-3 py-1 text-xs text-[var(--muted)] transition hover:border-white/16 hover:text-white">
              Copy
            </button>
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap text-sm leading-7 text-[#edf1f7]">{current.code}</pre>
        </div>
      </div>
    </div>
  );
}
