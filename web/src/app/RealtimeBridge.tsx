// RealtimeBridge - keeps the WebSocket open while signed in and refreshes cached data on events

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { realtime } from "@/lib/realtime";
import { useSession } from "@/lib/session";
import { toast } from "@/lib/toast";

// Server event -> query key prefixes to refetch. Screens never parse event payloads themselves.
const REFRESH: Record<string, string[][]> = {
  "offer.created": [["delivery", "offer"], ["hub", "drivers"]],
  "offer.expired": [["delivery", "offer"], ["hub", "drivers"]],
  "order.updated": [["delivery"], ["driver", "today"], ["hub"]],
  "order.on_hold": [["hub"]],
  "route.updated": [["delivery"]],
  "incident.created": [["incidents"], ["hub"]],
  "incident.updated": [["incidents"], ["hub"], ["delivery"]],
};

export function RealtimeBridge() {
  const queryClient = useQueryClient();
  const status = useSession((state) => state.status);
  const role = useSession((state) => state.user?.role);

  useEffect(() => {
    if (status !== "authenticated") return;
    realtime.start();
    const unsubscribe = realtime.subscribe(({ event }) => {
      for (const queryKey of REFRESH[event] ?? []) {
        void queryClient.invalidateQueries({ queryKey });
      }
      if (event === "incident.created" && role === "HUB_MANAGER") {
        toast.info("A driver reported a new incident.");
      }
      if (event === "incident.updated" && role === "DRIVER") {
        toast.info("The hub answered your incident report.");
      }
    });
    return () => {
      unsubscribe();
      realtime.stop();
    };
  }, [status, role, queryClient]);

  return null;
}
