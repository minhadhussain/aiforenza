"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { ReactNode } from "react";

type DashboardShellProps = {
  email: string;
  children: ReactNode;
};

const navItems = [
  ["Overview", "/dashboard"],
  ["API Keys", "/dashboard/api-keys"],
  ["Usage", "/dashboard/usage"],
  ["Billing", "/dashboard/billing"],
  ["Docs", "/docs"],
] as const;

function NavList({ pathname, closeMenu }: { pathname: string; closeMenu?: () => void }) {
  return (
    <nav className="space-y-1.5">
      {navItems.map(([label, href]) => {
        const active = href === "/dashboard" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);

        return (
          <Link
            key={href}
            href={href}
            onClick={closeMenu}
            className={`flex items-center gap-3 border border-transparent px-3 py-2.5 text-sm transition ${
              active
                ? "border-white/12 bg-white/[0.06] text-white"
                : "text-[var(--muted)] hover:border-white/8 hover:bg-white/[0.03] hover:text-white"
            }`}
          >
            <span className="inline-flex h-4 w-4 items-center justify-center border border-white/12 text-[10px] text-white/70">
              ▢
            </span>
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function DashboardShell({ email, children }: DashboardShellProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <main className="min-h-screen bg-[#030405] text-white">
      <div className="mx-auto grid min-h-screen w-full max-w-[1600px] lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="hidden border-r border-white/10 lg:block">
          <div className="sticky top-0 flex h-screen flex-col px-4 py-7">
            <div className="border-b border-white/10 pb-7">
              <div className="font-[family-name:var(--font-heading)] text-[1.05rem] font-semibold tracking-[-0.04em] text-white">AI Forenza</div>
            </div>

            <div className="pt-7">
              <NavList pathname={pathname} />
            </div>

            <div className="mt-auto border-t border-white/10 pt-5">
              <Link
                href="/dashboard"
                className="flex items-center gap-3 border border-transparent px-3 py-2.5 text-sm text-[var(--muted)] transition hover:border-white/8 hover:bg-white/[0.03] hover:text-white"
              >
                <span className="inline-flex h-4 w-4 items-center justify-center border border-white/12 text-[10px] text-white/70">▢</span>
                <span>Settings</span>
              </Link>

              <div className="mt-5 border-t border-white/10 pt-4">
                <div className="px-3 pb-4 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">Signed in</div>
                <div className="px-3 text-sm text-white">{email}</div>
                <form action="/logout" method="post" className="mt-4 px-3">
                  <button className="w-full border border-white/10 px-4 py-2.5 text-left text-sm text-[var(--muted)] transition hover:border-white/18 hover:text-white">
                    Log out
                  </button>
                </form>
              </div>
            </div>
          </div>
        </aside>

        <div className="min-w-0">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-4 lg:hidden">
            <div>
              <div className="font-[family-name:var(--font-heading)] text-[1.05rem] font-semibold tracking-[-0.04em] text-white">AI Forenza</div>
              <div className="mt-1 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">Developer dashboard</div>
            </div>
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="border border-white/10 px-3 py-2 text-sm text-white"
            >
              Menu
            </button>
          </div>

          {menuOpen ? (
            <div className="fixed inset-0 z-40 bg-black/90 px-4 py-4 lg:hidden">
              <div className="flex h-full flex-col border border-white/10 bg-[#050608] p-4">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="font-[family-name:var(--font-heading)] text-[1.05rem] font-semibold tracking-[-0.04em] text-white">AI Forenza</div>
                  <button type="button" onClick={() => setMenuOpen(false)} className="text-2xl text-white/80">
                    ×
                  </button>
                </div>

                <div className="pt-5">
                  <NavList pathname={pathname} closeMenu={() => setMenuOpen(false)} />
                </div>

                <div className="mt-auto border-t border-white/10 pt-4">
                  <Link
                    href="/dashboard"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-3 border border-transparent px-3 py-2.5 text-sm text-[var(--muted)] transition hover:border-white/8 hover:bg-white/[0.03] hover:text-white"
                  >
                    <span className="inline-flex h-4 w-4 items-center justify-center border border-white/12 text-[10px] text-white/70">▢</span>
                    <span>Settings</span>
                  </Link>

                  <div className="mt-5 border-t border-white/10 pt-4">
                    <div className="px-3 pb-4 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">Signed in</div>
                    <div className="px-3 text-sm text-white">{email}</div>
                    <form action="/logout" method="post" className="mt-4 px-3">
                      <button className="w-full border border-white/10 px-4 py-2.5 text-left text-sm text-[var(--muted)] transition hover:border-white/18 hover:text-white">
                        Log out
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          <div className="px-4 py-5 lg:px-8 lg:py-7">{children}</div>
        </div>
      </div>
    </main>
  );
}
