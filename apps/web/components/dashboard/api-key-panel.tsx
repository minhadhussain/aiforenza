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

export function ApiKeyPanel({ initialKeys, accessToken }: ApiKeyPanelProps) {
  const [keys, setKeys] = useState<ApiKeyRecord[]>(initialKeys);
  const [name, setName] = useState("Claude Code");
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
      setName("Claude Code");
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
    <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">API keys</p>
          <h2 className="mt-2 font-[family-name:var(--font-heading)] text-3xl">Create and revoke credentials</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Only the plaintext key is shown once. Stored records keep only a prefix and secure hash.</p>
        </div>
        <div className="rounded-full border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-2 text-sm font-semibold">
          {activeCount} active
        </div>
      </div>

      <form className="mt-6 flex flex-col gap-3 sm:flex-row" onSubmit={createKey}>
        <input
          className="flex-1 rounded-full border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-base outline-none focus:border-[var(--accent)]"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Key name"
          maxLength={80}
          required
        />
        <button
          className="inline-flex items-center justify-center rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
          type="submit"
          disabled={loading}
        >
          {loading ? "Working..." : "Create API key"}
        </button>
      </form>

      {revealedKey ? (
        <div className="mt-4 rounded-3xl border border-[#d3b58c] bg-[#fff4e3] p-4 text-sm text-[#6b4b21]">
          <div className="font-semibold">Copy this key now. It will not be shown again.</div>
          <div className="mt-2 break-all font-mono text-xs sm:text-sm">{revealedKey}</div>
        </div>
      ) : null}

      {error ? <div className="mt-4 rounded-3xl bg-[#f7d9cb] p-4 text-sm text-[#7f2d12]">{error}</div> : null}

      <div className="mt-6 space-y-3">
        {keys.length ? (
          keys.map((key) => (
            <article key={key.id} className="flex flex-col gap-4 rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-[family-name:var(--font-heading)] text-lg">{key.name}</p>
                <p className="mt-1 font-mono text-sm text-[var(--muted)]">{key.masked_key}</p>
                <p className="mt-2 text-sm text-[var(--muted)]">Status: {key.status}</p>
              </div>
              <button
                className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-white px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                disabled={loading || key.status === "revoked"}
                onClick={() => revokeKey(key.id)}
              >
                {key.status === "revoked" ? "Revoked" : "Revoke"}
              </button>
            </article>
          ))
        ) : (
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4 text-sm leading-6 text-[var(--muted)]">
            No API keys yet. Create your first key for Claude Code, OpenCode, or another OpenAI-compatible client.
          </div>
        )}
      </div>
    </section>
  );
}
