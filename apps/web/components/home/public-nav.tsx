"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  ["Models", "/models"],
  ["Pricing", "/pricing"],
  ["Docs", "/docs"],
  ["About", "/#about"],
] as const;

export function PublicNav() {
  const pathname = usePathname();

  return (
    <nav className="hidden items-center gap-7 text-sm text-[var(--muted)] lg:flex">
      {navItems.map(([label, href]) => {
        const isAbout = href === "/#about";
        const active = isAbout ? pathname === "/" : pathname === href;

        return (
          <Link
            key={label}
            className={`transition ${active ? "text-white" : "hover:text-white"}`}
            href={href}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
