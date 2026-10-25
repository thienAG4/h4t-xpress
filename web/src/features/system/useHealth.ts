// useHealth - polls /api/v1/health; a 503 still carries a body (database down)

import { useQuery } from "@tanstack/react-query";
import { ApiError, request } from "@/lib/http";

export type Health = {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
  version: string;
  demo_mode: boolean;
};

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      try {
        return await request<Health>("/health", { auth: false });
      } catch (error) {
        if (error instanceof ApiError && error.status === 503) {
          return { status: "degraded", database: "unavailable", version: "", demo_mode: false };
        }
        throw error;
      }
    },
    refetchInterval: 30_000,
    retry: 6,
    retryDelay: 5_000,
  });
}

/** True when the API reports demo mode (quick logins, OTP banner, simulator). */
export function useDemoMode(): boolean {
  return useHealth().data?.demo_mode ?? false;
}
