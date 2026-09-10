// Receives a real session over stdin; never logs cookies, tokens, or page HTML.
const { createRequire } = require('node:module');
const path = require('node:path');
const requireWeb = createRequire(path.resolve(__dirname, '../apps/web/package.json'));
const { createServerClient } = requireWeb('@supabase/ssr');

async function main() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const data = JSON.parse(input);
  const cookies = new Map();
  const client = createServerClient(data.url, data.anon_key, {
    cookies: {
      getAll: () => [...cookies].map(([name, value]) => ({name, value})),
      setAll: items => items.forEach(({name, value}) => cookies.set(name, value)),
    },
  });
  const { error } = await client.auth.setSession(data.session);
  if (error) throw new Error('Session setup failed');
  const response = await fetch('http://localhost:3000/dashboard', {
    headers: {Cookie: [...cookies].map(([name, value]) => `${name}=${value}`).join('; ')},
    redirect: 'manual',
  });
  const html = await response.text();
  const text = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '').replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ');
  const money = cents => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(cents / 100);
  const expected = money(data.expected_available_cents ?? data.expected_cents);
  const total = money(data.expected_cents);
  const reserved = money(data.expected_reserved_cents ?? 0);
  const balance = text.match(/AVAILABLE BALANCE\s+(\$[\d,.]+)/)?.[1];
  const verified = response.status === 200 && text.includes(data.email) && balance === expected
    && text.includes(`Wallet total: ${total}`) && text.includes(`Reserved for requests: ${reserved}`);
  const routes = {};
  for (const route of ['/dashboard/usage', '/dashboard/api-keys']) {
    const page = await fetch('http://localhost:3000' + route, {
      headers: {Cookie: [...cookies].map(([name, value]) => `${name}=${value}`).join('; ')},
      redirect: 'manual',
    });
    const body = await page.text();
    routes[route] = page.status;
    if (page.status !== 200 || body.includes('SUPABASE_URL is not configured.')) {
      throw new Error('Authenticated page failed');
    }
  }
  console.log(JSON.stringify({http_status: response.status, balance_verified: verified,
    available_display: balance, expected_display: expected, routes}));
  if (!verified) process.exitCode = 1;
}
main().catch(() => { console.log(JSON.stringify({balance_verified: false})); process.exitCode = 1; });
