"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import type { TopupRecord } from "@/lib/topups";
import { formatDateLabel, formatUsdFromCents } from "@/lib/dashboard";

type TopupPanelProps = {
  accessToken: string;
  balanceCents: number;
  initialTopups: TopupRecord[];
};

const packages = [
  { id: "starter_10", amountCents: 1000 },
  { id: "starter_25", amountCents: 2500 },
  { id: "starter_50", amountCents: 5000 },
  { id: "starter_100", amountCents: 10000 },
  { id: "starter_500", amountCents: 50000 },
  { id: "starter_1000", amountCents: 100000 },
];

export function TopupPanel({ accessToken, balanceCents, initialTopups }: TopupPanelProps) {
  const router = useRouter();
  const [paymentNotice, setPaymentNotice] = useState<string | null>(null);
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (query.get("cancelled") === "true") {
      setPaymentNotice("Checkout cancelled. No balance has been added.");
      return;
    }
    if (query.get("success") !== "true") return;
    setPaymentNotice("Payment submitted. Confirming your payment; balance updates only after verification.");
    let count = 0;
    const timer = window.setInterval(() => {
      router.refresh();
      if (++count >= 10) {
        window.clearInterval(timer);
        setPaymentNotice("Check your top-up status below. If payment is still pending, refresh again shortly.");
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [router]);
  const [selectedPackage, setSelectedPackage] = useState<string>("starter_10");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const completedCount = useMemo(() => initialTopups.filter((item) => item.status === "COMPLETED").length, [initialTopups]);

  async function startCheckout() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/billing/create-checkout-session`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ package_id: selectedPackage }),
      });

      const payload = (await response.json()) as {
        checkout_url?: string;
        detail?: string;
        error?: {
          message?: string;
          code?: string;
        };
      };
      if (!response.ok || !payload.checkout_url) {
        throw new Error(payload.error?.message || payload.detail || "Failed to create Stripe Checkout session.");
      }

      window.location.href = payload.checkout_url;
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to create Stripe Checkout session.");
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// BILLING</p>
        {paymentNotice && <p role="status" className="mt-3 text-sm text-[var(--muted)]">{paymentNotice}</p>}
      </header>

      <section className="grid gap-px overflow-hidden border border-white/10 bg-white/10 xl:grid-cols-[0.82fr_1.18fr]">
        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// Balance</p>
          <div className="mt-8 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">AVAILABLE BALANCE</div>
          <div className="mt-4 text-5xl font-semibold tracking-[-0.05em] text-white">{formatUsdFromCents(balanceCents)}</div>
          <p className="mt-5 text-sm leading-7 text-[var(--muted)]">Use prepaid wallet credits for API usage. Wallet crediting occurs only after verified Stripe webhook completion.</p>
          <div className="mt-8 text-sm text-[var(--muted)]">Completed top-ups: {completedCount}</div>
        </div>

        <div className="bg-[#050608] px-6 py-8 lg:px-7">
          <div className="flex flex-col gap-4 border-b border-white/10 pb-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="text-lg font-semibold text-white">Prepaid top-ups</div>
              <div className="mt-3 text-sm leading-7 text-[var(--muted)]">Choose a fixed MVP amount and continue to Stripe Checkout. A successful redirect does not credit your wallet until the verified webhook is processed.</div>
            </div>
            <button
              type="button"
              onClick={startCheckout}
              disabled={loading}
              className="inline-flex items-center justify-center border border-white/10 bg-white/[0.05] px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
            >
          {loading ? "Redirecting..." : `Add ${formatUsdFromCents(packages.find((pkg) => pkg.id === selectedPackage)?.amountCents ?? 1000)}`}
        </button>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {packages.map((pkg) => (
              <button
                key={pkg.id}
                type="button"
                onClick={() => setSelectedPackage(pkg.id)}
                className={`border px-4 py-5 text-left transition ${
                  selectedPackage === pkg.id
                    ? "border-white/18 bg-white/[0.07]"
                    : "border-white/10 bg-white/[0.03] hover:bg-white/[0.05]"
                }`}
              >
                <div className="text-2xl font-semibold tracking-[-0.04em] text-white">{formatUsdFromCents(pkg.amountCents)}</div>
                <div className="mt-2 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">Stripe Checkout</div>
              </button>
            ))}
          </div>

          {error ? <div className="mt-6 border border-[#7f2d12] bg-[#f7d9cb] px-4 py-4 text-sm text-[#7f2d12]">{error}</div> : null}
        </div>
      </section>

      <section className="border border-white/10 bg-[#050608] px-6 py-5 text-sm text-[var(--muted)]">
        Local Stripe development uses Stripe CLI webhook forwarding. Wallet crediting only happens after a verified webhook event reaches the backend.
      </section>

      <section>
        <p className="mb-4 font-mono text-sm uppercase tracking-[0.16em] text-white/70">// RECENT TOP-UPS</p>
        <div className="border border-white/10 bg-[#050608] p-4">
          {initialTopups.length ? (
            <div className="space-y-2">
              <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[0.9fr_0.8fr_0.9fr_0.9fr]">
                <div>DATE</div>
                <div>STATUS</div>
                <div>AMOUNT</div>
                <div>CURRENCY</div>
              </div>

              {initialTopups.map((topup) => (
                <div key={topup.id} className="grid gap-3 border border-white/10 px-3 py-3 text-sm md:grid-cols-[0.9fr_0.8fr_0.9fr_0.9fr]">
                  <div className="text-[var(--muted)]">{formatDateLabel(topup.created_at).toUpperCase()}</div>
                  <div className="text-white">{topup.status}</div>
                  <div className="text-[var(--muted)]">{formatUsdFromCents(topup.amount_cents)}</div>
                  <div className="text-[var(--muted)]">{topup.currency}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border border-white/10 px-4 py-4 text-sm text-[var(--muted)]">No top-ups yet. Your first Stripe Checkout payment will appear here after the webhook credits your wallet.</div>
          )}
        </div>
      </section>
    </div>
  );
}
