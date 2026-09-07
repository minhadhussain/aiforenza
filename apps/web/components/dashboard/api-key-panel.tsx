"use client";

import { useMemo, useState } from "react";

type ApiKeyRecord = {
  id: string;
  name: string;
  key_prefix: string;
  masked_key: string;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
  status: "active" | "revoked";
};

type ApiKeyPanelProps = {
  initialKeys: ApiKeyRecord[];
  accessToken: string;
};

type CreateResponse = {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  plaintext_key: string;
};

function formatCreatedLabel(value: string | null) {
  if (!value) {
    return "Sep 8";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export function ApiKeyPanel({ initialKeys, accessToken }: ApiKeyPanelProps) {
  const [keys, setKeys] = useState<ApiKeyRecord[]>(initialKeys);
  const [name, setName] = useState("Production");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);

  const activeCount = useMemo(() => keys.filter((key) => key.status === "active").length, [keys]);

  async function createKey(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api-keys`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      });

      const payload = (await response.json()) as CreateResponse | { detail?: string };

      if (!response.ok) {
        throw new Error("detail" in payload ? payload.detail || "Failed to create API key." : "Failed to create API key.");
      }

      const created = payload as CreateResponse;
      setRevealedKey(created.plaintext_key);
      setKeys((current) => [
        {
          id: created.id,
          name: created.name,
          key_prefix: created.key_prefix,
          masked_key: `${created.key_prefix.slice(0, 8)}••••••••`,
          last_used_at: null,
          created_at: created.created_at,
          revoked_at: null,
          status: "active",
        },
        ...current,
      ]);
      setName("Production");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to create API key.");
    } finally {
      setLoading(false);
    }
  }

  async function revokeKey(keyId: string) {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api-keys/${keyId}/revoke`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
      });

      const payload = (await response.json()) as { data?: ApiKeyRecord; detail?: string };

      if (!response.ok || !payload.data) {
        throw new Error(payload.detail || "Failed to revoke API key.");
      }

      setKeys((current) => current.map((item) => (item.id === keyId ? payload.data! : item)));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to revoke API key.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// API KEYS</p>
      </header>

      <section className="grid gap-px overflow-hidden border border-white/10 bg-white/10 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="min-h-[360px] bg-[#050608] px-6 py-8 lg:px-7">
          <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// User API Keys</p>
          <h2 className="mt-8 text-[1.65rem] font-semibold tracking-[-0.03em] text-white">Generate a User API Key</h2>
          <p className="mt-3 max-w-md text-sm leading-7 text-[var(--muted)]">Create and manage API keys for your applications, SDKs, coding assistants, and OpenAI-compatible tooling.</p>

          {revealedKey ? (
            <div className="mt-8 border border-[#d3b58c] bg-[#fff4e3] px-4 py-4 text-sm text-[#6b4b21]">
              <div className="font-semibold">Copy this key now. It will not be shown again.</div>
              <div className="mt-3 break-all font-mono text-xs sm:text-sm">{revealedKey}</div>
            </div>
          ) : null}

          {error ? <div className="mt-6 border border-[#7f2d12] bg-[#f7d9cb] px-4 py-4 text-sm text-[#7f2d12]">{error}</div> : null}
        </div>

        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-6">
            <div>
              <div className="text-lg font-semibold text-white">User API Keys</div>
              <div className="mt-3 text-sm leading-7 text-[var(--muted)]">
                {keys.length
                  ? `You currently have ${activeCount} active API key${activeCount === 1 ? "" : "s"}.`
                  : "You have not created any API keys yet."}
              </div>
            </div>

            <form className="flex w-full max-w-[320px] flex-col gap-3" onSubmit={createKey}>
              <input
                className="border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white outline-none transition placeholder:text-[var(--muted)] focus:border-white/18"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Key name"
                maxLength={80}
                required
              />
              <button
                className="inline-flex items-center justify-center border border-white/10 bg-white/[0.05] px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
                type="submit"
                disabled={loading}
              >
                {loading ? "Generating..." : "Generate API Key"}
              </button>
            </form>
          </div>

          <div className="mt-6 space-y-3">
            {keys.length ? (
              keys.map((key) => (
                <article key={key.id} className="border border-white/10 bg-white/[0.03] px-4 py-4">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-white">{key.name}</div>
                      <div className="mt-2 font-mono text-sm text-[var(--muted)]">{key.masked_key}</div>
                    </div>

                    <div className="grid gap-4 text-sm text-[var(--muted)] sm:grid-cols-3">
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Status</div>
                        <div className="mt-2 text-white">{key.status === "revoked" ? "Revoked" : "Active"}</div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Created</div>
                        <div className="mt-2 text-white">{formatCreatedLabel(key.created_at)}</div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Last used</div>
                        <div className="mt-2 text-white">{key.last_used_at ? formatCreatedLabel(key.last_used_at) : "Never"}</div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 flex justify-end">
                    <button
                      className="border border-white/10 px-4 py-2 text-sm text-white transition hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      disabled={loading || key.status === "revoked"}
                      onClick={() => revokeKey(key.id)}
                    >
                      {key.status === "revoked" ? "Revoked" : "Revoke"}
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <div className="border border-white/10 bg-white/[0.03] px-4 py-6 text-sm text-[var(--muted)]">
                You have not created any API keys yet. Generate one to connect AI Forenza to OpenCode, Claude Code, Cline, Python, JavaScript, or any OpenAI-compatible client.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
