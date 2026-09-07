import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchDashboardUsage, formatDateLabel, formatUsdFromCents } from "@/lib/dashboard";

export default async function DashboardUsagePage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const records = await fetchDashboardUsage(session.access_token);

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// RECENT USAGE</p>
        <p className="mt-3 text-sm leading-7 text-[var(--muted)]">Track request-level usage, token counts, and API cost history.</p>
      </header>

      <section className="border border-white/10 bg-[#050608] p-4">
        {records.length ? (
          <div className="space-y-2">
            <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[0.9fr_1.1fr_0.8fr_0.8fr_0.8fr_0.9fr]">
              <div>DATE</div>
              <div>MODEL</div>
              <div>INPUT</div>
              <div>OUTPUT</div>
              <div>COST</div>
              <div>STATUS</div>
            </div>

            {records.map((record) => (
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
      </section>
    </div>
  );
}
