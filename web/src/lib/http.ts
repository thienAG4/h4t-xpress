// HTTP client - JSON requests with bearer token and one silent refresh on 401

import type { TokenResponse } from "@/types";
import { useSession } from "./session";

// Same origin everywhere: Vite proxies /api in dev, nginx or a Vercel rewrite in production.
export const API_BASE = "/api/v1";

export type FieldError = { field: string; message: string };

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Field errors of a VALIDATION_ERROR response, keyed by field name. */
  get fieldErrors(): Record<string, string> {
    if (this.code !== "VALIDATION_ERROR" || !Array.isArray(this.details)) return {};
    return Object.fromEntries(
      (this.details as FieldError[]).map((detail) => [detail.field, detail.message]),
    );
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  // Set to false for sign-in calls: a 401 there means wrong credentials, not an expired token.
  auth?: boolean;
  headers?: Record<string, string>;
};

let refreshInFlight: Promise<boolean> | null = null;

/**
 * Exchange the refresh cookie for a new access token. Concurrent callers share one request.
 */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        useSession.getState().clear();
        return false;
      }
      const data = (await response.json()) as TokenResponse;
      useSession.getState().setSession(data.access_token, data.user);
      return true;
    } catch {
      useSession.getState().clear();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const search = params.toString();
  return `${API_BASE}${path}${search ? `?${search}` : ""}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const body: unknown = isJson ? await response.json() : undefined;
  if (response.ok) return body as T;

  const error = (body as { error?: { code?: string; message?: string; details?: unknown } })?.error;
  throw new ApiError(
    response.status,
    error?.code ?? "HTTP_ERROR",
    error?.message ?? response.statusText,
    error?.details,
  );
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, auth = true, headers = {} } = options;

  const send = () => {
    const token = useSession.getState().accessToken;
    return fetch(buildUrl(path, query), {
      method,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(auth && token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let response = await send();
  if (response.status === 401 && auth && (await refreshSession())) {
    response = await send();
  }
  return parseResponse<T>(response);
}

/** Multipart upload of one file (photos). Same token and refresh rules as `request`. */
export async function uploadFile<T>(path: string, file: Blob, filename: string): Promise<T> {
  const send = () => {
    const form = new FormData();
    form.append("file", file, filename);
    const token = useSession.getState().accessToken;
    return fetch(buildUrl(path), {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: form,
    });
  };

  let response = await send();
  if (response.status === 401 && (await refreshSession())) {
    response = await send();
  }
  return parseResponse<T>(response);
}
