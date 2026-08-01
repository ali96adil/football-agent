const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "";

export async function api<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(
    `${API_URL}${endpoint}`,
    {
      ...options,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
        ...csrfHeader(options?.method),
      },
      cache: "no-store",
    }
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `API ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

function csrfHeader(method?: string): Record<string, string> {
  if (!method || ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase()) || typeof document === "undefined") return {};
  const token = document.cookie.split("; ").find((item) => item.startsWith("football_csrf="))?.split("=").slice(1).join("=");
  return token ? { "X-CSRF-Token": decodeURIComponent(token) } : {};
}
