import type { ReactNode } from "react";

type AuthShellProps = {
  eyebrow: string;
  title: string;
  copy: string;
  footer: ReactNode;
  children: ReactNode;
};

export function AuthShell({ eyebrow, title, copy, footer, children }: AuthShellProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center px-6 py-10 sm:px-10">
      <div className="grid w-full gap-8 lg:grid-cols-[1fr_0.92fr]">
        <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-[var(--shadow)] backdrop-blur sm:p-10">
          <p className="text-sm uppercase tracking-[0.25em] text-[var(--muted)]">{eyebrow}</p>
          <h1 className="mt-4 font-[family-name:var(--font-heading)] text-4xl leading-tight sm:text-5xl">{title}</h1>
          <p className="mt-4 max-w-xl text-base leading-8 text-[var(--muted)]">{copy}</p>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {[
              ["$5 credit", "Granted after account creation in the wallet phase"],
              ["OpenAI-compatible", "Use one base URL and model name across tools"],
              ["Prepaid billing", "Top up only when the trial is not enough"],
            ].map(([label, detail]) => (
              <div key={label} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4">
                <div className="font-[family-name:var(--font-heading)] text-lg">{label}</div>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur sm:p-8">
          {children}
          <div className="mt-6 border-t border-[var(--border)] pt-5 text-sm text-[var(--muted)]">{footer}</div>
        </section>
      </div>
    </main>
  );
}
