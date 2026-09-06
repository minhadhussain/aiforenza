import Link from "next/link";

import { AuthShell } from "@/components/auth/auth-shell";
import { SignupForm } from "@/components/auth/signup-form";

export default function SignupPage() {
  return (
    <AuthShell
      eyebrow="Authentication"
      title="Create your developer account"
      copy="Phase 2 establishes the authenticated user flow so later wallet, API key, and billing work can attach cleanly to a protected dashboard."
      footer={
        <>
          Already registered? <Link className="font-semibold text-[var(--accent-strong)]" href="/login">Log in instead</Link>
        </>
      }
    >
      <SignupForm />
    </AuthShell>
  );
}
