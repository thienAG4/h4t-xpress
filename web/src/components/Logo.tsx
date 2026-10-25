// Logo - text wordmark "H4T Xpress" (no image or icon)

import { cn } from "@/lib/cn";

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("font-display text-lg font-extrabold tracking-tight text-ink", className)}>
      H4T <span className="text-primary-600">Xpress</span>
    </span>
  );
}
