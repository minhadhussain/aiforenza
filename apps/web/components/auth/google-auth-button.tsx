import { safeDashboardPath } from "@/lib/auth";

export function GoogleAuthButton({ intent, nextPath }: { intent: "login" | "signup"; nextPath?: string }) {
  const query = new URLSearchParams({ intent, next: safeDashboardPath(nextPath) });
  return (
    <div className="mb-6 space-y-5">
      <a
        href={`/auth/google?${query}`}
        role="button"
        className="inline-flex w-full items-center justify-center gap-3 rounded-full border border-[var(--border)] bg-white px-6 py-3 text-base font-semibold text-black transition hover:bg-white/90"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5">
          <path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2.1H12v4h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.8 3-4.3 3-7.4Z" />
          <path fill="#34A853" d="M12 22c2.7 0 5-1 6.6-2.4l-3.2-2.5c-.9.6-2 .9-3.4.9a6 6 0 0 1-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z" />
          <path fill="#FBBC05" d="M6.4 13.9a6 6 0 0 1 0-3.8V7.5H3.1a10 10 0 0 0 0 9l3.3-2.6Z" />
          <path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.9 5.5l3.3 2.6A6 6 0 0 1 12 6Z" />
        </svg>
        Continue with Google
      </a>
      <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
        <span className="h-px flex-1 bg-[var(--border)]" />
        <span>or continue with email</span>
        <span className="h-px flex-1 bg-[var(--border)]" />
      </div>
    </div>
  );
}
