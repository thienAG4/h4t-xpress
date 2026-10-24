import { useQuery } from "@tanstack/react-query";
import { ApiError, apiGet } from "@/lib/api";

export type Health = {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
  version: string;
  demo_mode: boolean;
};

/** Polls /api/v1/health. A 503 still carries a Health body (database down). */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      try {
        return await apiGet<Health>("/health");
      } catch (error) {
        if (error instanceof ApiError && error.status === 503 && error.body) {
          return error.body as Health;
        }
        throw error;
      }
    },
    refetchInterval: 30_000,
    retry: 6,
    retryDelay: 5_000,
  });
}
