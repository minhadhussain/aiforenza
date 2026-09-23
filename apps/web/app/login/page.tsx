import Link from "next/link";

import { AuthShell } from "@/components/auth/auth-shell";
import { LoginForm } from "@/components/auth/login-form";
import { GoogleAuthButton } from "@/components/auth/google-auth-button";
import { authErrorMessage } from "@/lib/auth";

type LoginPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const nextParam = resolvedSearchParams?.next;
  const nextPath = Array.isArray(nextParam) ? nextParam[0] : nextParam;
  const initialError = authErrorMessage(resolvedSearchParams?.error);

  return (
    <AuthShell
      eyebrow="Authentication"
      title="Return to your API dashboard"
      copy="Sign in with Google or email to manage your API keys, credits, and usage."
      footer={
        <>
          New here? <Link className="font-semibold text-[var(--accent-strong)]" href="/signup">Create an account</Link>
        </>
      }
    >
      <GoogleAuthButton intent="login" nextPath={nextPath} />
      <LoginForm nextPath={nextPath || "/dashboard"} initialError={initialError} />
    </AuthShell>
  );
}
