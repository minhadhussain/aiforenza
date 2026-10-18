import Link from "next/link";

import { AccountSetup } from "@/components/auth/account-setup";
import { AuthShell } from "@/components/auth/auth-shell";
import { safeDashboardPath } from "@/lib/auth";

export default async function CompleteAuthPage({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  const params = searchParams ? await searchParams : undefined;
  const nextPath = safeDashboardPath(typeof params?.next === "string" ? params.next : undefined);
  return (
    <AuthShell
      eyebrow="Account setup"
      title="Let’s get your account ready"
      copy="We’ll finish setting up your profile and wallet, then open your dashboard."
      footer={<Link className="font-semibold text-[var(--accent-strong)]" href={`/login?${new URLSearchParams({ next: nextPath })}`}>Use another account</Link>}
    >
      <AccountSetup nextPath={nextPath} retryRequired={params?.retry === "1"} />
    </AuthShell>
  );
}
