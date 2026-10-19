const assert = require("node:assert/strict");
const { test } = require("node:test");
const { load } = require("./helpers.cjs");

const { assertPublicEnvironment } = load("lib/public-environment.ts");
const jwt = (role) => `eyJhbGciOiJIUzI1NiJ9.${Buffer.from(JSON.stringify({ role })).toString("base64url")}.fixture`;

test("public configuration accepts Supabase anon/publishable and Stripe publishable keys", () => {
  assert.doesNotThrow(() => assertPublicEnvironment({
    NEXT_PUBLIC_API_BASE_URL: "https://api.example.com/v1",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: jwt("anon"),
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_fixture",
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: "pk_live_fixture",
    SUPABASE_SERVICE_ROLE_KEY: jwt("service_role"),
    STRIPE_SECRET_KEY: "sk_live_PRIVATE_FIXTURE",
  }));
});

test("public-prefix mistakes fail without printing any secret", () => {
  for (const prefix of ["NEXT_PUBLIC_", "VITE_", "EXPO_PUBLIC_", "REACT_APP_"]) {
    for (const value of ["sk_live_PRIVATE_FIXTURE", "sk-proj-PRIVATE_FIXTURE", "sk-ant-api03-PRIVATE_FIXTURE", "sb_secret_PRIVATE_FIXTURE", jwt("service_role"), jwt("authenticated")]) {
      const name = `${prefix}SUPABASE_ANON_KEY`;
      assert.throws(() => assertPublicEnvironment({ [name]: value }), (error) => {
        assert.ok(error.message.includes(name));
        assert.ok(!error.message.includes(value));
        return true;
      });
    }
  }
});

test("misnamed server credentials and public copies of opaque private keys are rejected", () => {
  assert.throws(() => assertPublicEnvironment({ NEXT_PUBLIC_AZURE_API_KEY: "opaque-provider-value" }));
  assert.throws(() => assertPublicEnvironment({
    AZURE_API_KEY: "opaque-server-credential-value",
    NEXT_PUBLIC_FEATURE_VALUE: "opaque-server-credential-value",
  }));
});
