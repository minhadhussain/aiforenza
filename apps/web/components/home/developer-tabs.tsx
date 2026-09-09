"use client";

import { useMemo, useState } from "react";

const examples = {
  OpenCode: {
    label: "OpenCode",
    snippet: `BASE URL\nhttp://localhost:8000/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-sol`,
    code: `provider = "openai-compatible"\nbase_url = "http://localhost:8000/v1"\napi_key = "YOUR_API_KEY"\nmodel = "gpt-5.6-sol"`,
  },
  "Claude Code": {
    label: "Claude Code",
    snippet: `BASE URL\nhttp://localhost:8000/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-sol`,
    code: `export OPENAI_BASE_URL="http://localhost:8000/v1"\nexport OPENAI_API_KEY="YOUR_API_KEY"\nexport OPENAI_MODEL="gpt-5.6-sol"`,
  },
  Python: {
    label: "Python",
    snippet: `BASE URL\nhttp://localhost:8000/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-sol`,
    code: `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="http://localhost:8000/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-sol",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)`,
  },
  JavaScript: {
    label: "JavaScript",
    snippet: `BASE URL\nhttp://localhost:8000/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-sol`,
    code: `import OpenAI from "openai"\n\nconst client = new OpenAI({\n  apiKey: process.env.AI_FORENZA_API_KEY,\n  baseURL: "http://localhost:8000/v1",\n})\n\nconst response = await client.chat.completions.create({\n  model: "gpt-5.6-sol",\n  messages: [{ role: "user", content: "Hello" }],\n})`,
  },
  cURL: {
    label: "cURL",
    snippet: `BASE URL\nhttp://localhost:8000/v1\n\nAPI KEY\nsk_live_••••••••••\n\nMODEL\ngpt-5.6-sol`,
    code: `curl http://localhost:8000/v1/chat/completions \\\n+  -H "Authorization: Bearer YOUR_API_KEY" \\\n+  -H "Content-Type: application/json" \\\n+  -d '{\n+    "model": "gpt-5.6-sol",\n+    "messages": [{"role": "user", "content": "Hello"}]\n+  }'`,
  },
} as const;

const tabNames = Object.keys(examples) as Array<keyof typeof examples>;

export function DeveloperTabs() {
  const [active, setActive] = useState<keyof typeof examples>("Python");
  const current = useMemo(() => {
    const example = examples[active];
    const normalize = (text: string) => text.replaceAll("gpt-5.6-sol", "gpt-5.6-sol")
      .replaceAll("http://localhost:8000/v1", process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1")
      .replace(/\n\+/g, "\n");
    return { ...example, snippet: normalize(example.snippet), code: normalize(example.code) };
  }, [active]);

  return (
    <div
      className="smooth-border rounded-[2rem] bg-[rgba(12,14,18,0.9)] p-3 shadow-[var(--shadow)] backdrop-blur"
      style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}
    >
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tabNames.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActive(tab)}
            className={`smooth-border whitespace-nowrap rounded-full px-4 py-2 text-sm transition ${
              active === tab
                ? "bg-white text-black"
                : "bg-white/[0.03] text-[var(--muted)] hover:text-white"
            }`}
            style={{ ["--smooth-border-color" as string]: active === tab ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.08)" }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="grid gap-4 p-3 lg:grid-cols-[0.92fr_1.08fr]">
        <div
          className="smooth-border rounded-[1.5rem] bg-[#0b0d10] p-5"
          style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}
        >
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Configuration</p>
              <h3 className="mt-2 font-[family-name:var(--font-heading)] text-lg text-white">{current.label}</h3>
            </div>
            <button
              className="smooth-border rounded-full px-3 py-1 text-xs text-[var(--muted)] transition hover:text-white"
              style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}
            >
              Copy
            </button>
          </div>
          <pre className="whitespace-pre-wrap text-sm leading-7 text-[#d8dde6]">{current.snippet}</pre>
        </div>

        <div
          className="smooth-border rounded-[1.5rem] bg-[#090b0d] p-5"
          style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}
        >
          <div className="mb-4 flex items-center justify-between">
            <div className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">OpenAI-Compatible Request</div>
            <button
              className="smooth-border rounded-full px-3 py-1 text-xs text-[var(--muted)] transition hover:text-white"
              style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}
            >
              Copy
            </button>
          </div>
          <pre className="whitespace-pre-wrap break-words text-sm leading-7 text-[#edf1f7] [overflow-wrap:anywhere]">{current.code}</pre>
        </div>
      </div>
    </div>
  );
}
