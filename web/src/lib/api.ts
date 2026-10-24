// All requests go through the same origin: Vite proxies /api in dev, nginx (Docker)
// or a Vercel rewrite in production forwards it to the API.
export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  const body: unknown = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : undefined;
  if (!response.ok) {
    throw new ApiError(response.status, `${response.status} ${response.statusText}`, body);
  }
  return body as T;
}
