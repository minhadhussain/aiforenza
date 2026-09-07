"use client";

import { useMemo, useState } from "react";

import type { TopupRecord } from "@/lib/topups";
import { formatDateLabel, formatUsdFromCents } from "@/lib/dashboard";

type TopupPanelProps = {
  accessToken: string;
  balanceCents: number;
  initialTopups: TopupRecord[];
};

const amounts = [1000, 2500, 5000, 10000, 50000, 100000];

export function TopupPanel({ accessToken, balanceCents, initialTopups }: TopupPanelProps) {
  const [selectedAmount, setSelectedAmount] = useState<number>(1000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const completedCount = useMemo(() => initialTopups.filter((item) => item.status === "COMPLETED").length, [initialTopups]);

  async function startCheckout() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/topups/checkout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ amount_cents: selectedAmount }),
      });

      const payload = (await response.json()) as { checkout_url?: string; detail?: string };
      if (!response.ok || !payload.checkout_url) {
        throw new Error(payload.detail || "Failed to create Stripe Checkout session.");
      }

      window.location.href = payload.checkout_url;
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to create Stripe Checkout session.");
      setLoading(false);
    }
  }

  return (
    <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Add funds</p>
          <h2 className="mt-2 font-[family-name:var(--font-heading)] text-3xl">Prepaid wallet top-ups</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Use Stripe Checkout to add balance in fixed MVP amounts. Wallet crediting happens only after verified webhook processing.</p>
        </div>
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-sm">
          <div className="text-[var(--muted)]">Current balance</div>
          <div className="mt-1 font-[family-name:var(--font-heading)] text-2xl">{formatUsdFromCents(balanceCents)}</div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {amounts.map((amount) => (
          <button
            key={amount}
            type="button"
            onClick={() => setSelectedAmount(amount)}
            className={`rounded-3xl border px-4 py-4 text-left transition ${
              selectedAmount === amount
                ? "border-[var(--accent)] bg-[var(--surface-strong)]"
                : "border-[var(--border)] bg-[var(--surface-strong)]"
            }`}
          >
            <div className="font-[family-name:var(--font-heading)] text-2xl">{formatUsdFromCents(amount)}</div>
            <div className="mt-2 text-sm text-[var(--muted)]">Stripe Checkout</div>
          </button>
        ))}
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-[var(--muted)]">Completed top-ups: {completedCount}</div>
        <button
          type="button"
          onClick={startCheckout}
          disabled={loading}
          className="inline-flex items-center justify-center rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Redirecting..." : `Add ${formatUsdFromCents(selectedAmount)}`}
        </button>
      </div>

      {error ? <div className="mt-4 rounded-3xl bg-[#f7d9cb] p-4 text-sm text-[#7f2d12]">{error}</div> : null}

      <div className="mt-6 space-y-3">
        {initialTopups.length ? (
          initialTopups.map((topup) => (
            <article key={topup.id} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm uppercase tracking-[0.15em] text-[var(--muted)]">{topup.status}</p>
                  <h3 className="mt-2 font-[family-name:var(--font-heading)] text-lg">{formatUsdFromCents(topup.amount_cents)}</h3>
                  <p className="mt-2 text-sm text-[var(--muted)]">Created {formatDateLabel(topup.created_at)}</p>
                </div>
                <div className="text-right text-sm text-[var(--muted)]">
                  <div>{topup.currency}</div>
                  <div className="mt-2">{topup.completed_at ? `Completed ${formatDateLabel(topup.completed_at)}` : "Pending webhook"}</div>
                </div>
              </div>
            </article>
          ))
        ) : (
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4 text-sm leading-6 text-[var(--muted)]">
            No top-ups yet. Your first Stripe Checkout payment will appear here after the webhook credits your wallet.
          </div>
        )}
      </div>
    </section>
  );
}
