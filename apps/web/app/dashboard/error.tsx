"use client";

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <div role="alert" className="space-y-4 border border-white/10 bg-[#050608] p-6">
      <h1 className="text-2xl font-semibold text-white">Your dashboard couldn’t load</h1>
      <p className="text-sm text-[var(--muted)]">You’re signed in, but account data is temporarily unavailable. Please try again.</p>
      <button
        type="button"
        onClick={reset}
        className="border border-white/10 bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-white/90"
      >
        Try again
      </button>
    </div>
  );
}
