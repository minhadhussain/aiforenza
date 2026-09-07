import { redirect } from "next/navigation";

import Link from "next/link";

import { CopyChip } from "@/components/dashboard/copy-chip";
import { fetchDashboardApiKeys, fetchDashboardOverview, fetchDashboardModels, fetchDashboardUsage, formatDateLabel, formatTransactionAmount, formatUsdFromCents } from "@/lib/dashboard";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const [overview, usageRecords, models, apiKeys] = await Promise.all([
    fetchDashboardOverview(session.access_token),
    fetchDashboardUsage(session.access_token),
    fetchDashboardModels(session.access_token),
    fetchDashboardApiKeys(session.access_token),
  ]);

  const recentUsage = usageRecords.slice(0, 4);
  const recentTransactions = overview.transactions.slice(0, 4);
  const modelPreview = models.slice(0, 8);
  const activeKey = apiKeys.find((key) => key.status === "active") ?? null;
  const displayName = overview.profile.email;

  return (
    <div className="space-y-10">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// WELCOME BACK</p>
        <h1 className="mt-3 text-[2rem] font-semibold tracking-[-0.04em] text-white">Your AI Forenza workspace</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">Signed in as {displayName}</p>
      </header>

      <section>
        <p className="mb-4 font-mono text-sm uppercase tracking-[0.16em] text-white/70">// QUICK LINKS</p>
        <div className="grid gap-px overflow-hidden border border-white/10 bg-white/10 lg:grid-cols-3">
          {[
            ["BILLING", "View your balance and add funds.", "/dashboard/billing"],
            ["API KEYS", "Create or revoke API keys.", "/dashboard/api-keys"],
            ["USAGE", "Track requests and API costs.", "/dashboard/usage"],
          ].map(([title, copy, href]) => (
            <Link
              key={title}
              href={href}
              className="group grid min-h-[112px] gap-4 border border-transparent bg-[#050608] px-5 py-5 transition hover:border-white/10 hover:bg-white/[0.05] focus-visible:border-white/16 focus-visible:bg-white/[0.05] focus-visible:outline-none"
            >
              <div className="inline-flex h-5 w-5 items-center justify-center border border-white/12 text-[10px] text-white/70">▢</div>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-white">{title}</div>
                  <div className="mt-3 text-sm leading-6 text-[var(--muted)]">{copy}</div>
                </div>
                <div className="text-xs uppercase tracking-[0.16em] text-white/40 transition group-hover:text-white/70 group-focus-visible:text-white/70">
                  Open →
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <p className="mb-4 font-mono text-sm uppercase tracking-[0.16em] text-white/70">// GET STARTED</p>
        <div className="border border-white/10 bg-[#050608] p-6 lg:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <h2 className="text-2xl font-semibold tracking-[-0.03em] text-white">Make your first API request.</h2>
              <p className="mt-3 text-sm leading-7 text-[var(--muted)]">Create a key, choose a model, and connect your app.</p>
            </div>
            <Link href="/docs" className="inline-flex items-center justify-center border border-white/10 px-4 py-2 text-sm text-white transition hover:bg-white/[0.04]">
              View Docs
            </Link>
          </div>

          <div className="mt-8 max-w-[760px] space-y-5">
            <div>
              <div className="font-mono text-xs uppercase tracking-[0.18em] text-white/70">[01] CREATE API KEY</div>
              <div className="mt-3">
                <Link className="inline-flex items-center justify-center border border-white/10 bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-white/90" href="/dashboard/api-keys">
                  Create API Key
                </Link>
              </div>
            </div>

            <div>
              <div className="font-mono text-xs uppercase tracking-[0.18em] text-white/70">[02] BASE URL</div>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="flex-1 border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white">https://api.YOURDOMAIN.com/v1</div>
                <CopyChip value="https://api.YOURDOMAIN.com/v1" />
              </div>
            </div>

            <div>
              <div className="font-mono text-xs uppercase tracking-[0.18em] text-white/70">[03] MODEL</div>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="flex-1 border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white">gpt-5.6-luna</div>
                <CopyChip value="gpt-5.6-luna" />
              </div>
            </div>

            <div>
              <div className="font-mono text-xs uppercase tracking-[0.18em] text-white/70">[04] REQUEST</div>
              <pre className="mt-3 overflow-x-auto border border-white/10 bg-white/[0.03] px-4 py-4 text-sm leading-7 text-[#edf1f7]">{`from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.YOURDOMAIN.com/v1"\n)`}</pre>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-8 xl:grid-cols-[0.72fr_1.28fr]">
        <section>
          <p className="mb-4 font-mono text-sm uppercase tracking-[0.16em] text-white/70">// BALANCE</p>
          <div className="border border-white/10 bg-[#050608] p-6">
            <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">AVAILABLE BALANCE</div>
            <div className="mt-4 text-5xl font-semibold tracking-[-0.05em] text-white">{formatUsdFromCents(overview.metrics.current_balance_cents)}</div>
            <div className="mt-5">
              <Link className="inline-flex items-center justify-center border border-white/10 bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-white/90" href="/dashboard/billing">
                Add Funds
              </Link>
            </div>

            {overview.metrics.current_balance_cents === 0 ? (
              <p className="mt-5 text-sm text-[var(--muted)]">Your balance is too low to make requests.</p>
            ) : overview.metrics.current_balance_cents <= 1000 ? (
              <p className="mt-5 text-sm text-[var(--muted)]">Balance is running low.</p>
            ) : null}

            <div className="mt-8 grid gap-px border border-white/10 bg-white/10 sm:grid-cols-3">
              <div className="bg-[#050608] px-4 py-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">TODAY</div>
                <div className="mt-3 text-lg text-white">{formatUsdFromCents(overview.metrics.today_usage_cents)}</div>
              </div>
              <div className="bg-[#050608] px-4 py-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">THIS MONTH</div>
                <div className="mt-3 text-lg text-white">{formatUsdFromCents(overview.metrics.month_usage_cents)}</div>
              </div>
              <div className="bg-[#050608] px-4 py-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">REQUESTS</div>
                <div className="mt-3 text-lg text-white">{overview.metrics.api_request_count.toLocaleString()}</div>
              </div>
            </div>
          </div>
        </section>

        <section>
          <p className="mb-4 font-mono text-sm uppercase tracking-[0.16em] text-white/70">// API KEYS</p>
          <div className="border border-white/10 bg-[#050608] p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-base font-semibold text-white">Production</div>
                <div className="mt-3 font-mono text-sm text-white/80">{activeKey?.masked_key ?? "sk_live_••••••••••••"}</div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">Created</div>
                    <div className="mt-2 text-sm text-white">{activeKey?.created_at ? formatDateLabel(activeKey.created_at) : "Sep 8"}</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">Last used</div>
                    <div className="mt-2 text-sm text-white">{activeKey?.last_used_at ? formatDateLabel(activeKey.last_used_at) : "Never"}</div>
                  </div>
                </div>
              </div>
              <div>
                <Link className="inline-flex items-center justify-center border border-white/10 px-4 py-2 text-sm text-white transition hover:bg-white/[0.04]" href="/dashboard/api-keys">
                  Manage API Keys
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-8 xl:grid-cols-[1fr_1fr]">
        <section>
          <div className="mb-4 flex items-center justify-between gap-4">
            <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// RECENT USAGE</p>
            <Link className="text-sm text-white/72 transition hover:text-white" href="/dashboard/usage">
              View usage →
            </Link>
          </div>

          <div className="border border-white/10 bg-[#050608] p-4">
            {recentUsage.length ? (
              <div className="space-y-2">
                <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[0.9fr_1.1fr_0.8fr_0.8fr_0.8fr_0.9fr]">
                  <div>DATE</div>
                  <div>MODEL</div>
                  <div>INPUT</div>
                  <div>OUTPUT</div>
                  <div>COST</div>
                  <div>STATUS</div>
                </div>

                {recentUsage.map((record) => (
                  <div key={record.id} className="grid gap-3 border border-white/10 px-3 py-3 text-sm md:grid-cols-[0.9fr_1.1fr_0.8fr_0.8fr_0.8fr_0.9fr]">
                    <div className="text-[var(--muted)]">{formatDateLabel(record.created_at).toUpperCase()}</div>
                    <div className="text-white">{record.model?.display_name ?? record.model?.slug ?? "Unknown"}</div>
                    <div className="text-[var(--muted)]">{record.input_tokens.toLocaleString()}</div>
                    <div className="text-[var(--muted)]">{record.output_tokens.toLocaleString()}</div>
                    <div className="text-[var(--muted)]">{formatUsdFromCents(record.customer_charge_cents)}</div>
                    <div className="text-[var(--muted)]">{record.status.toUpperCase()}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="border border-white/10 px-4 py-4 text-sm text-[var(--muted)]">No API requests yet.</div>
            )}
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between gap-4">
            <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// TRANSACTIONS</p>
            <Link className="text-sm text-white/72 transition hover:text-white" href="/dashboard/transactions">
              View transactions →
            </Link>
          </div>

          <div className="border border-white/10 bg-[#050608] p-4">
            {recentTransactions.length ? (
              <div className="space-y-2">
                <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[0.9fr_0.9fr_0.9fr_0.9fr]">
                  <div>DATE</div>
                  <div>TYPE</div>
                  <div>AMOUNT</div>
                  <div>BALANCE</div>
                </div>

                {recentTransactions.map((transaction) => (
                  <div key={transaction.id} className="grid gap-3 border border-white/10 px-3 py-3 text-sm md:grid-cols-[0.9fr_0.9fr_0.9fr_0.9fr]">
                    <div className="text-[var(--muted)]">{formatDateLabel(transaction.created_at).toUpperCase()}</div>
                    <div className="text-white">{transaction.type}</div>
                    <div className="text-[var(--muted)]">{formatTransactionAmount(transaction.amount_cents)}</div>
                    <div className="text-[var(--muted)]">{formatUsdFromCents(transaction.balance_after_cents)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="border border-white/10 px-4 py-4 text-sm text-[var(--muted)]">No transactions yet.</div>
            )}
          </div>
        </section>
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between gap-4">
          <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// AVAILABLE MODELS</p>
          <Link className="text-sm text-white/72 transition hover:text-white" href="/dashboard/models">
            View all models →
          </Link>
        </div>

        <div className="border border-white/10 bg-[#050608] p-4">
          <div className="space-y-2">
            <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[1.4fr_0.9fr_0.9fr]">
              <div>MODEL</div>
              <div>INPUT</div>
              <div>OUTPUT</div>
            </div>

            {modelPreview.map((model) => (
              <div key={model.id} className="grid gap-3 border border-white/10 px-3 py-3 text-sm md:grid-cols-[1.4fr_0.9fr_0.9fr]">
                <div className="text-white">{model.display_name}</div>
                <div className="text-[var(--muted)]">{formatUsdFromCents(Math.round(model.customer_input_price_per_million * 100))}</div>
                <div className="text-[var(--muted)]">{formatUsdFromCents(Math.round(model.customer_output_price_per_million * 100))}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
