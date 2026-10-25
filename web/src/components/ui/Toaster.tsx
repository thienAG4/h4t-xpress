// Toaster - renders the toast stack from the toast store

import { cn } from "@/lib/cn";
import { useToast } from "@/lib/toast";

const TONES = {
  success: "border-success-500 bg-white",
  error: "border-danger-500 bg-white",
  info: "border-primary-600 bg-white",
};

export function Toaster() {
  const { toasts, dismiss } = useToast();
  return (
    <div className="fixed top-4 right-4 z-50 flex w-[min(92vw,360px)] flex-col gap-2" aria-live="polite">
      {toasts.map((item) => (
        <div
          key={item.id}
          className={cn(
            "flex items-start justify-between gap-3 rounded-card border-l-4 px-4 py-3 text-sm shadow-lg",
            TONES[item.tone],
          )}
        >
          <span>{item.message}</span>
          <button
            type="button"
            className="text-xs font-semibold text-neutral-500 hover:text-ink"
            onClick={() => dismiss(item.id)}
          >
            Close
          </button>
        </div>
      ))}
    </div>
  );
}
