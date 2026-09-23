"use client";

import { useCallback, useEffect, useState } from "react";

type ModelConfig = {
  name: string;
  reasoning?: boolean;
  options?: { reasoningEffort?: string };
  variants?: Record<string, { reasoningEffort?: string; disabled?: boolean }>;
  limit: { context: number; input: number; output: number };
};
type OpenCodeConfig = {
  provider: { aiforenza: {
    npm: string;
    options: { baseURL: string };
    models: Record<string, ModelConfig>;
  } };
};

const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1").replace(/\/$/, "");
const configUrl = `${apiBase}/public/opencode-config`;

export function OpenCodeSetup() {
  const [config, setConfig] = useState<OpenCodeConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    let mounted = true;
    setConfig(null);
    setError(null);
    setCopied(false);
    async function load() {
      try {
        const response = await fetch(configUrl, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Configuration unavailable");
        const body = await response.json() as OpenCodeConfig;
        const provider = body.provider?.aiforenza;
        if (provider?.npm !== "@ai-sdk/openai-compatible" || !provider.options?.baseURL || "apiKey" in provider.options || !Object.keys(provider.models ?? {}).length) {
          throw new Error("Invalid configuration");
        }
        if (mounted) setConfig(body);
      } catch {
        if (mounted) setError("Unable to load the current OpenCode configuration. Check that the AI Forenza API and model catalog are available, then retry.");
      } finally {
        window.clearTimeout(timeout);
      }
    }
    void load();
    return () => { mounted = false; controller.abort(); window.clearTimeout(timeout); };
  }, [attempt]);

  const copy = useCallback(async () => {
    if (!config) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(config, null, 2));
      setCopied(true);
    } catch {
      setError("Clipboard unavailable. Download the configuration or copy the displayed JSON manually.");
    }
  }, [config]);

  const provider = config?.provider.aiforenza;
  const local = provider && /^(?:https?:\/\/)(?:localhost|127\.\d+\.\d+\.\d+|\[::1\])(?::\d+)?\//.test(provider.options.baseURL);
  return (
    <div className="mt-5 space-y-5" data-testid="opencode-setup">
      {error && <p role="alert" className="border border-amber-300/25 p-3 text-sm text-amber-100">{error}</p>}
      {!config && !error && <p role="status" className="text-sm text-[var(--muted)]">Loading the current model configuration…</p>}
      {provider && <>
        <div className="text-sm leading-7 text-[var(--muted)]">
          <p>Provider ID: <code className="text-white">aiforenza</code></p>
          <p>API base URL: <code data-testid="opencode-base-url" className="break-all text-white">{provider.options.baseURL}</code></p>
          <p>This configuration contains no API key. OpenCode uses the credential saved through <code>/connect</code>.</p>
          {local && <p className="mt-2 border border-amber-300/25 p-3 text-amber-100">Local development endpoint: this address works only on the machine running AI Forenza. For users on other computers, the service administrator must configure a reachable public HTTPS API URL.</p>}
        </div>
        <div className="flex flex-wrap gap-3">
          <a href={configUrl} download="opencode.json" className="border border-white/20 bg-white px-4 py-2 text-sm font-semibold text-black">Download opencode.json</a>
          <button type="button" onClick={() => void copy()} className="border border-white/20 px-4 py-2 text-sm">{copied ? "Copied" : "Copy configuration"}</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="pb-3 text-left text-[var(--muted)]">Current models and effort options from the backend registry</caption>
            <thead className="border-b border-white/10"><tr><th className="py-2 pr-4">Model</th><th className="py-2 pr-4">Efforts</th><th className="py-2">Default</th></tr></thead>
            <tbody>{Object.entries(provider.models).map(([slug, model]) => <tr key={slug} className="border-b border-white/10" data-model={slug}>
              <td className="py-3 pr-4">{model.name}<code className="block text-xs text-[var(--muted)]">{slug}</code></td>
              <td className="py-3 pr-4">{Object.entries(model.variants ?? {}).filter(([, variant]) => !variant.disabled).map(([name]) => name).join(" · ") || "Standard model settings"}</td>
              <td className="py-3">{model.options?.reasoningEffort ?? "Provider default"}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <details className="border border-white/10 p-4">
          <summary className="cursor-pointer text-sm">View configuration JSON</summary>
          <pre data-testid="opencode-config-json" className="mt-4 overflow-x-auto text-xs leading-6">{JSON.stringify(config, null, 2)}</pre>
        </details>
      </>}
      <button type="button" onClick={() => setAttempt((value) => value + 1)} className="border border-white/15 px-3 py-2 text-sm">Refresh configuration</button>
    </div>
  );
}
