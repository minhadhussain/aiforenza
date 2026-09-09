type ApiOptions = {
  accessToken?: string;
  cache?: RequestCache;
};

export async function apiGet<T>(path: string, options: ApiOptions): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1";

  if (!baseUrl) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL.");
  }

  const response = await fetch(`${baseUrl}${path}`, {
    method: "GET",
    headers: {
      ...(options.accessToken ? { Authorization: `Bearer ${options.accessToken}` } : {}),
      "Content-Type": "application/json",
    },
    cache: options.cache ?? "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed.";

    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Keep the fallback error text when no JSON body is returned.
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}
