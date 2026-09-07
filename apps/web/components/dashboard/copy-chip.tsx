"use client";

import { useState } from "react";

type CopyChipProps = {
  value: string;
  className?: string;
};

export function CopyChip({ value, className = "" }: CopyChipProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-[var(--muted)] transition hover:border-white/20 hover:text-white ${className}`}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
