# Google and email authentication

Both `/login` and `/signup` offer **Continue with Google**, followed by the existing email/password form. Each page has one account-switch link. Signup accepts a valid email address, not a username such as `ADMIN1`.

## Supabase storage and flow

- Supabase Auth stores users, Google identities, password hashes, and sessions.
- Google login and signup use the same Supabase OAuth flow. Supabase creates a user on the first successful Google sign-in and signs returning users in subsequently.
- `GET /auth/google` checks the hosted Supabase provider settings and starts `signInWithOAuth` using the existing server-side Supabase SSR client. The SDK manages the PKCE verifier cookie.
- `GET /auth/callback` exchanges the returned code for a session and persists the session cookies through the existing SSR client. It immediately opens `/auth/complete`, preserving the safe dashboard return path.
- `/auth/complete` displays setup progress while checking the session and initializing the account. A timeout or temporary outage shows **Retry account setup** while retaining the session. Retrying does not resubmit signup or grant a second trial credit.
- `POST /v1/account/bootstrap` requires the verified Supabase bearer session and derives the user ID/email from that identity. It calls the existing transactional `bootstrap_user_account` RPC. Client-supplied user IDs, emails, or grant amounts cannot select an account.
- Password login and immediately confirmed email signup use the same account initialization step, and open the recovery page if setup fails after authentication succeeds. Email signup requiring confirmation displays the confirmation instructions.
- The existing profile, one paid wallet, and once-only $5 signup credit are reused. OAuth does not create a separate wallet or another billing system.
- OAuth cancellation and failures return fixed safe messages. Browser and server auth requests have a 20-second deadline, including callback exchange and dashboard session checks. Temporary session-check failures open the recovery page rather than treating the user as signed out or blocking the protected layout. External return URLs are rejected.

## Required hosted Google setup

Google is currently enabled in the connected Supabase project, and both auth pages have been verified to reach Google's account sign-in form with a PKCE cookie. For another deployment, configure the hosted provider as follows; application code alone does not enable it.

1. In Google Cloud Console, configure the OAuth consent screen and create an **OAuth client ID → Web application**.
2. Add the Supabase callback as a Google **Authorized redirect URI**:
   ```text
   https://<your-project-ref>.supabase.co/auth/v1/callback
   ```
   Use the exact callback URL shown by Supabase. This is different from the application's callback below.
3. In Supabase **Authentication → Sign In / Providers → Google**, enable Google and enter the Google client ID and secret.
4. In Supabase **Authentication → URL Configuration**, set the real site URL and allow the application's callback URLs. For local development:
   ```text
   http://localhost:3000/auth/callback**
   http://127.0.0.1:3000/auth/callback**
   ```
   For deployment, add the corresponding HTTPS application callback on the trusted production domain. The suffix permits the `next`/`intent` query parameters.
5. If the Google consent screen is in testing mode, add the Google accounts that will test the app as test users.

Google client secrets belong in the Supabase provider settings. They must not be placed in `NEXT_PUBLIC_*` variables, browser code, or committed files. For local Supabase, the disabled `[auth.external.google]` block in `supabase/config.toml` shows the private environment variables to configure before enabling it.

The Supabase CLI needs `npx supabase login` (or a private `SUPABASE_ACCESS_TOKEN`) to manage hosted projects. The application service-role key and database password are not management access tokens. Google OAuth client credentials must also exist; the Supabase CLI cannot invent them.

Until the provider is enabled, the button returns a clear message on the original auth page and email/password authentication remains available.

## Verification

```powershell
npm --workspace apps/web run test:auth
python tools/verify_google_auth.py
python tools/verify_account_setup.py
python tools/verify_signin.py --full-flow --fresh-account
python tools/verify_signin.py --check-timeout
```

The Node route tests substitute external I/O to cover enabled-provider redirects, callback code exchange, chunked provider-session cookies, temporary session failures, cancellation, recovery, and safe return URLs. They do not claim a completed real Google login.

The browser checks exercise the real forms, single account-switch links, invalid `ADMIN1` email handling, Google handoff (or the disabled-provider response), callback cancellation, and invalid-code recovery. The fresh-account check verifies real Supabase Auth login, profile persistence, one paid wallet, and exactly one signup credit across repeated sign-ins. Its synthetic account is retired afterward while ledger evidence is retained.

`verify_account_setup.py` supplies an immediately confirmed signup response from a disposable admin-created identity, then uses its real Supabase session and backend RPCs. It verifies bootstrap failure and timeout recovery, a preserved dashboard deep link, no repeated signup request, and exactly one profile/wallet/trial grant after retries. It does not test Google consent or delivery of a confirmation email.

After this recovery change, the user confirmed that retrying the previously failing Google account opened the dashboard successfully. Repeat a real Google identity sign-in when changing hosted provider credentials or redirect URLs; the automated handoff checks stop at Google's sign-in form.
