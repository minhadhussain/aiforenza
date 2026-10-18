/** Bound auth requests in the browser, route handlers, and middleware alike. */
export function authFetch(input: RequestInfo | URL, init?: RequestInit) {
  const original = init?.signal ?? (input instanceof Request ? input.signal : undefined);
  const deadline = AbortSignal.timeout(20_000);
  return fetch(input, {
    ...init,
    signal: original ? AbortSignal.any([original, deadline]) : deadline,
  });
}
