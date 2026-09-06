import Link from "next/link";

import { AuthShell } from "@/components/auth/auth-shell";
import { LoginForm } from "@/components/auth/login-form";

type LoginPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const nextParam = resolvedSearchParams?.next;
  const nextPath = Array.isArray(nextParam) ? nextParam[0] : nextParam;

  return (
    <AuthShell
      eyebrow="Authentication"
      title="Return to your API dashboard"
      copy="Use your Supabase account to access wallet views, API keys, transactions, and usage screens as they come online in later phases."
      footer={
        <>
          New here? <Link className="font-semibold text-[var(--accent-strong)]" href="/signup">Create an account</Link>
        </>
      }
    >
      <LoginForm nextPath={nextPath || "/dashboard"} />
    </AuthShell>
  );
}
