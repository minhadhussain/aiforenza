import Link from "next/link";

import { AuthShell } from "@/components/auth/auth-shell";
import { SignupForm } from "@/components/auth/signup-form";
import { GoogleAuthButton } from "@/components/auth/google-auth-button";
import { authErrorMessage, safeDashboardPath } from "@/lib/auth";

export default async function SignupPage({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  const params = searchParams ? await searchParams : undefined;
  const nextPath = safeDashboardPath(typeof params?.next === "string" ? params.next : undefined);
  return (
    <AuthShell
      eyebrow="Authentication"
      title="Create your developer account"
      copy="Sign up with Google or email to start building with AI Forenza. Your account and sign-in details are securely managed by Supabase."
      footer={
        <>
          Already have an account? <Link className="font-semibold text-[var(--accent-strong)]" href="/login">Log in</Link>
        </>
      }
    >
      <GoogleAuthButton intent="signup" nextPath={nextPath} />
      <SignupForm nextPath={nextPath} initialError={authErrorMessage(params?.error)} />
    </AuthShell>
  );
}
