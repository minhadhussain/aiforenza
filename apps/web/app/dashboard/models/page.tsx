import { redirect } from "next/navigation";

import { CopyChip } from "@/components/dashboard/copy-chip";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchDashboardModels, formatModelRate } from "@/lib/dashboard";

function perMillionToCents(value: number | null) {
  return value ?? 0;
}

export default async function DashboardModelsPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const models = await fetchDashboardModels(session.access_token);

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// AVAILABLE MODELS</p>
        <p className="mt-3 text-sm leading-7 text-[var(--muted)]">Available customer-facing models and their current configured pricing.</p>
      </header>

      <section className="border border-white/10 bg-[#050608] p-4">
        {models.length ? (
          <div className="space-y-2">
            <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[1.4fr_0.9fr_0.9fr_0.9fr]">
              <div>MODEL</div>
              <div>INPUT</div>
              <div>OUTPUT</div>
              <div>CACHED</div>
            </div>

            {models.map((model) => (
              <div key={model.id} className="grid gap-3 border border-white/10 px-3 py-3 text-sm md:grid-cols-[1.4fr_0.9fr_0.9fr_0.9fr]">
                <div>
                  <div className="text-white">{model.display_name}</div>
                  <div className="mt-2 flex items-center gap-3">
                    <div className="font-mono text-xs text-[var(--muted)]">{model.slug}</div>
                    <CopyChip value={model.slug} />
                  </div>
                </div>
                <div className="text-[var(--muted)]">{formatModelRate(model.customer_input_price_per_million)}</div>
                <div className="text-[var(--muted)]">{formatModelRate(model.customer_output_price_per_million)}</div>
                <div className="text-[var(--muted)]">{formatModelRate(model.customer_cached_input_price_per_million)}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-white/10 px-4 py-4 text-sm text-[var(--muted)]">No enabled models are available yet.</div>
        )}
      </section>
    </div>
  );
}
