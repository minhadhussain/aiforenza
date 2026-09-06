import type { ReactNode } from "react";

type DashboardShellProps = {
  email: string;
  children: ReactNode;
};

export function DashboardShell({ email, children }: DashboardShellProps) {
  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-6 py-8 sm:px-10 lg:px-12">
      <header className="mb-8 flex flex-col gap-4 rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Protected dashboard</p>
          <h1 className="mt-2 font-[family-name:var(--font-heading)] text-3xl">Welcome back</h1>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Signed in as {email}. Wallets, usage, transactions, and API keys will attach to this surface in later phases.</p>
        </div>

        <form action="/logout" method="post">
          <button className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-strong)] px-5 py-3 text-sm font-semibold text-[var(--text)] transition hover:border-[var(--accent)]">
            Sign out
          </button>
        </form>
      </header>

      {children}
    </main>
  );
}
