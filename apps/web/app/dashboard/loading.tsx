export default function DashboardLoading() {
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Loading your dashboard…</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">You’re signed in. Fetching your account details.</p>
      </div>
      <div aria-hidden="true" className="grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="h-32 animate-pulse border border-white/10 bg-white/[0.04] motion-reduce:animate-none" />
        ))}
      </div>
    </div>
  );
}
