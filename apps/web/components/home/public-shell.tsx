import Link from "next/link";
import type { ReactNode } from "react";

import { MobileNav } from "@/components/home/mobile-nav";
import { PublicNav } from "@/components/home/public-nav";

type PublicShellProps = {
  children: ReactNode;
};

export function PublicShell({ children }: PublicShellProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1200px] flex-col px-4 pb-20 pt-5 sm:px-6 lg:px-8">
      <header className="sticky top-0 z-20 mb-14">
        <div className="smooth-border rounded-full bg-black/35 px-4 py-3 shadow-[var(--shadow)] backdrop-blur-md sm:px-5" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="font-[family-name:var(--font-heading)] text-base font-semibold tracking-[-0.035em] text-white sm:text-[1.06rem]">
              AI Forenza
            </Link>

            <PublicNav />

            <div className="hidden items-center gap-3 sm:flex">
              <Link className="px-3 py-2 text-sm text-[var(--muted)] transition hover:text-white" href="/login">
                Log in
              </Link>
              <Link className="inline-flex items-center justify-center rounded-full bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-white/90" href="/signup">
                Start Free
              </Link>
            </div>

            <MobileNav />
          </div>
        </div>
      </header>

      {children}
    </main>
  );
}
