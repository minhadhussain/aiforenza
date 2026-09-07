"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { docsPages } from "@/lib/docs";

export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:block">
      <div className="sticky top-24 border border-white/8 bg-white/[0.025] p-4 shadow-[var(--shadow)]">
        <div className="mb-4 border-b border-white/8 pb-4">
          <div className="text-sm uppercase tracking-[0.18em] text-[var(--muted)]">Documentation</div>
        </div>

        <nav className="space-y-1.5">
          <Link
            href="/docs"
            className={`block px-3 py-2 text-sm transition ${pathname === "/docs" ? "bg-white text-black" : "text-[var(--muted)] hover:bg-white/[0.04] hover:text-white"}`}
          >
            Overview
          </Link>

          {docsPages.map((page) => {
            const href = `/docs/${page.slug}`;
            const active = pathname === href;

            return (
              <Link
                key={page.slug}
                href={href}
                className={`block px-3 py-2 text-sm transition ${active ? "bg-white text-black" : "text-[var(--muted)] hover:bg-white/[0.04] hover:text-white"}`}
              >
                {page.title}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
