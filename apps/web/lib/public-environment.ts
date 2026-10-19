import { Buffer } from "node:buffer";

const publicPrefix = /^(NEXT_PUBLIC_|VITE_|EXPO_PUBLIC_|REACT_APP_)/;
const secretName = /(?:SERVICE_ROLE|SECRET|PRIVATE_KEY|PASSWORD|API_KEY_PEPPER|DATABASE_URL|LITELLM_MASTER_KEY|(?:OPENAI|ANTHROPIC|AZURE)_API_KEY)/;

function isSecretValue(value: string) {
  if (/^(?:sk[-_]|rk_(?:live|test)_|whsec_|sb_secret_)/.test(value) || /-----BEGIN .*PRIVATE KEY-----/.test(value)) return true;
  if (value.startsWith("eyJ") && value.split(".").length === 3) {
    try {
      // Supabase's anon JWT is intentionally public; sessions/service-role JWTs are not.
      return JSON.parse(Buffer.from(value.split(".")[1], "base64url").toString("utf8")).role !== "anon";
    } catch {
      return true;
    }
  }
  return false;
}

export function assertPublicEnvironment(env: Record<string, string | undefined>) {
  const privateValues = Object.entries(env)
    .filter(([name, value]) => !publicPrefix.test(name) && secretName.test(name) && value && value.length >= 16)
    .map(([, value]) => value!);
  const unsafe = Object.entries(env).filter(([name, value]) => publicPrefix.test(name) && value && (
    secretName.test(name) || isSecretValue(value.trim()) || privateValues.some(secret => value.includes(secret))
  )).map(([name]) => name);
  if (unsafe.length) {
    // Report variable names only, never their secret values.
    throw new Error(`Server secrets cannot use public environment prefixes: ${unsafe.join(", ")}`);
  }
}
