import { redirect } from "next/navigation";

import Link from "next/link";

import { CopyChip } from "@/components/dashboard/copy-chip";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function DashboardSettingsPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// SETTINGS</p>
        <p className="mt-3 text-sm leading-7 text-[var(--muted)]">
          Account, security, and developer defaults for your AI Forenza workspace.
        </p>
      </header>

      <section className="grid gap-px overflow-hidden border border-white/10 bg-white/10 xl:grid-cols-[0.88fr_1.12fr]">
        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// ACCOUNT</p>
          <h2 className="mt-8 text-[1.65rem] font-semibold tracking-[-0.03em] text-white">Developer account</h2>
          <p className="mt-3 max-w-md text-sm leading-7 text-[var(--muted)]">
            The dashboard uses your authenticated account to access wallet balance, API keys, usage, transactions, and top-ups.
          </p>

          <div className="mt-8 space-y-4 border-t border-white/10 pt-6 text-sm">
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Email</div>
              <div className="mt-2 text-white">{user.email ?? "unknown-user"}</div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">User ID</div>
              <div className="mt-2 break-all font-mono text-xs text-[var(--muted)]">{user.id}</div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Authentication</div>
              <div className="mt-2 text-white">Supabase session</div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Workspace type</div>
              <div className="mt-2 text-white">Developer dashboard</div>
            </div>
          </div>
        </div>

        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <div className="border-b border-white/10 pb-6">
            <div className="text-lg font-semibold text-white">Workspace defaults</div>
            <div className="mt-3 text-sm leading-7 text-[var(--muted)]">
              Keep your API base URL, documentation, billing, and key management close to where you use them.
            </div>
          </div>

          <div className="mt-6 space-y-5">
            <div className="border border-white/10 bg-white/[0.03] px-4 py-4">
              <div className="flex items-center justify-between gap-4">
                <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">API base URL</div>
                <CopyChip value="https://api.YOURDOMAIN.com/v1" />
              </div>
              <div className="mt-3 break-all text-sm text-white">https://api.YOURDOMAIN.com/v1</div>
            </div>

            <div className="border border-white/10 bg-white/[0.03] px-4 py-4">
              <div className="flex items-center justify-between gap-4">
                <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Recommended model</div>
                <CopyChip value="gpt-5.6-luna" />
              </div>
              <div className="mt-3 text-sm text-white">gpt-5.6-luna</div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/api-keys">
                <div className="font-semibold">Manage API keys</div>
                <div className="mt-2 text-[var(--muted)]">Create, name, and revoke access keys.</div>
              </Link>
              <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/billing">
                <div className="font-semibold">Billing & top-ups</div>
                <div className="mt-2 text-[var(--muted)]">Add prepaid funds and review recent credits.</div>
              </Link>
              <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/usage">
                <div className="font-semibold">Usage history</div>
                <div className="mt-2 text-[var(--muted)]">Inspect recorded request activity and costs.</div>
              </Link>
              <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/docs">
                <div className="font-semibold">Read the docs</div>
                <div className="mt-2 text-[var(--muted)]">Open the authenticated documentation workspace under the dashboard.</div>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-px overflow-hidden border border-white/10 bg-white/10 xl:grid-cols-[1fr_1fr]">
        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// SECURITY</p>
          <div className="mt-6 space-y-5 text-sm leading-7 text-[var(--muted)]">
            <div>
              <div className="font-semibold text-white">API key handling</div>
              <p className="mt-2">API keys are shown in full only once when created. Store them in your own environment variables or secret manager.</p>
            </div>
            <div>
              <div className="font-semibold text-white">Wallet-backed access</div>
              <p className="mt-2">Requests are billed against your prepaid wallet balance. If the balance is too low, the API rejects the request before provider forwarding.</p>
            </div>
            <div>
              <div className="font-semibold text-white">Backend-only secrets</div>
              <p className="mt-2">Provider credentials, Stripe secrets, and Supabase service-role credentials remain on the backend and are never exposed through dashboard settings.</p>
            </div>
          </div>
        </div>

        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// WORKSPACE LINKS</p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard">
              <div className="font-semibold">Overview</div>
              <div className="mt-2 text-[var(--muted)]">Return to your balance, quick links, and first-request workflow.</div>
            </Link>
            <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/models">
              <div className="font-semibold">Available models</div>
              <div className="mt-2 text-[var(--muted)]">Inspect current model IDs and customer-facing pricing.</div>
            </Link>
            <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/transactions">
              <div className="font-semibold">Transactions</div>
              <div className="mt-2 text-[var(--muted)]">Review immutable ledger activity across trial, top-ups, and usage.</div>
            </Link>
            <Link className="border border-white/10 px-4 py-4 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/usage">
              <div className="font-semibold">Usage records</div>
              <div className="mt-2 text-[var(--muted)]">Inspect request history, token counts, and recorded API costs.</div>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
