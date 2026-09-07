"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navItems = [
  ["Models", "/models"],
  ["Pricing", "/pricing"],
  ["Docs", "/docs"],
  ["About", "/#about"],
] as const;

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const [renderMenu, setRenderMenu] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    if (open) {
      setRenderMenu(true);
      return;
    }

    if (!renderMenu) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setRenderMenu(false);
    }, 220);

    return () => window.clearTimeout(timeout);
  }, [open, renderMenu]);

  function handleOpen() {
    setRenderMenu(true);
    setOpen(true);
  }

  function handleClose() {
    setOpen(false);
  }

  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        aria-label="Open navigation menu"
        onClick={handleOpen}
        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-white transition hover:border-white/20 hover:bg-white/[0.06] sm:hidden"
      >
        <span className="flex flex-col gap-1">
          <span className="block h-px w-4 bg-current" />
          <span className="block h-px w-4 bg-current" />
          <span className="block h-px w-4 bg-current" />
        </span>
      </button>

      {renderMenu ? (
        <div className={`fixed inset-0 z-50 bg-[#050607]/98 px-5 py-5 sm:hidden ${open ? "animate-[fadeIn_180ms_ease-out_forwards]" : "animate-[fadeOut_180ms_ease-in_forwards]"}`}>
          <div className={`mx-auto flex h-full w-full max-w-lg flex-col rounded-[2rem] border border-white/8 bg-[#090b0d] p-5 shadow-[0_30px_120px_rgba(0,0,0,0.6)] ${open ? "animate-[panelIn_220ms_cubic-bezier(0.22,1,0.36,1)_forwards]" : "animate-[panelOut_180ms_cubic-bezier(0.55,0.06,0.68,0.19)_forwards]"}`}>
            <div className="flex items-center justify-between gap-4 border-b border-white/8 pb-4">
              <Link href="/" onClick={handleClose} className="font-[family-name:var(--font-heading)] text-base tracking-[0.14em] text-white">
                <span className="text-[0.95rem] font-semibold tracking-[-0.03em] text-white">AI Forenza</span>
              </Link>
              <button
                type="button"
                aria-label="Close navigation menu"
                onClick={handleClose}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-white transition hover:border-white/20 hover:bg-white/[0.06]"
              >
                <span className="text-lg">×</span>
              </button>
            </div>

            <nav className="mt-8 flex flex-1 flex-col gap-3">
              {navItems.map(([label, href]) => (
                ((label, href, active) => (
                <Link
                  key={label}
                  href={href}
                  onClick={handleClose}
                  className={`rounded-2xl border px-4 py-4 text-base transition ${active ? "border-white/18 bg-white text-black" : "border-white/8 bg-white/[0.02] text-white hover:border-white/18 hover:bg-white/[0.05]"}`}
                >
                  {label}
                </Link>
                ))(label, href, href === "/#about" ? pathname === "/" : pathname === href)
              ))}
            </nav>

            <div className="mt-6 grid gap-3 border-t border-white/8 pt-5">
              <Link
                href="/login"
                onClick={handleClose}
                className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.03] px-5 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/[0.06]"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                onClick={handleClose}
                className="inline-flex items-center justify-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-white/90"
              >
                Start Free
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
