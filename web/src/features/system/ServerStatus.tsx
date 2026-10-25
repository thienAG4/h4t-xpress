// ServerStatus - API/database status pill, including the free-tier "waking up" state

import { cn } from "@/lib/cn";
import { useHealth } from "./useHealth";

export function ServerStatus({ className }: { className?: string }) {
  const { data, isPending, isError, failureCount } = useHealth();

  let tone = "bg-neutral-100 text-neutral-600";
  let dot = "bg-neutral-400";
  let label = "Checking server";

  if (isPending && failureCount > 0) {
    // Free-tier hosting sleeps when idle; the first request can take up to a minute.
    label = "Waking up server";
    dot = "bg-warning-500 animate-pulse";
    tone = "bg-warning-50 text-warning-700";
  } else if (isError) {
    label = "API unreachable";
    dot = "bg-danger-500";
    tone = "bg-danger-50 text-danger-700";
  } else if (data) {
    const healthy = data.database === "ok";
    label = healthy ? `API online, v${data.version}` : "Database unavailable";
    dot = healthy ? "bg-success-500" : "bg-warning-500";
    tone = healthy ? "bg-success-50 text-success-700" : "bg-warning-50 text-warning-700";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium",
        tone,
        className,
      )}
      role="status"
    >
      <span className={cn("size-2 rounded-full", dot)} aria-hidden />
      {label}
      {data?.demo_mode && <span className="font-semibold">(demo)</span>}
    </span>
  );
}
